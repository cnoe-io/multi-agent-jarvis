# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
import requests
from requests.auth import HTTPBasicAuth
from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.agents.jira_agent.tools._jira_instance import JiraInstanceManager
from langchain_core.tools import tool
from multi_agent_jarvis.dryrun_utils import dryrun_response
from multi_agent_jarvis.agents.jira_agent.tools.dryrun.mock_responses import JIRA_GET_ACCOUNT_ID_FROM_EMAIL_MOCK_RESPONSE


async def _get_jira_assignee(issue_key: str) -> str:
  """Retrieves the assignee's display name from a Jira issue.
  Args:
    issue_key (str): The key of the Jira issue to retrieve the assignee from.
  Returns:
    str: The display name of the assignee, or None if the issue does not exist,
       the assignee is not set, or if there was an error retrieving the issue details.
  """
  jira_server_url = os.getenv("JIRA_SERVER")
  logging.debug(f"JIRA_SERVER: {jira_server_url}")
  user_email = os.getenv("JARVIS_JIRA_USER_EMAIL")
  logging.debug(f"JARVIS_JIRA_USER_EMAIL: {user_email}")
  access_token = os.getenv("JARVIS_JIRA_ACCESS_TOKEN")
  auth = HTTPBasicAuth(user_email, access_token)
  headers = {"Accept": "application/json", "Content-Type": "application/json"}
  issue_url = f"{jira_server_url}/rest/api/3/issue/{issue_key}"
  logging.info(f"issue_url: {issue_url}")
  issue_response = requests.get(issue_url, headers=headers, auth=auth)
  if issue_response.status_code == 200:
    issue_data = issue_response.json()
    assignee_field = issue_data.get("fields", {}).get("assignee")
    if assignee_field is None:
      logging.info("Assignee is None")
      return None
    assignee = assignee_field.get("displayName")
    logging.info(f"assignee: {assignee}")
    return assignee
  else:
    logging.error(
      f"Failed to retrieve issue details. Status code: {issue_response.status_code}, Response: {issue_response.text}"
    )
    return None


@tool
async def get_jira_assignee(issue_key: str) -> str:
  """
  Retrieves the assignee's display name of a JIRA issue.

  Args:
    issue_key: JIRA Issue ID.
  Returns:
    str: The display name of the assignee, or None if there is no assignee.
  """
  return await _get_jira_assignee(issue_key)


@tool
async def get_jira_reporter_displayname(issue_key: str) -> str:
  """
  Retrieves the display name of the reporter of a JIRA issue.

  Args:
    issue_key (str): JIRA Issue ID.

  Returns:
    str: The display name of the reporter, or None if not found.
  """
  jira_server_url = os.getenv("JIRA_SERVER")
  user_email = os.getenv("JARVIS_JIRA_USER_EMAIL")
  access_token = os.getenv("JARVIS_JIRA_ACCESS_TOKEN")
  auth = HTTPBasicAuth(user_email, access_token)
  headers = {"Accept": "application/json", "Content-Type": "application/json"}
  issue_url = f"{jira_server_url}/rest/api/3/issue/{issue_key}"
  issue_response = requests.get(issue_url, headers=headers, auth=auth)
  if issue_response.status_code == 200:
    issue_data = issue_response.json()
    reporter = issue_data.get("fields", {}).get("reporter", {}).get("displayName")
    return reporter
  else:
    logging.error(
      f"Failed to retrieve issue details. Status code: {issue_response.status_code}, Response: {issue_response.text}"
    )
    return None


async def get_jira_reporter_account_id(issue_key: str) -> str:
  """
  Retrieves the account ID of the reporter of a JIRA issue.

  Args:
    issue_key (str): JIRA Issue ID.

  Returns:
    str: The account ID of the reporter, or None if not found or an error occurs.
  """
  jira_server_url, auth, headers = JiraInstanceManager.get_auth_instance()

  issue_url = f"{jira_server_url}/rest/api/3/issue/{issue_key}"
  issue_response = requests.get(issue_url, headers=headers, auth=auth)
  if issue_response.status_code == 200:
    issue_data = issue_response.json()
    reporter_account_id = issue_data.get("fields", {}).get("reporter", {}).get("accountId")
    return reporter_account_id
  else:
    logging.error(
      f"Failed to retrieve issue details. Status code: {issue_response.status_code}, Response: {issue_response.text}"
    )
    return None


