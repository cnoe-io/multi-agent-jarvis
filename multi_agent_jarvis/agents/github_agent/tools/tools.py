# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from multi_agent_jarvis.setup_logging import logging
import os
from github import Github, Auth
from multi_agent_jarvis.agents.jira_agent import _create_outshift_service_desk_ticket
from multi_agent_jarvis.webex.webex_util import send_webex_message_to_person, send_webex_message_to_room
from multi_agent_jarvis.agents.backstage_agent.api import get_backstage_component_details
from langchain_core.tools import tool
from typing import Literal

from multi_agent_jarvis.agents.github_agent.api.github_actions import (
  get_ci_logs,
  retrieve_ci_status,
  list_ci_workflows,
  trigger_github_workflow,
)

from multi_agent_jarvis.agents.github_agent.api.pull_request import (
  read_pull_request,
  update_pull_request,
  list_pull_requests,
  add_pull_request_comment,
  read_latest_pull_request_comments,
)

from multi_agent_jarvis.agents.github_agent.api.repo import (
  get_repo_description,
  get_repo_topics,
  get_repo_members
)

GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_ORGS_OPTIONS = os.getenv("GITHUB_ORGS_OPTIONS")
REPO_TEMPLATE_OPTIONS = os.getenv("REPO_TEMPLATE_OPTIONS", "").split(",")
BACKSTAGE_LIFECYCLE_OPTIONS = os.getenv("BACKSTAGE_LIFECYCLE_OPTIONS", "development, experimental, production").split(",")
BACKSTAGE_PROJECTS_LITERAL = os.getenv("BACKSTAGE_PROJECTS_LITERAL", "cnoe").split(",")


