# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from multi_agent_jarvis.setup_logging import logging

from multi_agent_jarvis.async_http_utils import with_async_http_session
from multi_agent_jarvis.dryrun_utils import dryrun_response
from multi_agent_jarvis.agents.backstage_agent.api.dryrun.mock_responses import (
  MOCK_GET_BACKSTAGE_GROUPS_BY_USER_RESPONSE,
)
from multi_agent_jarvis.agents.backstage_agent.api.common import BACKSTAGE_URL

@dryrun_response(MOCK_GET_BACKSTAGE_GROUPS_BY_USER_RESPONSE)
@with_async_http_session
async def get_backstage_groups_by_user(session, user_id: str):
  """
  Fetches the list of Backstage groups for a given user.

  This function makes an HTTP GET request to the Backstage API to retrieve
  the groups that a specified user is a member of. The function logs the
  URL being accessed, the user ID for which groups are being fetched, and
  the response from the API. If the request is successful, it extracts and
  returns the names of the groups. If the request fails, it logs an error
  and raises an HTTP error.

  Returns:
    list: A list of group names that the user is a member of.

  Raises:
    HTTPError: If the HTTP request to the Backstage API fails.
  """

  BACKSTAGE_API_TOKEN = os.getenv("BACKSTAGE_API_TOKEN")
  group_url = (
    f"{BACKSTAGE_URL}/api/catalog/entities/by-query?filter=kind=group,spec.members={user_id}&fields=metadata.name"
  )
  logging.info(f"Group URL: {group_url}")
  headers = {"Authorization": f"Bearer {BACKSTAGE_API_TOKEN}"}

  logging.info(f"Fetching groups for user_id: {user_id}")

  async with session.get(group_url, headers=headers) as group_response:
    group_response_text = await group_response.text()
    logging.info(f"Group Response: {group_response_text}")

    if group_response.status != 200:
      logging.error(f"Group request failed with status code: {group_response.status}")
      group_response.raise_for_status()

    groups = await group_response.json()
  group_items = groups["items"]
  group_names = [group["metadata"]["name"] for group in group_items]

  logging.info(f"Groups found for the user: {group_names}")

  if not group_names:
    logging.info("No groups found for the user")
    return "No groups found for the user"

  return group_names
