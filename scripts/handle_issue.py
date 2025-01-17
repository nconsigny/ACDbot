import os
import sys
import argparse
from github import Github

# Import your custom modules
from modules import discourse, zoom

def handle_github_issue(issue_number: int, repo_name: str):
    """
    Fetches the specified GitHub issue, extracts its title and body,
    then creates a Discourse topic using the issue title as the topic title
    and its body as the topic content.
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
    try:
        start_time, duration = parse_issue_for_time(issue_body)
        zoom_link = zoom.create_meeting(
            title=f"Issue {issue.number}: {issue_title}",
            start_time=start_time,
            duration_minutes=duration
        )
        # Post Zoom link as a comment
        issue.create_comment(f"Zoom meeting created: {zoom_link}")
    except Exception as e:
        issue.create_comment(f"Error creating Zoom meeting: {e}")

    # 5. Post Discourse Topic Link as a Comment
    try:
        topic_id = discourse_response.get("topic_id")
        discourse_url = f"{os.environ.get('DISCOURSE_BASE_URL', 'https://ethereum-magicians.org')}/t/{topic_id}"
        issue.create_comment(f"Discourse topic created: {discourse_url}")
    except Exception as e:
        issue.create_comment(f"Error posting Discourse topic: {e}")

def parse_issue_for_time(issue_body: str):
    """
    Parses the issue body to extract start time and duration.
    Adjust the regex or parsing logic according to your issue formatting.
    """
    import re
    from datetime import datetime

    # Example: Extract ISO 8601 datetime and duration in minutes
    iso_match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", issue_body)
    duration_match = re.search(r"Duration:\s*(\d+)\s*minutes", issue_body, re.IGNORECASE)

    if iso_match:
        start_time = iso_match.group(0)
    else:
        # Default start time or raise an error
        start_time = datetime.utcnow().isoformat() + "Z"

    if duration_match:
        duration = int(duration_match.group(1))
    else:
        duration = 60  # Default duration

    return start_time, duration

def main():
    parser = argparse.ArgumentParser(description="Handle GitHub issue and create Discourse topic.")
    parser.add_argument("--issue_number", required=True, type=int, help="GitHub issue number")
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., 'org/repo')")
    args = parser.parse_args()

    handle_github_issue(issue_number=args.issue_number, repo_name=args.repo)

if __name__ == "__main__":
    main()