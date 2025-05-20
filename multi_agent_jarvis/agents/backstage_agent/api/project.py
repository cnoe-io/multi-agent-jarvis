# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from multi_agent_jarvis.setup_logging import logging

from multi_agent_jarvis.async_http_utils import with_async_http_session
from multi_agent_jarvis.dryrun_utils import dryrun_response
from multi_agent_jarvis.agents.backstage_agent.api.dryrun.mock_responses import (
  MOCK_GET_BACKSTAGE_PROJECTS_BY_USER_RESPONSE,
)
from multi_agent_jarvis.agents.backstage_agent.api.common import BackstageUserDoesNotBelongToProjectError, BACKSTAGE_URL

@dryrun_response(MOCK_GET_BACKSTAGE_PROJECTS_BY_USER_RESPONSE)
@with_async_http_session
async def get_backstage_projects_by_user(session, user_id: str):
  """
  Fetches the projects owned by the groups that the specified user is a member of from the Backstage catalog.

  Returns:
    dict: A dictionary containing the projects owned by the groups the user is a member of.
        If no groups are found for the user, an empty dictionary is returned.

  Raises:
    HTTPError: If the request to fetch groups or projects fails with a status code other than 200.
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

  project_url = f"{BACKSTAGE_URL}/api/catalog/entities/by-query?"
  project_url += "&".join([f"filter=kind=system,relations.ownedBy=group:default/{group}" for group in group_names])
  logging.info(f"Project URL: {project_url}")

  logging.info("Checking if any of the groups own a project")

  async with session.get(project_url, headers=headers) as project_response:
    project_response_text = await project_response.text()
    logging.debug(f"Project Response: {project_response_text}")

    if project_response.status == 200:
      logging.info("Project request successful")
      return await project_response.json()
    else:
      logging.error(f"Project request failed with status code: {project_response.status}")
      project_response.raise_for_status()

async def get_backstage_project_details(project_name: str, user_id: str):
  """
  Fetches the details of a specific project owned by the groups that the specified user is a member of.

  This function searches through the projects owned by the user's groups and returns the details
  of the project that matches the specified project name.

  Args:
    project_name (str): The name of the project to find.
    user_id (str): The ID of the user whose groups' projects are being searched.

  Returns:
    dict: A dictionary containing the details of the specified project if found.
          If the project is not found, returns a message indicating so.

  Raises:
    HTTPError: If the request to fetch projects fails with a status code other than 200.
  """

  projects = await get_backstage_projects_by_user(user_id)

  logging.debug(f"Projects: {projects}")

  for project in projects.get("items", []):
    if project["metadata"]["name"].lower() == project_name.lower():
      logging.info(f"Project found: {project}")
      return project

  logging.info(f"Project '{project_name}' not found for user '{user_id}'")
  raise BackstageUserDoesNotBelongToProjectError()
