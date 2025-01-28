import os
import sys
import argparse
from modules import discourse, zoom
from github import Github
import re
from datetime import datetime
import json
import requests
from github import InputGitAuthor

# Import your custom modules

MAPPING_FILE = "meeting_topic_mapping.json"

def load_meeting_topic_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r") as f:
            return json.load(f)
    return {}

def save_meeting_topic_mapping(mapping):
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f)

def handle_github_issue(issue_number: int, repo_name: str):
    """
    Fetches the specified GitHub issue, extracts its title and body,
    then creates or updates a Discourse topic using the issue title as the topic title
    and its body as the topic content.

    If the date/time or duration cannot be parsed from the issue body, 
    a comment is posted indicating the format error, and no meeting is created.
    """
    # 1. Connect to GitHub API
    gh = Github(os.environ["GITHUB_TOKEN"])
    repo = gh.get_repo(repo_name)

    # 2. Retrieve the issue
    issue = repo.get_issue(number=issue_number)
    issue_title = issue.title
    issue_body = issue.body or "(No issue body provided.)"

    # Load existing mapping
    mapping = load_meeting_topic_mapping()

    # 3. Check for existing topic_id in issue comments
    topic_id = None
    for comment in issue.get_comments():
        if comment.body.startswith("**Discourse Topic ID:**"):
            try:
                topic_id = int(comment.body.split("**Discourse Topic ID:**")[1].strip())
                break
            except ValueError:
                continue

    if topic_id:
        # Update the existing Discourse topic
        discourse_response = discourse.update_topic(
            topic_id=topic_id,
            title=issue_title,
            body=issue_body,
            category_id=63  
        )
    else:
        # Create a new Discourse topic
        discourse_response = discourse.create_topic(
            title=issue_title,
            body=issue_body,
            category_id=63  
        )
        topic_id = discourse_response.get("topic_id")
        # Add a hidden comment with the topic_id for future updates
        issue.create_comment(f"**Discourse Topic ID:** {topic_id}")

    # 4. (Optional) Create Zoom Meeting
    try:
        start_time, duration = parse_issue_for_time(issue_body)
        join_url, zoom_id = zoom.create_meeting(
            topic=f"Issue {issue.number}: {issue_title}",
            start_time=start_time,
            duration=duration
        )
        issue.create_comment(f"Zoom meeting created: {join_url}\nZoom Meeting ID: {zoom_id}")
    except ValueError:
        issue.create_comment(
            "Meeting couldn't be created due to format error. "
            "Couldn't extract date/time and duration. Expected date/time in UTC like:\n\n"
            "  [Jan 16, 2025, 14:00 UTC](https://savvytime.com/converter/utc/jan-16-2025/2pm)\n\n"
            "Please run the script manually to schedule the meeting."
        )
    except Exception as e:
        issue.create_comment(f"Error creating Zoom meeting: {e}")

    # 5. Post Discourse Topic Link as a Comment
    try:
        discourse_url = (
            f"{os.environ.get('DISCOURSE_BASE_URL', 'https://ethereum-magicians.org')}/t/{topic_id}"
        )
        issue.create_comment(f"Discourse topic created/updated: {discourse_url}")
    except Exception as e:
        issue.create_comment(f"Error posting Discourse topic: {e}")

    # 6. Update the mapping and save it
    mapping[str(zoom_id)] = topic_id
    save_meeting_topic_mapping(mapping)

    # Commit the updated mapping file to the repository
    commit_mapping_file(repo)
    print(f"Mapping updated: Zoom Meeting ID {zoom_id} -> Discourse Topic ID {topic_id}")

    # Remove any null mappings or failed entries
    mapping = {k: v for k, v in mapping.items() if v is not None}

