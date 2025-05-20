# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

def send_card(webex_api, room_id, card_payload):
  """Sends a card to the specified room"""
  msg_result = webex_api.messages.create(
    roomId=room_id,
    text="If you see this your client cannot render cards",
    attachments=[
      {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": card_payload,
      }
    ],
  )
  return msg_result


def create_good_bad_card(response_type: str):
  """Creates a good/bad response card for the user to fill in"""

  return {
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.3",
    "body": [
      {
        "type": "Container",
        "items": [
          {
            "type": "ColumnSet",
            "columns": [
              {
                "type": "Column",
                "width": "stretch",
                "items": [
                  {
                    "type": "ActionSet",
                    "actions": [
                      {
                        "type": "Action.Submit",
                        "title": "👎 Bad Response",
                        "id": "id_down",
                        "data": {
                          "good_bad_down": "bad",
                          "response_type": response_type,
                        },
                        "style": "destructive",
                      }
                    ],
                    "horizontalAlignment": "Center",
                  }
                ],
              },
              {
                "type": "Column",
                "width": "stretch",
                "items": [
                  {
                    "type": "ActionSet",
                    "actions": [
                      {
                        "type": "Action.Submit",
                        "title": "👍 Good Response",
                        "id": "id_up",
                        "data": {
                          "good_bad_up": "good",
                          "response_type": response_type,
                        },
                        "style": "positive",
                      }
                    ],
                    "horizontalAlignment": "Center",
                  }
                ],
              },
            ],
          }
        ],
      }
    ],
  }


def create_good_options_card():
  """Creates a response card with options for good for the user to fill in"""

  return {
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.3",
    "body": [
      {
        "type": "ActionSet",
        "actions": [
          {
            "type": "Action.Submit",
            "title": "📝 Very Helpful",
            "id": "id_very_helpful",
            "data": {"good_option": "Very Helpful"},
            "style": "positive",
          },
          {
            "type": "Action.Submit",
            "title": "🎯 Accurate",
            "id": "id_accurate",
            "data": {"good_option": "Accurate"},
            "style": "positive",
          },
          {
            "type": "Action.Submit",
            "title": "✅ Simplified My Task",
            "id": "id_simplified_my_task",
            "data": {"good_option": "Simplified My Task"},
            "style": "positive",
          },
          {
            "type": "Action.Submit",
            "title": "❔Other",
            "id": "id_other",
            "data": {"good_option": "Other"},
            "style": "positive",
          },
        ],
        "horizontalAlignment": "Center",
      },
    ],
  }


def create_bad_options_card():
  """Creates a response card with options for bad for the user to fill in"""

  return {
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.3",
    "body": [
      {
        "type": "ActionSet",
        "actions": [
          {
            "type": "Action.Submit",
            "title": "❌ Inaccurate",
            "id": "id_inaccurate",
            "data": {"bad_option": "Inaccurate"},
            "style": "destructive",
          },
          {
            "type": "Action.Submit",
            "title": "✏️ Poorly Formatted",
            "id": "id_poorly_formatted",
            "data": {"bad_option": "Poorly Formatted"},
            "style": "destructive",
          },
          {
            "type": "Action.Submit",
            "title": "💬 Incomplete",
            "id": "id_incomplete",
            "data": {"bad_option": "Incomplete"},
            "style": "destructive",
          },
          {
            "type": "Action.Submit",
            "title": "🧠 Off-Topic",
            "id": "id_off_topic",
            "data": {"bad_option": "Off-Topic"},
            "style": "destructive",
          },
          {
            "type": "Action.Submit",
            "title": "❔Other",
            "id": "id_other",
            "data": {"bad_option": "Other"},
            "style": "destructive",
          },
        ],
        "horizontalAlignment": "Center",
      },
    ],
  }


def create_feedback_card(user_id, date, feedback_option):
  card = {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.3",
    "body": [
      {
        "type": "TextBlock",
        "text": "Outshift Support Bot Feedback Form",
        "weight": "Bolder",
        "size": "Medium",
      },
      {
        "type": "ColumnSet",
        "columns": [
          {
            "type": "Column",
            "width": "stretch",
            "items": [
              {
                "type": "TextBlock",
                "text": user_id,
                "weight": "Bolder",
                "wrap": True,
                "id": "user_id",
              },
              {
                "type": "TextBlock",
                "spacing": "None",
                "text": date,
                "isSubtle": True,
                "wrap": True,
                "id": "date",
              },
            ],
          },
        ],
      },
      {
        "type": "Input.Text",
        "placeholder": "Enter your feedback here",
        "id": "feedback",
        "label": "Please fill in your feedback below",
        "isRequired": True,
        "isMultiline": True,
        "errorMessage": "Please enter your feedback in the text box",
      },
      {
        "type": "ActionSet",
        "actions": [
          {
            "type": "Action.Submit",
            "title": "Cancel",
            "style": "destructive",
            "associatedInputs": "none",
            "id": "button_cancel",
          },
          {
            "type": "Action.Submit",
            "title": "Submit",
            "style": "positive",
            "associatedInputs": "auto",
            "id": "button_submit",
            "data": {"user_id": user_id, "date": date, "feedback_option": feedback_option},
          },
        ],
        "spacing": "None",
        "horizontalAlignment": "Center",
      },
    ],
  }

  return card


def create_user_input_card(input_fields):
  """Creates a user input card with specified input fields."""
  input_elements = []

  for field in input_fields:
    if field.get("field_values"):
      # Create a dropdown menu for fields with predefined values
      input_element = {
        "type": "Input.ChoiceSet",
        "id": field["field_name"],
        "label": field["field_description"],
        "isRequired": True,
        "errorMessage": f"Please select a valid {field['field_name']}",
        "choices": [{"title": value, "value": value} for value in field["field_values"]],
        "style": "compact",  # or "expanded" if you prefer
      }
    else:
      # Default to a text input if no predefined values
      input_element = {
        "type": "Input.Text",
        "id": field["field_name"],
        "placeholder": f"Enter {field['field_name']}",
        "label": field["field_description"],
        "isRequired": False,
        "errorMessage": f"Please enter a valid {field['field_name']}",
      }

    input_elements.append(input_element)

  card = {
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.3",
    "body": input_elements,
    "actions": [{"type": "Action.Submit", "title": "Submit", "data": {"user_input": True}}],
  }

  return card
