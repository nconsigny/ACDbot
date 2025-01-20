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
    
    1) A single start time and a separate "Duration in minutes" line, e.g.
         [Jan 16, 2025, 14:00 UTC](https://savvytime.com/...) or [Jan 18, 2025, 14:00-15:30 UTC](https://savvytime.com/...)
         Duration in minutes
         90
    """
    import re
    from datetime import datetime

    # Regex to capture something like "[Jan 16, 2025, 14:00 UTC](...)" or
    # "[Jan 18, 2025, 14:00-15:30 UTC](...)"
    #  - Group 1: "Jan 16, 2025, 14:00" or "Jan 18, 2025, 14:00"
    #  - Group 2: "-15:30" (optional dash + end time)
    pattern = re.compile(
        r"\[([A-Za-z]{3}\s+\d{1,2},\s*\d{4},\s*\d{1,2}:\d{2})(-\d{1,2}:\d{2})?\s*UTC\]\(",
        re.IGNORECASE
    )

    match = pattern.search(issue_body)
    if not match:
        raise ValueError("Missing or invalid date/time format (couldn't match bracketed time).")

    # -------------------------
    # Handle start time
    # -------------------------
    # Extract the first portion, e.g., "Jan 16, 2025, 14:00"
    datetime_str = match.group(1).strip()
    # Attempt to parse the start time
    try:
        start_dt = datetime.strptime(datetime_str, "%b %d, %Y, %H:%M")
        start_time_utc = start_dt.isoformat() + "Z"
    except ValueError:
        raise ValueError("Unable to parse the start time in the specified format.")

    # -------------------------
    # Handle optional end time
    # -------------------------
    # Group 2 might be something like "-15:30"
    end_segment = match.group(2)  # e.g., "-15:30"
    duration_minutes = None

    if end_segment:
        # If user provided an end time "14:00-15:30"
        # Remove the leading dash, then parse
        end_time_str = end_segment.lstrip("-").strip()  # "15:30"
        try:
            end_dt = datetime.strptime(
                f"{start_dt.strftime('%b %d, %Y, ')}{end_time_str}",
                "%b %d, %Y, %H:%M"
            )
        except ValueError:
            raise ValueError("Unable to parse the end time in the specified format.")

        # Compute duration in minutes
        if end_dt <= start_dt:
            raise ValueError(
                "End time is not after start time; cannot compute positive duration."
            )

        duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
    else:
        # If user did not provide an end time in the bracketed text,
        # look for a "Duration in minutes" line in the rest of the issue
        duration_match = re.search(
            r"Duration in minutes\s*\n-?\s*(\d+)",
            issue_body,
            re.IGNORECASE
        )
        if not duration_match:
            raise ValueError(
                "Missing or invalid duration format. "
                "Provide 'Duration in minutes' or start-end time in bracketed text."
            )
        duration_minutes = int(duration_match.group(1))

    return start_time_utc, duration_minutes

def main():
    parser = argparse.ArgumentParser(description="Handle GitHub issue and create/update Discourse topic.")
    parser.add_argument("--issue_number", required=True, type=int, help="GitHub issue number")
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., 'org/repo')")
    args = parser.parse_args()

    handle_github_issue(issue_number=args.issue_number, repo_name=args.repo)

if __name__ == "__main__":
    main()