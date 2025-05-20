# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.agents.backstage_agent.api.project import get_backstage_project_details
from multi_agent_jarvis.agents.backstage_agent.api.common import BackstageUserDoesNotBelongToProjectError

BACKSTAGE_PROJECTS_LIST = os.getenv("BACKSTAGE_PROJECTS_LIST", "cnoe").split(",")

async def get_backstage_component_details(
  project_name, user_id, org_name, repo_name, component_description, lifecycle, language_stack
):
  """
  Fetches the details of a specific component owned by the groups that the specified user is a member of.
  This function searches through the components owned by the user's groups and returns the details
  of the component that matches the specified repo name.
  Args:
    project_name (str): The name of the project to find.
    user_id (str): The ID of the user whose groups' components are being searched.
    repo_name (str): The name of the component to find.
    component_description (str): The description of the component.
    lifecycle (str): The lifecycle of the component.
    language_stack (str): The language stack of the component.
  Returns:
    dict: A dictionary containing the details of the specified component if found.
          If the component is not found, returns a message indicating so.
  Raises:
    HTTPError: If the request to fetch components fails with a status code other than 200.
  """

  valid_projects = BACKSTAGE_PROJECTS_LIST
  if project_name not in valid_projects:
    raise ValueError(f"Invalid project name. Valid project names are: {', '.join(valid_projects)}")

  try:
    if project_name != "other":
      project_details = await get_backstage_project_details(project_name, user_id)

      project_source_location = (
        project_details.get("metadata", {}).get("annotations", {}).get("backstage.io/source-location", "")
      )  # Project Source Location

      component_owner = project_details.get("metadata", {}).get("name", "")  # Project Name
      component_name = repo_name  # Repository Name
      component_title = repo_name.replace("-", " ").replace("_", " ").title()  # Repository Title
      component_description = (
        component_description if component_description else f"Repository for {repo_name}"
      )  # Repository Description
      component_tags = project_details.get("metadata", {}).get("tags", [])  # Project Tags
      component_owner = f"user:{user_id}"
      component_type = project_details.get("spec", {}).get("type", "")
      component_lifecycle = lifecycle
      component_stack = language_stack
      trimmed_project_source_location = project_source_location.replace(
        "https://github.com/cnoe-io", ""
      ).replace("url:", "")
    else:
      project_source_location = f"https://github.com/{org_name}/{repo_name}"  # Repo URL
      component_owner = f"user:{user_id}"  # User ID
      component_name = repo_name  # Repository Name
      component_title = repo_name.replace("-", " ").replace("_", " ").title()  # Repository Title
      component_tags = ["other"]  # Project Tags
      component_type = "service"  # Component Type
      component_lifecycle = lifecycle  # Component Lifecycle
      component_stack = language_stack  # Component Stack
      trimmed_project_source_location = project_source_location  # Project Source Location

    return (
      project_source_location,
      trimmed_project_source_location,
      component_owner,
      component_name,
      component_title,
      component_description,
      component_tags,
      component_type,
      component_lifecycle,
      component_stack,
    )
  except BackstageUserDoesNotBelongToProjectError as e:
    exception_message = (
      str(e)
      + f" User {user_id} does not belong to Project: {project_name} in Backstage. "
      + "Please contact Platform Team for assistance "
    )
    logging.error(exception_message)
    raise BackstageUserDoesNotBelongToProjectError(exception_message)
