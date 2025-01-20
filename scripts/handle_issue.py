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

    1) A single start time and a separate "Duration in minutes" line, e.g.,
         - We will not have a meeting on [Jan 16, 2025, 14:00 UTC](...)
         - Duration in minutes
         - 90

    2) A start time with an end time separated by a dash, e.g.,
         - We will not have a meeting on [Jan 18, 2025, 14:00-15:30 UTC](...)
       This implies a 90-minute duration (14:00 → 15:30).

    If any values can't be found or parsed, a ValueError is raised.
    """
    import re
    from datetime import datetime

    # -------------------------------------------------------------------------
    # 1) Improved regex for the bracketed date/time:
    #    Accepts patterns like [Jan 18 2025 14:00 UTC](...) or [Jan 18, 2025, 14:00 UTC](...)
    #    Also optionally [-15:30] for an end time, like 14:00-15:30
    # -------------------------------------------------------------------------
    date_pattern = re.compile(
        r"""
        \[                         # A literal '['
        (                          # Group 1 => the entire start datetime text
          [A-Za-z]{3}              # Month abbreviation (any case) e.g., 'Jan', 'jan'
          [,\s]+                   # One or more commas/spaces
          \d{1,2}                  # Day, e.g., '18'
          (?:[,\s]+)\d{4}          # One or more commas/spaces, followed by 4-digit year
          (?:[,\s]+)\d{1,2}:\d{2}  # One or more commas/spaces, then hour:minute
        )
        (?:-(\d{1,2}:\d{2}))?      # Group 2 => optional end time after '-', e.g. '-15:30'
        \s*UTC\]\(                 # Then " UTC]("
        """,
        re.IGNORECASE | re.VERBOSE
    )

    match = date_pattern.search(issue_body)
    if not match:
        raise ValueError("Missing or invalid date/time format (couldn't match bracketed time).")

    datetime_str = match.group(1)  # e.g. "jan 18 2025 14:00" or "Jan 18, 2025, 14:00"
    end_time_str = match.group(2)  # e.g. "15:30" if present, or None

    # -------------------------------------------------------------------------
    # 2) Normalize the start datetime string to handle the month abbreviation
    #    Python's datetime.strptime() expects "Jan" not "jan"/"JAN".
    # -------------------------------------------------------------------------
    # Example: "jan 18 2025 14:00" -> "Jan 18 2025 14:00"
    if len(datetime_str) >= 3:
        datetime_str = datetime_str[0:3].title() + datetime_str[3:]

    datetime_str = datetime_str.replace(",", " ")
    # Collapse multiple spaces => single space
    datetime_str = re.sub(r"\s+", " ", datetime_str).strip()

    # Parse the start datetime with strptime
    # Format now expected: "Jan 18 2025 14:00"
    try:
        start_dt = datetime.strptime(datetime_str, "%b %d %Y %H:%M")
    except ValueError as e:
        raise ValueError(f"Unable to parse the start time: {e}")

    start_time_utc = start_dt.isoformat() + "Z"

    # -------------------------------------------------------------------------
    # 3) Parse the optional end time if present
    # -------------------------------------------------------------------------
    duration_minutes = None
    if end_time_str:
        # e.g. "14:00-15:30" => end_time_str = "15:30"
        # We'll construct "Jan 18 2025 15:30"
        end_datetime_str = f"{start_dt.strftime('%b %d %Y')} {end_time_str}"

        try:
            end_dt = datetime.strptime(end_datetime_str, "%b %d %Y %H:%M")
        except ValueError as e:
            raise ValueError(f"Unable to parse the end time: {e}")

        if end_dt <= start_dt:
            raise ValueError("End time is not after start time; cannot compute positive duration.")
        duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
    else:
        # ---------------------------------------------------------------------
        # 4) Extract "Duration in minutes" if no end time was provided
        #    We'll be lenient with leading bullets/dashes. We'll let them appear
        #    on both lines. We also allow multiple spaces. We allow \r\n or \n.
        # ---------------------------------------------------------------------
        duration_pattern = re.compile(
            r"""
            (?sm)                    # DOTALL (.) matches newlines, MULTILINE for ^$
            ^[ \t\-]*                # Start of a line, optional spaces/dashes
            Duration\s+in\s+minutes # The key phrase, ignoring case because re.IGNORECASE
            [ \t]*[\r\n]+            # Then only whitespace until a line break
            ^[ \t\-]*                # On the next line, optional spaces/dashes
            (\d+)                    # The actual number of minutes (Group 1)
            """,
            re.IGNORECASE | re.VERBOSE
        )
        match_duration = duration_pattern.search(issue_body)
        if not match_duration:
            raise ValueError(
                "Missing or invalid duration format. Provide 'Duration in minutes' or a start-end time in bracketed text."
            )
        duration_minutes = int(match_duration.group(1))

    return start_time_utc, duration_minutes


def main():
    parser = argparse.ArgumentParser(description="Handle GitHub issue and create/update Discourse topic.")
    parser.add_argument("--issue_number", required=True, type=int, help="GitHub issue number")
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., 'org/repo')")
    args = parser.parse_args()

    handle_github_issue(issue_number=args.issue_number, repo_name=args.repo)


if __name__ == "__main__":
    main()