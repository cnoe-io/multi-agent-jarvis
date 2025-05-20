# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.agents.jira_agent.tools.jira_user import _get_jira_assignee

JARVIS_JIRA_USER_DISPLAYNAME = os.getenv("JARVIS_JIRA_USER_DISPLAYNAME")

async def process_jira_webhook(jira_payload):
  """
  Processes a JIRA webhook payload and extracts relevant information based on the event type.
  Args:
    jira_payload: An object containing the JIRA webhook data. It is expected to have methods to extract
            issue key, summary, description, webhook event, issue event type name, comment author,
            comment body, and assigned user display name.
  Returns:
    tuple: A tuple containing the issue key and a formatted question string if the event is an issue assignment
         to JARVIS_JIRA_USER_DISPLAYNAME. Returns (None, None) for other events or conditions.
  """
  logging.info("Processing JIRA webhook...")

  # Extract necessary information from the webhook data
  # timestamp = jira_payload.get_timestamp()
  issue_key = jira_payload.get_issue_key()
  issue_summary = jira_payload.get_issue_summary()
  issue_description = jira_payload.get_issue_description()
  llm_question = f"Summary: {issue_summary} Description: {issue_description}"
  logging.info(f"[Extract Info] Issue Key: {issue_key}, Summary: {issue_summary}, Description: {issue_description}")

  # Check for different webhook events
  webhook_event = jira_payload.get_webhook_event()
  issue_event_type_name = jira_payload.get_issue_event_type_name()

  if webhook_event == "comment_created":
    logging.info("*" * 80)
    logging.info(f"Processing {webhook_event} event.")
    logging.info("*" * 80)
    author = jira_payload.get_comment_author()
    logging.info(f"Author: {author}")
    issue_assignee = await _get_jira_assignee(issue_key)
    logging.info(f"Issue Assignee: {issue_assignee}")
    if author == JARVIS_JIRA_USER_DISPLAYNAME:
      logging.info(f"Skipping comment: Comment made by {author}")
      return None, None, None
    if issue_assignee is None:
      logging.info("Skipping Comment: Issue has no assignee.")
      return None, None, None
    if issue_assignee.lower() != JARVIS_JIRA_USER_DISPLAYNAME.lower():
      logging.info(f"Skipping Comment: Issue not assigned to {JARVIS_JIRA_USER_DISPLAYNAME}")
      return None, None, None
    comment = jira_payload.get_comment_body()
    logging.info(f"Comment Body: {comment}")
    logging.info("-" * 80)
    logging.info(f"[comment_created] Issue Key: {issue_key}, Comment Author: {author} Comment Body: {comment}")
    logging.info("-" * 80)
    new_comment = f"Comment by {author}: {comment}"
    logging.info(f"New Comment: {new_comment}")
    return issue_key, new_comment, webhook_event
  elif issue_event_type_name == "issue_assigned":
    logging.info("*" * 80)
    logging.info(f"Processing {issue_event_type_name} event.")
    logging.info("*" * 80)
    assigned_user_displayname = jira_payload.get_assigned_user_displayname()
    labels = jira_payload.get_labels()
    if assigned_user_displayname and assigned_user_displayname.lower() == JARVIS_JIRA_USER_DISPLAYNAME.lower():
      if labels and ("JARVIS_AUTOMATION_TRACKING" in labels or "JARVIS_AGENT_AT_WORK" in labels):
        logging.info(
          f"[issue_assigned] Skipping issue with JARVIS_AUTOMATION_TRACKING or JARVIS_AGENT_AT_WORK label. {labels}"
        )
      else:
        logging.info(
          "[issue_assigned] Bingo! Assigned user is {JARVIS_JIRA_USER_DISPLAYNAME} and no JARVIS_AUTOMATION_TRACKING label."
        )
        if issue_key and llm_question:
          return issue_key, llm_question, issue_event_type_name
    else:
      logging.info(f"Skipping issue assignment to {assigned_user_displayname}")
  return None, None, None