@tool
async def tool_create_github_repo(
  repo_name: str,
  project_name: BACKSTAGE_PROJECTS_LITERAL,
  user_email: str,
  org_name: GITHUB_ORGS_OPTIONS,
  repo_template: REPO_TEMPLATE_OPTIONS,
  jira_issue_id: str,
) -> str:
  """
  Creates a new GitHub repo under the specified organization.
  Args:
    repo_name (str): The name of the repo to be created.
    project_name (str): The name of the project associated with the repo.
    org_name (str): The name of the organization under which the repo will be created. Defaults to cisco-eti.
    repo_template (str, optional): The name of the template repo to use for creating the new repo. Defaults to None.
    jira_issue_id (str, optional): The JIRA issue ID for the request. Default OPENSD-XXXX.
  Returns:
    str: The URL of the newly created repo.
  Raises:
    ValueError: If the repo name or organization name is invalid.
    Exception: For any other errors that occur during the repo creation process.
  """
  repo_description = f"Repository for {repo_name}"
  language_stack = "generic"
  lifecycle = "experimental"

  if repo_template and repo_template.lower() == "none":
    repo_template = None

  if not repo_name or not org_name:
    raise ValueError("Repository name and organization name must be provided.")

  project_name = project_name.lower()

  logging.debug("Starting repo creation process.")
  GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

  # using an access token
  auth = Auth.Token(GITHUB_TOKEN)

  # Public Web Github
  g = Github(auth=auth)

  try:
    # Check if the repo already exists
    repo = g.get_repo(f"{org_name}/{repo_name}")
    if repo:
      return f"Repository '{repo_name}' already exists in organization '{org_name}'."
  except Exception:
    logging.info(f"Repository '{repo_name}' does not exist. Proceeding with creation.")

  logging.info(
    f"Input parameters - \n"
    f"repo_name: {repo_name}, \n"
    f"project_name: {project_name}, \n"
    f"user_email: {user_email}, \n"
    f"org_name: {org_name}, \n"
    f"repo_template: {repo_template}"
  )
  try:
    message = (
      f"Creating GitHub repo with the following details:\n"
      f"Repository Name: {repo_name}\n"
      f"Organization Name: {org_name}\n"
      f"Template Repository: {repo_template}"
    )

    logging.info(message)

    if not language_stack:
      language_stack = "Unknown"

    if not lifecycle:
      lifecycle = "experimental"

    user_id = user_email.replace("@cisco.com", "")

    (
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
    ) = await get_backstage_component_details(
      project_name=project_name,
      user_id=user_id,
      org_name=org_name,
      repo_name=repo_name,
      component_description=repo_description,
      lifecycle=lifecycle,
      language_stack=language_stack,
    )

    logging.info(f"Project Source Location: {project_source_location}")
    logging.info(f"Trimmed Project Source Location: {trimmed_project_source_location}")
    logging.info(f"Component Owner: {component_owner}")
    logging.info(f"Component Name: {component_name}")
    logging.info(f"Component Title: {component_title}")
    logging.info(f"Component Description: {component_description}")
    logging.info(f"Component Tags: {component_tags}")
    logging.info(f"Component Type: {component_type}")
    logging.info(f"Component Lifecycle: {component_lifecycle}")
    logging.info(f"Component Stack: {component_stack}")

    jira_summary = f"GitHub Repository Creation Request: {repo_name} from User: {user_email}"

    jira_description = (
      f"GitHub repo creation request for name: '{repo_name}' under organization '{org_name}' "
      f"from user with email '{user_email}'.\n\n"
      f"Details:\n"
      f"Repository Name: {repo_name}\n"
      f"Organization Name: {org_name}\n"
      f"Template Repository: {repo_template}\n"
    )

    if jira_issue_id != "OPENSD-XXXX":
      jira_ticket = jira_issue_id
      service_desk_ticket_response = f"Using existing JIRA ticket: {jira_ticket}"
    else:
      service_desk_ticket_response, jira_ticket = await _create_outshift_service_desk_ticket(
        summary=jira_summary, description=jira_description, user_email=user_email
      )
      logging.info(f"Service Desk Response: {service_desk_ticket_response}")
      logging.info(f"Jira Ticket: {jira_ticket}")

    run_url = ""

    component_info = (
      f"COMPONENT_OWNER={component_owner},"
      f"COMPONENT_SYSTEM={project_name},"
      f"COMPONENT_NAME={component_name},"
      f"COMPONENT_TITLE={component_title},"
      f"COMPONENT_DESCRIPTION={component_description},"
      f"COMPONENT_TAGS={';'.join(component_tags)},"
      f"COMPONENT_TYPE={component_type},"
      f"COMPONENT_LIFECYCLE={component_lifecycle},"
      f"COMPONENT_STACK={component_stack},"
      f"PROJECT_SOURCE_LOCATION={trimmed_project_source_location}"
    )

    run_url = await trigger_github_workflow(
      workflow_name="create-repo-add-backstage-component",
      REPO_NAME=repo_name,  # Repo name input param to workflow
      ORG_NAME=org_name,  # Org name input param to workflow
      PROJECT_NAME=project_name,  # Project name input param to workflow
      TEMPLATE_NAME=repo_template if repo_template else "",  # Repo template input param to workflow
      COMPONENT_INFO=component_info,  # Component info input param to workflow
      JIRA_TICKET=jira_ticket,  # Jira ticket input param to workflow
    )

    user_request_sent_card = {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.2",
        "body": [
          {
            "type": "TextBlock",
            "text": "Request sent for approval",
            "weight": "Bolder",
            "size": "Medium",
          },
          {
            "type": "TextBlock",
            "text": f"{service_desk_ticket_response}",
            "wrap": True,
          },
        ],
      },
    }

    send_webex_message_to_person(
      user_email,
      "Your request has been sent for approval.",
      user_request_sent_card,
    )

    admin_approval_required_card = {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.2",
        "body": [
          {
            "type": "TextBlock",
            "text": "Approval request: New repo creation",
            "weight": "Bolder",
            "size": "Medium",
          },
          {
            "type": "TextBlock",
            "text": f"Repository Name: {repo_name}",
            "wrap": True,
          },
          {
            "type": "TextBlock",
            "text": f"Organization Name: {org_name}",
            "wrap": True,
          },
          {
            "type": "TextBlock",
            "text": f"Template Repository: {repo_template}",
            "wrap": True,
          },
          {
            "type": "TextBlock",
            "text": f"[GitHub Workflow Run URL]({run_url})",
            "wrap": True,
          },
          {
            "type": "TextBlock",
            "text": f"{service_desk_ticket_response}",
            "wrap": True,
          },
        ],
      },
    }

    send_webex_message_to_room(
      f"Approval request: New repo creation: {repo_name}",
      admin_approval_required_card,
    )

    return f"Your request for '{repo_name}' under organization '{org_name}' has been sent for further approval. {service_desk_ticket_response}"
  except Exception as e:
    logging.error(f"Exception: {str(e)}")
    return f"Failed to create repo: {str(e)}"


