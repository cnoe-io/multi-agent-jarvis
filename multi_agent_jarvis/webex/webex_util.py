# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from multi_agent_jarvis.models import Feedback
from multi_agent_jarvis.setup_logging import logging
from webexteamssdk import WebexTeamsAPI
import os

WEBEX_ACCESS_TOKEN = os.getenv("WEBEX_ACCESS_TOKEN")


def send_feedback_to_webex(feedback: Feedback, user_email: str):
  """
  Sends a feedback card to a Webex room. Supports the JARVIS_DRYRUN env var.

  Args:
    feedback (Feedback): The feedback object containing title, description, and rating.
    user_email (str): The email of the user sending the feedback.
  """
  if os.getenv("JARVIS_DRYRUN") == "True":
    logging.info("Not sending feedback due to dryrun")
    return
  logging.info(
    f"Feedback received from {user_email}: Type - {feedback.type}, Reason - {feedback.reason}, AdditionalFeedback - {feedback.additionalFeedback}, Timestamp - {feedback.timestamp}, Message - {feedback.message}"
  )
  WEBEX_ROOM_ID = os.getenv("WEBEX_ROOM_ID")

  api = WebexTeamsAPI(access_token=WEBEX_ACCESS_TOKEN)

  logging.info("Preparing to send user feedback to Webex.")
  card = {
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.2",
      "body": [
        {
          "type": "TextBlock",
          "text": "User Feedback Received",
          "weight": "Bolder",
          "size": "Medium",
        },
        {"type": "TextBlock", "text": f"From: {user_email}", "wrap": True},
        {"type": "TextBlock", "text": f"Type: {feedback.type}", "wrap": True},
        {
          "type": "TextBlock",
          "text": f"Reason: {feedback.reason}",
          "wrap": True,
        },
        {
          "type": "TextBlock",
          "text": f"Additional Feedback: {feedback.additionalFeedback}",
          "wrap": True,
        },
        {
          "type": "TextBlock",
          "text": f"Timestamp: {feedback.timestamp}",
          "wrap": True,
        },
        {
          "type": "TextBlock",
          "text": f"Message: {feedback.message}",
          "wrap": True,
        },
      ],
    },
  }

  try:
    logging.info(f"Sending feedback card to Webex room ID: {WEBEX_ROOM_ID}")
    message = api.messages.create(roomId=WEBEX_ROOM_ID, markdown="User feedback received:", attachments=[card])
    logging.info(f"Feedback card sent successfully. Message ID: {message.id}")
  except Exception as e:
    logging.error(f"An error occurred while sending the feedback card: {e}")


def send_webex_message_to_person(recipient_email: str, message: str, attachments: dict = None):
  """
  Sends a message to a specific person on Webex. Supports the JARVIS_DRYRUN env var.

  Args:
    recipient_email (str): The email of the recipient.
    message (str): The message to be sent.
    attachments (dict, optional): Attachments to be included in the message. Defaults to None.
  """
  if os.getenv("JARVIS_DRYRUN") == "True":
    logging.info("Not sending webex message due to dryrun")
    return
  try:
    api = WebexTeamsAPI(access_token=WEBEX_ACCESS_TOKEN)
    logging.debug("Fetching recipient information.")
    recipient = api.people.list(email=recipient_email.strip())
    recipient_list = list(recipient)
    logging.debug(f"Recipient list for {recipient_email}: {recipient_list}")
    if not recipient_list:
      raise ValueError(f"No Webex user found with email {recipient_email}")
    recipient_id = recipient_list[0].id

    logging.info(f"Recipient ID: {recipient_id}")
    if attachments:
      message_to_person = api.messages.create(toPersonId=recipient_id, markdown=message, attachments=[attachments])
    else:
      message_to_person = api.messages.create(toPersonId=recipient_id, markdown=message)
    logging.info(f"Message sent to person. Message ID: {message_to_person.id}")
  except Exception as e:
    logging.error(f"An error occurred while sending the message to person: {e}")


def send_webex_message_to_room(message: str, attachments: dict = None):
  """
  Sends a message to a Webex room. Supports the JARVIS_DRYRUN env var.

  Args:
    room_id (str): The ID of the Webex room.
    message (str): The message to be sent.
    attachments (dict, optional): Attachments to be included in the message. Defaults to None.
  """
  if os.getenv("JARVIS_DRYRUN") == "True":
    logging.info("Not sending webex message due to dryrun")
    return
  try:
    room_id = os.getenv("WEBEX_ROOM_ID")
    api = WebexTeamsAPI(access_token=WEBEX_ACCESS_TOKEN)
    if room_id:
      if attachments:
        message_to_room = api.messages.create(roomId=room_id, markdown=message, attachments=[attachments])
      else:
        message_to_room = api.messages.create(roomId=room_id, markdown=message)
      logging.info(f"Message sent to room. Message ID: {message_to_room.id}")
    else:
      logging.warning("WEBEX_ROOM_ID is not set. Skipping sending message to room.")
  except Exception as e:
    logging.error(f"An error occurred while sending the message to room: {e}")