@dryrun_response(JIRA_GET_ACCOUNT_ID_FROM_EMAIL_MOCK_RESPONSE)
async def _get_account_id_from_email(email: str) -> str:
  """
  Retrieves the account ID associated with a given email address in JIRA.

  Args:
    email (str): The email address of the user whose account ID is to be retrieved.

  Returns:
    str: The account ID of the user, as a string. Returns None if the user is not found or if an error occurs.

  Raises:
    Exception: If the JIRA API request fails or encounters an error. The exception will contain details about the failure, including the HTTP status code and response text (if available).
  """
  jira_server_url, auth, headers = JiraInstanceManager.get_auth_instance()

  try:
    search_url = f"{jira_server_url}/rest/api/3/user/search"

    query = {"query": email}

    user_search_response = requests.get(search_url, headers=headers, params=query, auth=auth)

    if user_search_response.status_code == 200:
      users_data = user_search_response.json()
      if users_data:
        account_id = users_data[0].get("accountId")
        logging.info(f"Account ID found for email {email}: {account_id}")
        return account_id
      else:
        logging.warning(f"No users found with email {email}.")
        return None
    else:
      logging.error(
        f"Failed to retrieve user details for email {email}. Status code: {user_search_response.status_code}, Response: {user_search_response.text}"
      )
      return None
  except Exception as e:
    logging.error(f"Failed to get account ID for email {email}. Error: {e}")
    return None


@tool
async def get_account_id_from_email(email: str) -> str:
  """
  Retrieves the account ID associated with a given email address in JIRA.

  Args:
    email (str): The email address of the user whose account ID is to be retrieved.

  Returns:
    str: The account ID of the user, as a string. Returns None if the user is not found or if an error occurs.

  Raises:
    Exception: If the JIRA API request fails or encounters an error. The exception will contain details about the failure, including the HTTP status code and response text (if available).
  """
  return await _get_account_id_from_email(email)


async def _get_jira_reporter_email(issue_key: str) -> str:
  """
  Retrieves the email address of the reporter of a JIRA issue.

  Args:
    issue_key (str): JIRA Issue ID.

  Returns:
    str: The email address of the reporter, or None if not found or an error occurs.
  """
  reporter_account_id = await get_jira_reporter_account_id(issue_key)
  if not reporter_account_id:
    logging.error("Reporter account ID not found.")
    return None

  jira_server_url = os.getenv("JIRA_SERVER")
  user_email = os.getenv("JARVIS_JIRA_USER_EMAIL")
  access_token = os.getenv("JARVIS_JIRA_ACCESS_TOKEN")
  auth = HTTPBasicAuth(user_email, access_token)
  headers = {"Accept": "application/json", "Content-Type": "application/json"}
  user_url = f"{jira_server_url}/rest/api/2/user?accountId={reporter_account_id}"
  user_response = requests.get(user_url, headers=headers, auth=auth)
  if user_response.status_code == 200:
    user_data = user_response.json()
    reporter_email = user_data.get("emailAddress")
    if reporter_email and "|" in reporter_email:
      reporter_email = reporter_email.split("|")[0].strip("[]")
    return reporter_email
  else:
    logging.error(
      f"Failed to retrieve user details. Status code: {user_response.status_code}, Response: {user_response.text}"
    )
    return None


@tool
async def get_jira_reporter_email(issue_key: str) -> str:
  """
  Retrieves the email address of the reporter of a JIRA issue.

  Args:
    issue_key (str): JIRA Issue ID.

  Returns:
    str: The email address of the reporter, or None if not found or an error occurs.
  """
  return await _get_jira_reporter_email(issue_key)