@tool
async def tool_add_existing_git_repo_to_backstage_component(
  repo_name: str,
  project_name: BACKSTAGE_PROJECTS_LITERAL,
  user_email: str,
  org_name: GITHUB_ORGS_OPTIONS,
  repo_template: REPO_TEMPLATE_OPTIONS,
  repo_description: str,
  language_stack: str,
  lifecycle: BACKSTAGE_LIFECYCLE_OPTIONS,
  ci_url: str,
  cd_url: str,
  jira_issue_id: str,
) -> str:
  """
  Add an existing GitHub repo to a Backstage component.
  Args:
    repo_name (str): The name of the existing repo to be added to backstage.
    project_name (str): The name of the project.
    org_name (str): The name of the organization. Defaults to cisco-eti.
    repo_template (str, optional): The template repo name.
    repo_description (str, optional): The description of the repo.
    language_stack (str, optional): The language stack of the repo.
    lifecycle (str, optional): The lifecycle stage of the repo. Defaults to experimental.
    ci_url (str, optional): The CI pipeline URL.
    cd_url (str, optional): The CD pipeline URL.
    jira_issue_id (str, optional): The JIRA issue ID for the request. Default OPENSD-XXXX.
  Returns:
    str: The URL of the newly created repo.
  Raises:
    ValueError: If the repo name or organization name is invalid.
    Exception: For any other errors during the repo creation process.
  """

  if not repo_name or not org_name:
    raise ValueError("Repository name and organization name must be provided.")

  project_name = project_name.lower()
  logging.debug("Starting repo creation process.")
  GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

  # using an access token
  auth = Auth.Token(GITHUB_TOKEN)

  # Public Web Github
  g = Github(auth=auth)

  try:
    # Check if the repo already exists
    repo = g.get_repo(f"{org_name}/{repo_name}")
    if repo:
      logging.info(f"Repository '{repo_name}' already exists in organization '{org_name}'.")
    else:
      ValueError(f"Repository '{repo_name}' does not exist in organization '{org_name}'.")
  except Exception as e:
    logging.error(f"Repository '{repo_name}' does not exist. Error: {str(e)}")
    raise Exception(f"Repository '{repo_name}' does not exist in organization '{org_name}'. Error: {str(e)}")

  logging.info(
    f"Input parameters - \n"
    f"repo_name: {repo_name}, \n"
    f"project_name: {project_name}, \n"
    f"user_email: {user_email}, \n"
    f"org_name: {org_name}, \n"
    f"repo_template: {repo_template}"
  )
  try:
    message = (
      f"Creating GitHub repo with the following details:\n"
      f"Repository Name: {repo_name}\n"
      f"Organization Name: {org_name}\n"
      f"Template Repository: {repo_template}"
    )

    logging.info(message)

    if not language_stack:
      language_stack = "Unknown"

    if not lifecycle:
      lifecycle = "experimental"

    user_id = user_email.replace("@cisco.com", "")

    (
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
    ) = await get_backstage_component_details(
      project_name=project_name,
      user_id=user_id,
      org_name=org_name,
      repo_name=repo_name,
      component_description=repo_description,
      lifecycle=lifecycle,
      language_stack=language_stack,
    )

    logging.info(f"Project Source Location: {project_source_location}")
    logging.info(f"Trimmed Project Source Location: {trimmed_project_source_location}")
    logging.info(f"Component Owner: {component_owner}")
    logging.info(f"Component Name: {component_name}")
    logging.info(f"Component Title: {component_title}")
    logging.info(f"Component Description: {component_description}")
    logging.info(f"Component Tags: {component_tags}")
    logging.info(f"Component Type: {component_type}")
    logging.info(f"Component Lifecycle: {component_lifecycle}")
    logging.info(f"Component Stack: {component_stack}")

    jira_summary = f"Add existing repo {repo_name} from User: {user_email} to backstage"

    jira_description = (
      f"Add existing repo '{repo_name}' under organization '{org_name}' to backstage"
      f"from user with email '{user_email}'.\n\n"
      f"Details:\n"
      f"Repository Name: {repo_name}\n"
      f"Organization Name: {org_name}\n"
      f"Template Repository: {repo_template}\n"
    )

    if jira_issue_id != "OPENSD-XXXX":
      jira_ticket = jira_issue_id
      service_desk_ticket_response = f"Using existing JIRA ticket: {jira_ticket}"
    else:
      service_desk_ticket_response, jira_ticket = await _create_outshift_service_desk_ticket(
        summary=jira_summary, description=jira_description, user_email=user_email
      )
      logging.info(f"Service Desk Response: {service_desk_ticket_response}")
      logging.info(f"Jira Ticket: {jira_ticket}")

    run_url = ""

    component_info = (
      f"COMPONENT_OWNER={component_owner},"
      f"COMPONENT_SYSTEM={project_name},"
      f"COMPONENT_NAME={component_name},"
      f"COMPONENT_TITLE={component_title},"
      f"COMPONENT_DESCRIPTION={component_description},"
      f"COMPONENT_TAGS={';'.join(component_tags)},"
      f"COMPONENT_TYPE={component_type},"
      f"COMPONENT_LIFECYCLE={component_lifecycle},"
      f"COMPONENT_STACK={component_stack},"
      f"PROJECT_SOURCE_LOCATION={trimmed_project_source_location}"
    )

    repo_url = f"https://github.com/{org_name}/{repo_name}"

    run_url = await trigger_github_workflow(
      workflow_name="existing-repo-add-backstage-component",
      REPO_NAME=repo_name,  # Repo name input param to workflow
      ORG_NAME=org_name,  # Org name input param to workflow
      REPO_URL=repo_url,  # Repo name input param to workflow
      PROJECT_NAME=project_name,  # Project name input param to workflow
      COMPONENT_INFO=component_info,  # Component info input param to workflow
      JIRA_TICKET=jira_ticket,  # Jira ticket input param to workflow
      CI_URL=ci_url,  # CI URL input param to workflow
      CD_URL=cd_url,  # CD URL input param to workflow
    )

    user_request_sent_card = {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.2",
        "body": [
          {"type": "TextBlock", "text": "Request sent for approval", "weight": "Bolder", "size": "Medium"},
          {"type": "TextBlock", "text": f"{service_desk_ticket_response}", "wrap": True},
        ],
      },
    }

    send_webex_message_to_person(user_email, "Your request has been sent for approval.", user_request_sent_card)

    admin_approval_required_card = {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.2",
        "body": [
          {
            "type": "TextBlock",
            "text": "Approval request: Add existing repo to backstage",
            "weight": "Bolder",
            "size": "Medium",
          },
          {"type": "TextBlock", "text": f"Repository Name: {repo_name}", "wrap": True},
          {"type": "TextBlock", "text": f"Organization Name: {org_name}", "wrap": True},
          {"type": "TextBlock", "text": f"Template Repository: {repo_template}", "wrap": True},
          {"type": "TextBlock", "text": f"[GitHub Workflow Run URL]({run_url})", "wrap": True},
          {"type": "TextBlock", "text": f"{service_desk_ticket_response}", "wrap": True},
        ],
      },
    }

    send_webex_message_to_room(
      f"Approval request: Add existing repo to backstage: {repo_name}", admin_approval_required_card
    )

    return f"Your request for '{repo_name}' under organization '{org_name}' has been sent for further approval. {service_desk_ticket_response}"
  except Exception as e:
    logging.error(f"Exception: {str(e)}")
    return f"Failed to create repo: {str(e)}"


