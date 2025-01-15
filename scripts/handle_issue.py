import os
import sys
import re
import requests
import argparse
from github import Github
from modules.zoom import create_zoom_meeting
from modules.discourse import create_topic

def parse_arguments():
    parser = argparse.ArgumentParser(description="Handle new issue")
    parser.add_argument("--issue_number", required=True, type=int)
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g. org/repo)")
    return parser.parse_args()

def extract_times_from_issue_body(body_text):
    """
    Example function to parse out the date/time info.
    You might do more robust pattern matching or rely on
    a link to timeanddate.com in the body.
    """
    # Simple example: look for an ISO datetime pattern
    match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", body_text)
    if match:
        start_time = match.group(0)
        # Hard-code a 60-minute meeting; or parse an end_time, etc.
        return start_time, 60
    return None, None

def main():
    args = parse_arguments()

    # 1) Connect to GitHub API
    gh = Github(os.environ["GITHUB_TOKEN"])
    repo = gh.get_repo(args.repo)
    issue = repo.get_issue(number=args.issue_number)

    # 2) Parse start/end times from the issue body
    start_time, duration = extract_times_from_issue_body(issue.body)

    # Fallback if no time is found
    if not start_time:
        print("No start time found in issue body; skipping Zoom creation.")
        sys.exit(0)

    # 3) Create Zoom meeting
    try:
        zoom_link = create_zoom_meeting(
            title=f"Issue {issue.number}: {issue.title}",
            start_time=start_time,
            duration_minutes=duration
        )
        # Optionally, post a comment back to the issue with info
        issue.create_comment(f"Zoom link created: {zoom_link}")

    except Exception as e:
        issue.create_comment(f"Error creating Zoom meeting: {e}")
        raise

    # 4) Create a Discourse topic for this new call
    try:
        
        topic_title = f"Discussion for Issue #{issue.title}"
        topic_body = f"This is an automated discussion thread {issue.body}.\n\nZoom Link: {zoom_link}\n\n"
        discourse_topic_response = create_topic(
            title=topic_title,
            body=topic_body,
            category_id=63  # or parse from the issue or your logic
        )
        topic_id = discourse_topic_response.get("topic_id")
        issue.create_comment(f"Discourse topic created with ID: {topic_id}")

    except Exception as e:
        issue.create_comment(f"Error creating Discourse topic: {e}")
        raise

    # You could also track the new Zoom Meeting ID and Discourse ID by adding
    # custom labels or by storing them in your database.

if __name__ == "__main__":
    main()