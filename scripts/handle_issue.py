import os
import sys
import argparse
from modules import discourse, zoom
from github import Github

# Import your custom modules


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


def parse_issue_for_time(issue_body: str):
    """
    Parses the issue body to extract a start time and duration based on possible formats:
    
    - Date/time line followed by a duration line (with or without "Duration in minutes" preceding it)
    """
    import re
    from datetime import datetime

    # -------------------------------------------------------------------------
    # 1. Regex pattern to find the date/time in the issue body
    # -------------------------------------------------------------------------
    date_pattern = re.compile(
        r"""
        \[                         # Literal '['
        (                          # Start of group for date/time
          [A-Za-z]{3}              # Month abbreviation (e.g., Jan, Feb)
          [,\s]+                   # Comma or whitespace
          \d{1,2}                  # Day of the month
          [,\s]+                   # Comma or whitespace
          \d{4}                    # Year
          [,\s]+                   # Comma or whitespace
          \d{1,2}:\d{2}            # Time in HH:MM format
        )
        (?:-(\d{1,2}:\d{2}))?      # Optional end time (HH:MM)
        \s*UTC\]                   # ' UTC]'
        """,
        re.IGNORECASE | re.VERBOSE
    )

    date_match = date_pattern.search(issue_body)
    if not date_match:
        raise ValueError("Missing or invalid date/time format (couldn't match bracketed time).")

    datetime_str = date_match.group(1)
    end_time_str = date_match.group(2)

    # Normalize month abbreviation
    datetime_str = datetime_str.title()

    datetime_str = datetime_str.replace(",", " ")
    datetime_str = re.sub(r"\s+", " ", datetime_str).strip()

    # Parse start datetime
    try:
        start_dt = datetime.strptime(datetime_str, "%b %d %Y %H:%M")
    except ValueError as e:
        raise ValueError(f"Unable to parse the start time: {e}")
    
    start_time_utc = start_dt.isoformat() + "Z"

    # -------------------------------------------------------------------------
    # 2. Determine duration
    # -------------------------------------------------------------------------
    duration_minutes = None
    if end_time_str:
        # Calculate duration from end time
        end_datetime_str = f"{start_dt.strftime('%b %d %Y')} {end_time_str}"
        try:
            end_dt = datetime.strptime(end_datetime_str, "%b %d %Y %H:%M")
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
            ^[ \t\-]*                # Optional spaces/dashes at the start
            (?:Duration\s+in\s+minutes\s*)? # Optional 'Duration in minutes'
            [ \t\-]*                 # Optional spaces/dashes
            (\d+)                    # The duration number
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


def main():
    parser = argparse.ArgumentParser(description="Handle GitHub issue and create/update Discourse topic.")
    parser.add_argument("--issue_number", required=True, type=int, help="GitHub issue number")
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., 'org/repo')")
    args = parser.parse_args()

    handle_github_issue(issue_number=args.issue_number, repo_name=args.repo)


if __name__ == "__main__":
    main()