@tool
async def tool_retrieve_ci_status(repo_name: str, workflow_name: str, org_name: GITHUB_ORGS_OPTIONS) -> str:
  """
  Retrieves the CI status of the last run for a specified workflow in a GitHub repo.
  Args:
    repo_name (str): The name of the repo.
    org_name (str): The name of the organization. Defaults to cisco-eti.
    workflow_name (str): The name of the workflow.
  Returns:
    str: The status of the last run of the specified workflow.
  Raises:
    ValueError: If the repo name, organization name, or workflow name is invalid.
    Exception: For any other errors that occur during the retrieval process.
  """
  return await retrieve_ci_status(repo_name, workflow_name, org_name)

@tool
async def tool_list_ci_workflows(repo_name: str, org_name: GITHUB_ORGS_OPTIONS) -> list:
  """
  Retrieves a list of CI workflows for a specified GitHub repo.
  Args:
    repo_name (str): The name of the repo.
    org_name (str): The name of the organization. Defaults to cisco-eti. Options: cisco-eti, outshift-platform, cisco-platform
  Returns:
    list: A list of workflow names.
  Raises:
    ValueError: If the repo name or organization name is invalid.
    Exception: For any other errors that occur during the retrieval process.
  """
  return await list_ci_workflows(repo_name, org_name)

