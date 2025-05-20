# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
import requests
import json
from requests.auth import HTTPBasicAuth
from multi_agent_jarvis.setup_logging import logging
from langchain_core.tools import tool

from multi_agent_jarvis.agents.jira_agent.tools.jira_user import _get_account_id_from_email
from multi_agent_jarvis.agents.jira_agent.tools._jira_instance import JiraInstanceManager
from multi_agent_jarvis.agents.jira_agent.tools.utils import _urlify_jira_issue_id


@tool
async def create_jira_issue(
  project_key: str, summary: str, description: str, issue_type: str, reporter_email: str
) -> str:
  """
  Create a new generic Jira issue.

  Args:
    project_key (str): Jira Project Key.
    summary (str): The summary of the issue.
    description (str): The description of the issue.
    issue_type (str): The type of the issue (e.g., "Bug", "Task").
    reporter_email (str): The email of the reporter.

  Returns:
    str: The URL of the created Jira issue.
  """
  logging.info(f"Creating a new Jira issue in project: {project_key}")
  try:
    jira_api = JiraInstanceManager.get_jira_instance()
    reporter_id = await _get_account_id_from_email(reporter_email)
    issue_dict = {
      "project": {"key": project_key},
      "summary": summary,
      "description": description,
      "issuetype": {"name": issue_type},
      "reporter": {"id": reporter_id},
    }
    new_issue = jira_api.create_issue(fields=issue_dict)
    urlify_jira_issue_id = await _urlify_jira_issue_id(new_issue.key)
    logging.info(f"Created new Jira issue: {urlify_jira_issue_id}")
    return urlify_jira_issue_id
  except Exception as e:
    logging.error(f"Error creating Jira issue: {e}")
    return {}


@tool
async def assign_jira(issue_key: str, assignee_email: str) -> str:
  """
  Assigns a JIRA ticket to a specified user.

  Args:
    issue_key (str): The key of the JIRA issue to assign.
    assignee_email (str): The email of the user to assign the issue to.

  Returns:
    str: A message indicating the result of the assignment.

  Raises:
    Exception: If the JIRA API request fails or encounters an error.  The exception will contain details about the failure, including the HTTP status code and response text (if available).
  """

  jira_server_url = os.getenv("JIRA_SERVER")
  user_email = os.getenv("JARVIS_JIRA_USER_EMAIL")
  access_token = os.getenv("JARVIS_JIRA_ACCESS_TOKEN")
  auth = HTTPBasicAuth(user_email, access_token)
  headers = {"Accept": "application/json", "Content-Type": "application/json"}
  #####################################
  ### Assign the ticket to the user ###
  #####################################
  try:
    assignee_url = f"{jira_server_url}/rest/api/3/issue/{issue_key}/assignee"

    payload = json.dumps({"accountId": await _get_account_id_from_email(assignee_email)})

    response = requests.put(assignee_url, headers=headers, data=payload, auth=auth)

    if response.status_code == 204:
      urlify_jira_issue_id = await _urlify_jira_issue_id(issue_key)
      logging.info(f"JIRA ticket {issue_key} assigned to {assignee_email} successfully.")
      return f"JIRA ticket assigned successfully {urlify_jira_issue_id}."
    else:
      logging.error(
        f"Failed to assign JIRA ticket {issue_key} to {assignee_email}. Status code: {response.status_code}, Response: {response.text}"
      )
  except Exception as e:
    logging.error(f"Failed to assign JIRA ticket {issue_key} to {assignee_email}. Error: {e}")
    raise e
  return "Failed to assign JIRA ticket."


@tool
async def update_issue_reporter(issue_key: str, reporter_email: str) -> str:
  """
  Update the reporter of a Jira issue.

  Args:
    issue_key (str): Jira Issue ID.
    reporter_email (str): The email of the new reporter.

  Returns:
    str: A message indicating the result of the update.
  """
  logging.info(f"Updating reporter of ticket: {issue_key}")
  try:
    jira_api = JiraInstanceManager.get_jira_instance()
    reporter_id = await _get_account_id_from_email(reporter_email)
    issue = jira_api.issue(issue_key)
    issue.update(reporter={"id": reporter_id})
    logging.info("Reporter updated successfully.")
    urlify_jira_issue_id = await _urlify_jira_issue_id(issue_key)
    return f"Reporter updated successfully on Jira {urlify_jira_issue_id}."
  except Exception as e:
    logging.error(f"Error updating reporter: {e}")
    return "Failed to update reporter."


async def _add_new_label_to_issue(issue_key: str, label: str) -> str:
  """
  Add a new label to a Jira issue.

  Args:
    issue_key (str): Jira Issue ID.
    label (str): The label to add.

  Returns:
    str: A message indicating the result of the operation.
  """
  logging.info(f"Adding label '{label}' to ticket: {issue_key}")
  try:
    jira_api = JiraInstanceManager.get_jira_instance()
    issue = jira_api.issue(issue_key)
    issue.fields.labels.append(label)
    issue.update(fields={"labels": issue.fields.labels})
    logging.info("Label added successfully.")
    urlify_jira_issue_id = await _urlify_jira_issue_id(issue_key)
    return f"Label added successfully on Jira {urlify_jira_issue_id}."
  except Exception as e:
    logging.error(f"Error adding label: {e}")
    return "Failed to add label."


@tool
async def add_new_label_to_issue(issue_key: str, label: str) -> str:
  """
  Add a new label to a Jira issue.

  Args:
    issue_key (str): Jira Issue ID.
    label (str): The label to add.

  Returns:
    str: A message indicating the result of the operation.
  """
  return await _add_new_label_to_issue(issue_key, label)


@tool
async def get_jira_issue_details(issue_key: str) -> dict:
  """
  Retrieve the details of a Jira ticket based on its key.

  Args:
    issue_key (str): Jira Issue ID.

  Returns:
    dict: A dictionary containing the details of the ticket.
  """
  logging.info(f"Retrieving details for ticket: {issue_key}")
  try:
    jira_api = JiraInstanceManager.get_jira_instance()
    issue = jira_api.issue(issue_key)
    urlify_jira_issue_id = await _urlify_jira_issue_id(issue.key)
    ticket_details = {
      "key": urlify_jira_issue_id,
      "summary": issue.fields.summary,
      "description": issue.fields.description,
      "status": issue.fields.status.name,
      "priority": issue.fields.priority.name,
      "reporter": issue.fields.reporter.displayName,
      "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
      "created": issue.fields.created,
      "updated": issue.fields.updated,
    }
    logging.info(f"Ticket details: {ticket_details}")
    return ticket_details
  except Exception as e:
    logging.error(f"Error retrieving ticket details: {e}")
    return {}
