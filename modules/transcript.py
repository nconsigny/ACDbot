import os
from modules import zoom, discourse

def post_zoom_transcript_to_discourse(meeting_id: str, category_id: int = 63):
    """
    High-level function: 
      1) Fetch a transcript from Zoom for the given meeting_id
      2) Create a Discourse topic with the transcript as the body

    :param meeting_id: Zoom meeting ID (string or int)
    :param category_id: Discourse category ID
    :return: The JSON response from discourse.create_topic
    """
    transcript_text = zoom.fetch_zoom_transcript(meeting_id)

    # If you want to give your new topic a descriptive title:
    topic_title = f"Zoom Transcript for Meeting {meeting_id}"

    # Now create a Discourse topic with the transcript as its content
    topic_data = discourse.create_topic(
        title=topic_title,
        body=transcript_text,
        category_id=category_id
    )
    return topic_data