@tool
async def tool_retrieve_ci_logs(repo_name: str, org_name: GITHUB_ORGS_OPTIONS, last_n_logs: int) -> list:
  """
  Retrieves the logs of the last run for a specified workflow in a GitHub repo.
  Args:
    repo_name (str): The name of the repo.
    org_name (str): The name of the organization. Defaults to cisco-eti. Options: cisco-eti, outshift-platform, cisco-platform
    last_n_logs (int, optional): The number of last log messages to retrieve. Defaults to 10.
  Returns:
    list: A list of log messages from the last run of the specified workflow.
  Raises:
    ValueError: If the repo name or organization name is invalid.
    Exception: For any other errors that occur during the retrieval process.
  """
  return await get_ci_logs(repo_name, org_name, last_n_logs)

@tool
async def tool_read_pull_request(repo_name: str, pull_number: int, org_name: GITHUB_ORGS_OPTIONS) -> dict:
  """
  Reads details of a specific pull request from a GitHub repo.
  Args:
    repo_name (str): The name of the repo
    pull_number (int): The pull request number
    org_name (str): The organization name
  Returns:
    dict: Pull request details including title, body, state, etc.
  """
  logging.info(f"Reading pull request {pull_number} from repo {repo_name} in org {org_name}")
  return await read_pull_request(repo_name, pull_number, org_name)

@tool
async def tool_update_pull_request(
  repo_name: str,
  pull_number: int,
  title: str,
  description: str,
  state: Literal['open', 'closed'],
  org_name: GITHUB_ORGS_OPTIONS
) -> str:
  """
  Updates an existing pull request in a GitHub repo.
  Args:
    repo_name (str): The name of the repo
    pull_number (int): The pull request number
    title (str): New title for the PR
    description (str): New body text for the PR
    org_name (str): The organization name
  Returns:
    str: URL of the updated pull request
  """
  return await update_pull_request(repo_name, pull_number, title, description, state, org_name)

@tool
async def tool_list_pull_requests(
  repo_name: str,
  state: Literal['open', 'closed'],
  org_name: GITHUB_ORGS_OPTIONS) -> list:
  """
  Lists pull requests for a specified GitHub repo.
  Args:
    repo_name (str): The name of the repo
    state (str): The state of the pull requests to return. Can be 'open', 'closed'. Defaults to 'open'.
    org_name (str): The organization name
  Returns:
    list: A list of pull requests with details including title and link.
  """
  logging.info(f"Listing pull requests from repo {repo_name} in org {org_name} with state {state}")
  return await list_pull_requests(repo_name, state, org_name)

@tool
async def tool_add_pull_request_comment(
  repo_name: str,
  pull_number: int,
  comment: str,
  org_name: GITHUB_ORGS_OPTIONS) -> str:
  """
  Adds a comment to a pull request.
  Args:
    repo_name (str): The name of the repo
    pull_number (int): The pull request number
    comment (str): The comment text to add
    org_name (str): The organization name
  Returns:
    str: URL of the created comment
  """
  return await add_pull_request_comment(repo_name, pull_number, comment, org_name)

@tool
async def tool_read_latest_pull_request_comments(
  repo_name: str,
  pull_number: int,
  limit: Literal[1],
  org_name: GITHUB_ORGS_OPTIONS,
) -> list:
  """
  Gets the most recent comments from a pull request.
  Args:
    repo_name (str): The name of the repo
    pull_number (int): The pull request number
    limit (int): Maximum number of comments to return
    org_name (str): The organization name
  Returns:
    list: List of recent comments with author and text
  """
  return await read_latest_pull_request_comments(repo_name, pull_number, limit, org_name)

@tool
async def tool_get_repo_description(repo_name: str, org_name: GITHUB_ORGS_OPTIONS) -> str:
  """
  Gets the description of a GitHub repository.
  Args:
    repo_name (str): The name of the repo
    org_name (str): The organization name
  Returns:
    str: The repository description
  """
  return await get_repo_description(repo_name, org_name)

@tool
async def tool_get_repo_topics(repo_name: str, org_name: GITHUB_ORGS_OPTIONS) -> list:
  """
  Gets the topics/tags associated with a GitHub repository.
  Args:
    repo_name (str): The name of the repo
    org_name (str): The organization name
  Returns:
    list: List of repository topics
  """
  return await get_repo_topics(repo_name, org_name)

@tool
async def tool_get_repo_members(repo_name: str, org_name: GITHUB_ORGS_OPTIONS) -> list:
  """
  Gets the list of members/collaborators for a GitHub repository.
  Args:
    repo_name (str): The name of the repo
    org_name (str): The organization name
  Returns:
    list: List of repository members with their roles
  """
  return await get_repo_members(repo_name, org_name)
