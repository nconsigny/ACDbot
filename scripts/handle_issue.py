import os
import sys
import argparse
from ..modules import discourse, zoom
from github import Github

# Import your custom modules


def handle_github_issue(issue_number: int, repo_name: str):
    """
    Fetches the specified GitHub issue, extracts its title and body,
    then creates a Discourse topic using the issue title as the topic title
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

    # 3. Create Discourse Topic
    discourse_response = discourse.create_topic(
        title=issue_title,
        body=issue_body,
        category_id=63  # Replace with your desired category ID
    )

    # 4. (Optional) Create Zoom Meeting
    #    Raise a ValueError in parse_issue_for_time if date/time format is invalid
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
        topic_id = discourse_response.get("topic_id")
        discourse_url = (
            f"{os.environ.get('DISCOURSE_BASE_URL', 'https://ethereum-magicians.org')}/t/{topic_id}"
        )
        issue.create_comment(f"Discourse topic created: {discourse_url}")
    except Exception as e:
        issue.create_comment(f"Error posting Discourse topic: {e}")

def parse_issue_for_time(issue_body: str):
    """
    Parses the issue body to extract start time and duration based on the new format.

    Expected format example within the issue body:
      - [Jan 16, 2025, 14:00 UTC](https://savvytime.com/converter/utc/jan-16-2025/2pm)
      - Duration in minutes

    If these values can't be found or parsed, a ValueError is raised instead of falling back.
    """
    import re
    from datetime import datetime

    # Match something like: [Jan 16, 2025, 14:00 UTC](...)
    date_time_match = re.search(
        r"\[([A-Za-z]{3} \d{1,2}, \d{4}, \d{1,2}:\d{2} UTC)\]\(",
        issue_body
    )
    if not date_time_match:
        raise ValueError("Missing or invalid date/time format.")

    dt_str = date_time_match.group(1).strip()
    # Example format: "Jan 16, 2025, 14:00 UTC"
    try:
        dt_obj = datetime.strptime(dt_str, "%b %d, %Y, %H:%M UTC")
        start_time = dt_obj.isoformat() + "Z"
    except ValueError:
        raise ValueError("Unable to parse date/time in the specified format.")

    # Extract duration in minutes
    duration_match = re.search(
        r"Duration in minutes\s*\n-?\s*(\d+)",
        issue_body,
        re.IGNORECASE
    )
    if not duration_match:
        raise ValueError("Missing or invalid duration format.")

    duration = int(duration_match.group(1))
    return start_time, duration

def main():
    parser = argparse.ArgumentParser(description="Handle GitHub issue and create Discourse topic.")
    parser.add_argument("--issue_number", required=True, type=int, help="GitHub issue number")
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., 'org/repo')")
    args = parser.parse_args()

    handle_github_issue(issue_number=args.issue_number, repo_name=args.repo)

if __name__ == "__main__":
    main()