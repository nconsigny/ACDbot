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
         [Jan 16, 2025, 14:00 UTC](https://savvytime.com/...)
         Duration in minutes
         90

    2) A start time with an end time separated by a dash, e.g.,
         [Jan 18, 2025, 14:00-15:30 UTC](https://savvytime.com/...)
       This implies a 90-minute duration (14:00 → 15:30).

    The parser is improved to handle uppercase, lowercase, or mixed-case month abbreviations
    by normalizing the month portion before parsing. Commas around the day/year are also optional.

    If these values can't be found or parsed, a ValueError is raised.
    """
    import re
    from datetime import datetime

    # This pattern matches:
    #  - "[Jan 18, 2025, 14:00 UTC](...)"
    #  - "[jan 18 2025 14:00 UTC](...)"
    #  - "[Jan 18 2025 14:00-15:30 UTC](...)"
    #    etc.
    pattern = re.compile(
        r"\[([A-Za-z]{3}\s+\d{1,2}(?:,\s*)?\d{4}(?:,\s*)?\d{1,2}:\d{2})(-\d{1,2}:\d{2})?\s*UTC\]\(",
        re.IGNORECASE
    )

    match = pattern.search(issue_body)
    if not match:
        raise ValueError("Missing or invalid date/time format (couldn't match bracketed time).")

    # Extract the date/time portion, e.g. "jan 18 2025 14:00" or "Jan 18, 2025, 14:00"
    datetime_str = match.group(1).strip()

    # Normalize the first three letters for the month abbreviation so "jan" => "Jan", "seP" => "Sep", etc.
    # This ensures datetime.strptime() will accept the month.
    if len(datetime_str) >= 3:
        month_part = datetime_str[:3].title()  # e.g., "Jan"
        remainder = datetime_str[3:]          # e.g., " 18 2025 14:00"
        datetime_str = month_part + remainder

    # Try parsing the start time in two ways (with or without commas).
    start_dt = None
    for fmt in ("%b %d %Y %H:%M", "%b %d, %Y, %H:%M"):
        try:
            start_dt = datetime.strptime(datetime_str, fmt)
            break
        except ValueError:
            pass

    if not start_dt:
        raise ValueError("Unable to parse the start time in the specified format.")

    start_time_utc = start_dt.isoformat() + "Z"

    # Check for optional end time segment (e.g. "-15:30")
    end_segment = match.group(2)
    duration_minutes = None

    if end_segment:
        # Remove the leading dash, e.g. "-15:30" => "15:30"
        end_time_str = end_segment.lstrip("-").strip()

        # We also need to handle the month/day/year for the end time, but we already have it in start_dt.
        # We'll reconstruct a new date string for the end time using the same approach.
        # Example: "Jan 18 2025" + " 15:30"
        date_prefix = start_dt.strftime("%b %d %Y ")
        end_datetime_str = date_prefix + end_time_str

        # Normalize the month in case the start_dt month was originally lowercase
        # (Not always necessary if date_prefix is from strftime, which already yields capitalized month.)
        if len(end_datetime_str) >= 3:
            end_datetime_str = end_datetime_str[0:3].title() + end_datetime_str[3:]

        end_dt = None
        # Attempt parsing with or without commas in the same spirit:
        for fmt_end in ("%b %d %Y %H:%M", "%b %d, %Y, %H:%M"):
            try:
                end_dt = datetime.strptime(end_datetime_str, fmt_end)
                break
            except ValueError:
                pass

        if not end_dt:
            raise ValueError("Unable to parse the end time in the specified format.")

        if end_dt <= start_dt:
            raise ValueError("End time is not after start time; cannot compute positive duration.")

        duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
    else:
        # If user didn't provide an end time, look for a "Duration in minutes" line in the rest of the issue.
        import re
        duration_match = re.search(
            r"Duration in minutes\s*\n-?\s*(\d+)",
            issue_body,
            re.IGNORECASE
        )
        if not duration_match:
            raise ValueError(
                "Missing or invalid duration format. Provide 'Duration in minutes' or a start-end time in bracketed text."
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