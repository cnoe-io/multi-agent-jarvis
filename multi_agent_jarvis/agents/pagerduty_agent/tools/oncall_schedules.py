# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import aiohttp
from multi_agent_jarvis.async_http_utils import with_async_http_session
import json
import os
from multi_agent_jarvis.setup_logging import logging
from langchain_core.tools import tool
from datetime import datetime
from datetime import timedelta
from multi_agent_jarvis.dryrun_utils import dryrun_response
from multi_agent_jarvis.agents.pagerduty_agent.tools.dryrun.mock_responses import PAGERDUTY_GET_CURRENT_ONCALL_MOCK_RESPONSE

# Replace these with your actual PagerDuty API token and schedule ID
API_TOKEN = os.getenv("PAGERDUTY_API_TOKEN")


@with_async_http_session
async def get_user_id_from_user_email(session, user_email):
  """
  Retrieve the PagerDuty user ID based on their user_email.

  Args:
    user_email (str): The user_email address of the user.

  Returns:
    str: The user ID.

  Raises:
    ValueError: If no user is found for the given user_email.
  """
  url = "https://api.pagerduty.com/users"
  headers = {
    "Authorization": f"Token token={API_TOKEN}",
    "Accept": "application/vnd.pagerduty+json;version=2",
  }
  params = {"query": user_email}

  logging.info(f"Fetching user ID for user_email: {user_email}")
  async with session.get(url, headers=headers, params=params) as response:
    response.raise_for_status()
    response_data = await response.json()
    users = response_data.get("users", [])

  if not users:
    logging.error(f"No user found for user_email: {user_email}")
    raise ValueError(f"No user found for user_email: {user_email}")

  user_id = users[0]["id"]
  logging.info(f"Found user ID: {user_id} for user_email: {user_email}")
  return user_id


@with_async_http_session
async def get_schedule_by_id(session, schedule_id):
  """
  Retrieve the schedule details for a given PagerDuty schedule ID.

  Args:
    schedule_id (str): The ID of the PagerDuty schedule.

  Returns:
    dict: The schedule details.

  Raises:
    ValueError: If no schedule is found for the given schedule_id.
  """
  url = f"https://api.pagerduty.com/schedules/{schedule_id}"
  headers = {
    "Authorization": f"Token token={API_TOKEN}",
    "Accept": "application/vnd.pagerduty+json;version=2",
  }

  logging.info(f"Fetching schedule details for schedule ID: {schedule_id}")

  async with session.get(url, headers=headers) as response:
    response.raise_for_status()
    response_data = await response.json()
    schedule = response_data.get("schedule", {})

  if not schedule:
    logging.error(f"No schedule found for schedule ID: {schedule_id}")
    raise ValueError(f"No schedule found for schedule ID: {schedule_id}")

  logging.info(f"Found schedule details for schedule ID: {schedule_id}")
  logging.info(f"Schedule: {json.dumps(schedule, indent=2)}")
  return schedule


@with_async_http_session
async def get_user_email_from_user_id(session, self_url_link):
  """
  Retrieve the user_email address based on their self_url_link.

  Args:
    self_url_link (str): The self_url_link of the user.

  Returns:
    str: The user email.

  Raises:
    ValueError: If no user is found for the given self_url_link.
  """
  headers = {
    "Authorization": f"Token token={API_TOKEN}",
    "Accept": "application/vnd.pagerduty+json;version=2",
  }

  logging.info(f"Fetching user email for self_url_link: {self_url_link}")
  async with session.get(self_url_link, headers=headers) as response:
    response.raise_for_status()
    response_data = await response.json()
    user = response_data.get("user", {})

  if not user:
    logging.error(f"No user found for self_url_link: {self_url_link}")
    raise ValueError(f"No user found for self_url_link: {self_url_link}")

  user_email = user["email"]
  logging.info(f"Found user email: {user_email} for self_url_link: {self_url_link}")
  return user_email


@with_async_http_session
async def get_oncall_users_on_schedule(session, schedule_id):
  """
  Retrieve the schedule details for a given PagerDuty schedule ID.

  Args:
    schedule_id (str): The ID of the PagerDuty schedule.

  Returns:
    dict: The schedule details.

  Raises:
    ValueError: If no schedule is found for the given schedule_id.
  """
  try:
    since = (datetime.now() - timedelta(hours=1)).isoformat() + "Z"
    until = (datetime.now() + timedelta(hours=1)).isoformat() + "Z"

    url = f"https://api.pagerduty.com/schedules/{schedule_id}/users"
    headers = {
      "Authorization": f"Token token={API_TOKEN}",
      "Accept": "application/vnd.pagerduty+json;version=2",
    }
    params = {"since": since, "until": until}

    logging.info(f"Fetching on-call users for schedule ID: {schedule_id}")
    async with session.get(url, headers=headers, params=params) as response:
      response.raise_for_status()
      response_json = await response.json()
    logging.info(f"Response: {json.dumps(response_json, indent=2)}")
    users = [user for user in response_json.get("users", []) if user.get("self") is not None]

    if not users:
      logging.error(f"No on-call users found for schedule ID: {schedule_id}")
      raise ValueError(f"No on-call users found for schedule ID: {schedule_id}")

    logging.info(f"Found on-call users for schedule ID: {schedule_id}")
    user_email = await get_user_email_from_user_id(users[0]["self"])
    return users[0]["summary"], users[0]["html_url"], user_email

  except aiohttp.ClientResponseError as e:
    logging.error(f"HTTP Request failed: {e}")
    raise ValueError(f"HTTP Request failed: {e}")
  except Exception as e:
    logging.error(f"An error occurred: {e}")
    raise ValueError(f"An error occurred: {e}")


