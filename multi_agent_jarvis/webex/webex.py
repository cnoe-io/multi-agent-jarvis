# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from multi_agent_jarvis.setup_logging import logging as log
import httpx
from httpx_sse import connect_sse
from multi_agent_jarvis.models import ChatBotQuestion, Feedback
import os
import json

from multi_agent_jarvis.webex.utils.cards.cards import (
  create_good_bad_card,
  create_good_options_card,
  create_bad_options_card,
  create_feedback_card,
  create_user_input_card,
  send_card,
)
from multi_agent_jarvis.webex.utils.webexwebsocket import WebexMessage

# Instances
from multi_agent_jarvis.webex.instance import WebexInstanceManager

webex_api = None


def submit_question(question: ChatBotQuestion, user_email: str):
  url = "http://localhost:8000/submit_question"
  headers = {"USER_EMAIL": user_email}
  with httpx.Client() as client:
    response = client.post(url, data=question.json(), headers=headers, timeout=5.0)
    response_data = response.json()
    log.info(f"response_data: {response_data}")
    # Assume the response contains a 'chat_id' field
    return response_data.get("chat_id")


def submit_feedback(feedback: Feedback, user_email: str):
  url = "http://localhost:8000/submit_feedback"
  headers = {"USER_EMAIL": user_email}
  with httpx.Client() as client:
    response = client.post(url, data=feedback.json(), headers=headers, timeout=5.0)
    response_data = response.json()
    log.info(f"response_data: {response_data}")
    return response_data


def process_event(event, room_id):
  log.info(event)
  if event.event in {"data", "error"} and hasattr(event, "data"):
    try:
      response = json.loads(event.data)
    except json.JSONDecodeError as e:
      log.error(f"{type(e).__name__}: {e}")
      response = {"answer": "Error decoding Jarvis response"}
    query_response = response.get("answer", "Missing response from Jarvis")
    if query_response.strip():
      webex_api.messages.create(roomId=room_id, markdown=query_response.strip())
      # Check for user input requirement
      if "metadata" in response and response["metadata"].get("user_input") and response["metadata"].get("input_fields"):
        input_fields = response["metadata"]["input_fields"]
        user_input_card = create_user_input_card(input_fields)
        send_card(webex_api, room_id, user_input_card)
  elif event.event == "end":
    good_bad_card = create_good_bad_card(response_type="jarvis_agent")
    send_card(webex_api, room_id, good_bad_card)
  else:
    log.warning(f"Unknown event type: {event}")


def _process_message(room_id, user_email, text, user_files=[]):
  chat_id = submit_question(ChatBotQuestion(chat_id=room_id, question=text, user_files=user_files), user_email)

  webex_api.messages.create(roomId=room_id, text="Working on it...")

  if chat_id != room_id:
    log.warning("Chat ID not equal to room ID")

  url = f"http://localhost:8000/get_answer_stream/{chat_id}"
  headers = {"USER_EMAIL": user_email}
  with httpx.Client() as client:
    with connect_sse(client, "GET", url, headers=headers, timeout=60.0) as event_source:
      for event in event_source.iter_sse():
        process_event(event, room_id)


def process_message(message_obj):
  room_id = message_obj.roomId
  user_email = message_obj.personEmail
  user_files = message_obj.files or []
  text = message_obj.text
  _process_message(room_id, user_email, text, user_files)


def process_card(action_obj):
  inputs = action_obj.inputs
  user_emails = webex_api.people.get(action_obj.personId).emails
  if not user_emails:
    log.warning("Missing user email, skipping feedback")
    return
  user_email = user_emails[0]

  if not inputs:
    webex_api.messages.delete(action_obj.messageId)
  elif "user_input" in inputs:
    # Process user input card submission
    user_input_text = "\n".join(f"{key}: {value}" for key, value in inputs.items() if key != "user_input")
    webex_api.messages.delete(action_obj.messageId)
    _process_message(action_obj.roomId, user_email, user_input_text)
  else:
    process_feedback_card(inputs, action_obj, user_email)


def process_feedback_card(inputs, action_obj, user_email):
  if "feedback" in inputs:
    """Feedback Card Submission"""
    date = inputs.get("date")
    feedback = inputs.get("feedback")
    feedback_option = inputs.get("feedback_option")

    submit_feedback(
      Feedback(
        type="webex",
        reason=feedback_option,
        additionalFeedback="",
        timestamp=date,
        message=feedback,
      ),
      user_email,
    )

    # Submission Message in the user's bot channel
    webex_api.messages.create(roomId=action_obj.roomId, text="Thank you for giving your feedback!")
  elif "good_bad_down" in inputs:
    # Bad Response Card Submission
    send_card(webex_api, action_obj.roomId, create_bad_options_card())
  elif "good_bad_up" in inputs:
    # Good Response Card Submission
    send_card(webex_api, action_obj.roomId, create_good_options_card())
  elif "good_option" in inputs:
    if inputs["good_option"] == "Other":
      feedback_card = create_feedback_card(user_email, str(action_obj.created), inputs["good_option"])
      send_card(webex_api, action_obj.roomId, feedback_card)
    else:
      submit_feedback(
        Feedback(
          type="webex",
          reason="",
          additionalFeedback="",
          timestamp=str(action_obj.created),
          message=inputs["good_option"],
        ),
        user_email,
      )
  elif "bad_option" in inputs:
    # Always ask for feedback in bad options
    feedback_card = create_feedback_card(user_email, str(action_obj.created), inputs["bad_option"])
    send_card(webex_api, action_obj.roomId, feedback_card)

  webex_api.messages.delete(action_obj.messageId)


def jarvis_webex():
  # === Setup Bots and Webex APIs ===
  access_token = os.getenv("WEBEX_ACCESS_TOKEN")
  if not access_token:
    raise ValueError("Missing WEBEX_ACCESS_TOKEN env var")
  webex = WebexMessage(access_token=access_token, on_message=process_message, on_card=process_card)
  global webex_api
  webex_api = WebexInstanceManager.get_instance(access_token)

  log.info("\n\n___Bot_started_____")
  webex.run()
