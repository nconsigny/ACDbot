import os
import sys
import pathlib

# Add the project root to sys.path
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from scripts.handle_issue import parse_issue_for_time

def test_parse_issue():
    test_cases = [
        {
            "description": "Format with separate duration",
            "issue_body": """
            # Rollcall ACDbot testing

            - We will not have a meeting on [Jan 16, 2025, 14:00 UTC](https://savvytime.com/converter/utc/jan-16-2025/2pm)
            - Duration in minutes
            - 90

            # Agenda 

            - Testing the discourse
            - Testing the telegram bot

            Other comments and resources
            """
        },
        {
            "description": "Format with start and end time",
            "issue_body": """
            # Rollcall ACDbot testing

            - We will not have a meeting on [Jan 18, 2025, 14:00-15:30 UTC](https://savvytime.com/converter/utc/jan-18-2025/2pm)

            # Agenda 

            - Testing the discourse
            - Testing the telegram bot

            Other comments and resources
            """
        },
        {
            "description": "Lowercase month without commas",
            "issue_body": """
            # Protocol call ACDbot testing

            - We will not have a meeting on [jan 18 2025 14:00 UTC](https://savvytime.com/converter/utc/jan-18-2025/2pm)
            - Duration in minutes
            - 90

            # Agenda 

            - Testing the discourse
            - Testing the telegram bot

            Other comments and resources
            EDIT TEST n°10
            """
        },
        {
            "description": "Lowercase month with duration line",
            "issue_body": """
            # Protocol call ACDbot testing

            - We will not have a meeting on [jan 18 2025 14:00-15:30 UTC](https://savvytime.com/converter/utc/jan-18-2025/2pm)

            # Agenda 

            - Testing the discourse
            - Testing the telegram bot

            Other comments and resources
            EDIT TEST n°10
            """
        },
        {
            "description": "Incorrect format",
            "issue_body": """
            # Protocol call ACDbot testing

            - We will not have a meeting on Jan 18, 2025 at 14:00 UTC
            - Duration in minutes
            - 90

            # Agenda 

            - Testing the discourse
            - Testing the telegram bot

            Other comments and resources
            EDIT TEST n°10
            """
        },
        {
            "description": "End time before start time",
            "issue_body": """
            # Protocol call ACDbot testing

            - We will not have a meeting on [Jan 20, 2025, 16:00-15:30 UTC](https://savvytime.com/converter/utc/jan-20-2025/2pm)

            # Agenda 

            - Testing the discourse
            - Testing the telegram bot

            Other comments and resources
            EDIT TEST n°10
            """
        },
        {
            "description": "Additional spaces and dashes",
            "issue_body": """
            # Protocol call ACDbot testing

            - We will not have a meeting on [jan 19, 2025, 13:00 UTC](https://savvytime.com/converter/utc/jan-19-2025/2pm)
            -   Duration    in    minutes
            -    60

            # Agenda 

            - Testing the discourse
            - Testing the telegram bot

            Other comments and resources
            EDIT TEST n°11
            """
        },
    ]

    for case in test_cases:
        print(f"---\nTest Case: {case['description']}")
        try:
            start_time, duration = parse_issue_for_time(case["issue_body"])
            print(f"Start Time (UTC): {start_time}")
            print(f"Duration (minutes): {duration}")
        except ValueError as ve:
            print(f"Error: {ve}")

if __name__ == "__main__":
    test_parse_issue()