@dryrun_response(PAGERDUTY_GET_CURRENT_ONCALL_MOCK_RESPONSE)
@with_async_http_session
async def get_current_oncall_person_based_on_schedule(session, schedule_name):
  """
  Retrieve the current on-call person for a given PagerDuty schedule.

  Args:
    schedule_name (str): The name of the PagerDuty schedule.

  Returns:
    str: The email of the current on-call person.

  Raises:
    ValueError: If no schedule or on-call person is found for the given schedule_name.
  """
  try:
    url = "https://api.pagerduty.com/schedules"
    headers = {
      "Authorization": f"Token token={API_TOKEN}",
      "Accept": "application/vnd.pagerduty+json;version=2",
    }
    params = {"query": schedule_name}

    logging.info(f"Fetching schedule ID for schedule name: {schedule_name}")
    async with session.get(url, headers=headers, params=params) as response:
      response.raise_for_status()
      response_data = await response.json()
    schedules = response_data.get("schedules", [])

    logging.info(f"Schedules: {json.dumps(schedules, indent=2)}")

    if not schedules:
      logging.error(f"No schedule found for schedule name: {schedule_name}")
      raise ValueError(f"No schedule found for schedule name: {schedule_name}")

    schedule_id = schedules[0]["id"]
    logging.info(f"Found schedule ID: {schedule_id} for schedule name: {schedule_name}")

    # Fetch on-call users using the schedule ID
    return await get_oncall_users_on_schedule(schedule_id)

  except aiohttp.ClientResponseError as e:
    logging.error(f"HTTP Request failed: {e}")
    raise ValueError(f"HTTP Request failed: {e}")
  except Exception as e:
    logging.error(f"An error occurred: {e}")
    raise ValueError(f"An error occurred: {e}")


@tool
async def who_is_on_sre_oncall():
  """
  Retrieve the current SRE on-call person.

  Returns:
    str: The email of the current SRE on-call person.

  Raises:
    ValueError: If no SRE service or on-call person is found.
  """
  try:
    logging.info("Fetching current SRE on-call persons")

    (
      sre_primary_oncall_name,
      sre_primary_oncall_url,
      sre_primary_oncall_email,
    ) = await get_current_oncall_person_based_on_schedule("ETI SRE - Primary")
    logging.info(f"Found SRE Primary Oncall: {sre_primary_oncall_name} - {sre_primary_oncall_email}")

    (
      sre_secondary_oncall_name,
      sre_secondary_oncall_url,
      sre_secondary_oncall_email,
    ) = await get_current_oncall_person_based_on_schedule("ETI SRE - Secondary")
    logging.info(f"Found SRE Secondary Oncall: {sre_secondary_oncall_name} - {sre_secondary_oncall_email}")

    (
      service_desk_name_us,
      service_desk_url_us,
      service_desk_email_us,
    ) = await get_current_oncall_person_based_on_schedule("Outshift Platform Service Desk Support US")
    (
      service_desk_name_europe,
      service_desk_url_europe,
      service_desk_email_europe,
    ) = await get_current_oncall_person_based_on_schedule("Outshift Platform Service Desk Support Europe")
    logging.info(
      f"Found SRE Service Desk Oncall US: {service_desk_name_us} - {service_desk_email_us}, Europe: {service_desk_name_europe} - {service_desk_email_europe}"
    )

    markdown = "## Platform On-Call Persons\n\n"
    markdown += f"**Platform Primary Oncall:**\n[{sre_primary_oncall_name}]({sre_primary_oncall_url}) - {sre_primary_oncall_email}\n\n"
    markdown += f"**Platform Secondary Oncall:**\n[{sre_secondary_oncall_name}]({sre_secondary_oncall_url}) - {sre_secondary_oncall_email}\n\n"
    markdown += (
      f"**Platform Service Desk US:**\n[{service_desk_name_us}]({service_desk_url_us}) - {service_desk_email_us}\n\n"
    )
    markdown += f"**Platform Service Desk Europe:**\n[{service_desk_name_europe}]({service_desk_url_europe}) - {service_desk_email_europe}\n"

    logging.info("Successfully formatted Platform on-call persons as markdown")
    return markdown

  except Exception as e:
    logging.error(f"Error fetching SRE on-call persons: {e}")
    return f"Error fetching SRE on-call persons: {e}"
