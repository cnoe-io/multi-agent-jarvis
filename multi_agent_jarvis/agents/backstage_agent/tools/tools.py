# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from langchain_core.tools import tool
from multi_agent_jarvis.agents.backstage_agent.api import (
  get_backstage_catalog_entities,
  get_backstage_groups_by_user,
  get_backstage_projects_by_user,
)

@tool
async def tool_get_backstage_catalog_entities(user_id: str):
  """
  Fetch backstage catalog entities.

  This function sends a GET request to the catalog API to retrieve entities
  associated with the specified user ID. The request is authenticated using
  an API token obtained from the environment variable 'BACKSTAGE_API_TOKEN'.

  Returns:
    dict: A dictionary containing the JSON response from the API if the request is successful.

  Raises:
    HTTPError: If the request fails with a status code other than 200.
  """
  return await get_backstage_catalog_entities(user_id)

@tool
async def tool_get_backstage_groups_by_user(user_id: str):
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
  return await get_backstage_groups_by_user(user_id)

@tool
async def tool_get_backstage_projects_by_user(user_id: str):
  """
  Fetches the projects owned by the groups that the specified user is a member of from the Backstage catalog.

  Returns:
    dict: A dictionary containing the projects owned by the groups the user is a member of.
        If no groups are found for the user, an empty dictionary is returned.

  Raises:
    HTTPError: If the request to fetch groups or projects fails with a status code other than 200.
  """
  return await get_backstage_projects_by_user(user_id)