def parse_issue_for_time(issue_body: str):
    """
    Parses the issue body to extract a start time and duration based on possible formats:
    
    - Date/time line followed by a duration line (with or without "Duration in minutes" preceding it)
    - Accepts both abbreviated and full month names
    """
    
    # -------------------------------------------------------------------------
    # 1. Regex pattern to find the date/time in the issue body
    # -------------------------------------------------------------------------
    date_pattern = re.compile(
        r"""
        \[?                                        # Optional opening bracket
        (?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?    # Optional day of the week
        (?P<month>[A-Za-z]{3,9})\s+               # Full or abbreviated month name
        (?P<day>\d{1,2}),?\s+                      # Day of the month, comma optional
        (?P<year>\d{4}),?\s+                       # Year, comma optional
        (?P<hour>\d{1,2}):(?P<minute>\d{2})        # Start time HH:MM
        (?:-(?P<end_hour>\d{1,2}):(?P<end_minute>\d{2}))?  # Optional end time HH:MM
        \s*UTC                                     # UTC timezone
        \]?                                        # Optional closing bracket
        """,
        re.IGNORECASE | re.VERBOSE
    )

    date_match = date_pattern.search(issue_body)
    if not date_match:
        raise ValueError("Missing or invalid date/time format.")

    month = date_match.group('month')
    day = date_match.group('day')
    year = date_match.group('year')
    hour = date_match.group('hour')
    minute = date_match.group('minute')
    end_hour = date_match.group('end_hour')
    end_minute = date_match.group('end_minute')

    # Construct the datetime string
    datetime_str = f"{month} {day} {year} {hour}:{minute}"
    try:
        start_dt = datetime.strptime(datetime_str, "%B %d %Y %H:%M")  # Full month name
    except ValueError:
        try:
            start_dt = datetime.strptime(datetime_str, "%b %d %Y %H:%M")  # Abbreviated month name
        except ValueError as e:
            raise ValueError(f"Unable to parse the start time: {e}")

    start_time_utc = start_dt.isoformat() + "Z"

    # -------------------------------------------------------------------------
    # 2. Determine duration
    # -------------------------------------------------------------------------
    duration_minutes = None
    if end_hour and end_minute:
        # Calculate duration from end time
        end_month = month  # Assuming the end time is on the same month and year
        end_day = day      # Assuming the end time is on the same day
        end_datetime_str = f"{end_month} {end_day} {year} {end_hour}:{end_minute}"
        try:
            end_dt = datetime.strptime(end_datetime_str, "%B %d %Y %H:%M")  # Full month name
        except ValueError:
            try:
                end_dt = datetime.strptime(end_datetime_str, "%b %d %Y %H:%M")  # Abbreviated month name
            except ValueError as e:
                raise ValueError(f"Unable to parse the end time: {e}")

        if end_dt <= start_dt:
            raise ValueError("End time must be after start time.")

        duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
    else:
        # Extract duration from the line following the date/time
        # Find the position after the date/time match
        end_pos = date_match.end()

        # Extract the remaining text after date/time
        remaining_text = issue_body[end_pos:]

        # Regex to find a number (duration) in the lines after date/time
        duration_pattern = re.compile(
            r"""
            ^[ \t\-]*                             # Optional spaces/dashes at the start
            (?:Duration\s+in\s+minutes\s*)?      # Optional 'Duration in minutes'
            [ \t\-]*                              # Optional spaces/dashes
            (\d+)                                 # The duration number
            """,
            re.MULTILINE | re.IGNORECASE | re.VERBOSE
        )

        duration_match = duration_pattern.search(remaining_text)
        if duration_match:
            duration_minutes = int(duration_match.group(1))
        else:
            raise ValueError(
                "Missing or invalid duration format. Provide duration in minutes after the date/time."
            )

    return start_time_utc, duration_minutes

def commit_mapping_file(repo):
    file_path = MAPPING_FILE
    commit_message = "Update meeting-topic mapping"
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    author = InputGitAuthor(
        name="GitHub Actions Bot",
        email="actions@github.com"
    )

    with open(file_path, "r") as f:
        file_content = f.read()

    # Check if the file exists in the repository
    try:
        contents = repo.get_contents(file_path, ref=branch)
        repo.update_file(
            path=contents.path,
            message=commit_message,
            content=file_content,
            sha=contents.sha,
            branch=branch,
            author=author,
        )
        print(f"Updated {file_path} in the repository.")
    except Exception as e:
        repo.create_file(
            path=file_path,
            message=commit_message,
            content=file_content,
            branch=branch,
            author=author,
        )
        print(f"Created {file_path} in the repository.")

def main():
    parser = argparse.ArgumentParser(description="Handle GitHub issue and create/update Discourse topic.")
    parser.add_argument("--issue_number", required=True, type=int, help="GitHub issue number")
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., 'org/repo')")
    args = parser.parse_args()

    handle_github_issue(issue_number=args.issue_number, repo_name=args.repo)


if __name__ == "__main__":
    main()