# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, Dict, List, Optional
from github import Github, Auth
from multi_agent_jarvis.setup_logging import logging
import asyncio

# Required environment variables
GITHUB_ORGS_OPTIONS = os.getenv("GITHUB_ORGS_OPTIONS")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# using an access token
auth = Auth.Token(GITHUB_TOKEN)

async def create_pull_request(
  org_name: str,
  repo: str,
  title: str,
  head: str,
  base: str,
  description: Optional[str] = None,
) -> Dict[str, Any]:
  """
  Asynchronously creates a pull request.

  Args:
    org_name (str): The owner of the repository.
    repo (str): The name of the repository.
    title (str): The title of the pull request.
    head (str): The branch to merge from.
    base (str): The branch to merge into.
    description (Optional[str]): The body/description of the pull request.

  Returns:
    Dict[str, Any]: The created pull request as a dictionary.
  """
  g = Github(auth=auth)
  try:
    repo = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo}")
    logging.info(f"Creating pull request in repo {repo} in org {org_name}")
    payload = {
      "title": title,
      "head": head,
      "base": base,
    }
    if description:
      payload["body"] = description

    pull_request = await asyncio.to_thread(repo.create_pull, **payload)
    logging.info(f"Successfully created pull request in repo {repo} in org {org_name}")
  except Exception as e:
    logging.error(f"Error creating pull request in repo {repo} in org {org_name}: {e}")
    raise Exception(f"Error creating pull request in repo {repo} in org {org_name}: {e}")
  finally:
    g.close()
  return pull_request.raw_data

async def list_pull_requests(
  repo: str,
  state: str = "open",
  org_name: str = GITHUB_ORGS_OPTIONS,
) -> List[Dict[str, Any]]:
  """
  Asynchronously lists all pull requests for a repository.

  Args:
    org_name (str): The owner of the repository.
    repo (str): The name of the repository.
    state (str): The state of the pull requests to list. Can be "open", "closed", or "all".

  Returns:
    List[Dict[str, Any]]: A list of pull requests, each as a dictionary.
  """
  g = Github(auth=auth)
  try:
    repo = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo}")
    logging.info(f"Listing pull requests for repo {repo} in org {org_name}")
    pulls = await asyncio.to_thread(repo.get_pulls, state=state)
    logging.info(f"Successfully listed pull requests for repo {repo} in org {org_name}")
  except Exception as e:
    logging.error(f"Error listing pull requests for repo {repo} in org {org_name}: {e}")
    raise Exception(f"Error listing pull requests for repo {repo} in org {org_name}: {e}")
  finally:
    g.close()
  return [{"title": pull.title, "link": pull.html_url} for pull in pulls]

async def read_pull_request(
  repo: str,
  pull_number: int,
  org_name: str = GITHUB_ORGS_OPTIONS,
) -> Dict[str, Any]:
  """
  Asynchronously reads a pull request.

  Args:
    repo (str): The name of the repository.
    pull_number (int): The pull request number.
    org_name (str): The owner of the repository.

  Returns:
    Dict[str, Any]: The pull request as a dictionary.
  """
  g = Github(auth=auth)
  try:
    repo = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo}")
    logging.info(f"Reading pull request {pull_number} from repo {repo} in org {org_name}")
    pull_request = await asyncio.to_thread(repo.get_pull, number=pull_number)
    logging.info(f"Successfully read pull request {pull_number} from repo {repo} in org {org_name}")
  except Exception as e:
    logging.error(f"Error reading pull request {pull_number} from repo {repo} in org {org_name}: {e}")
    raise Exception(f"Error reading pull request {pull_number} from repo {repo} in org {org_name}: {e}")
  finally:
    g.close()
  return pull_request.raw_data

async def update_pull_request(
  repo: str,
  pull_number: int,
  title: Optional[str] = None,
  description: Optional[str] = None,
  state: Optional[str] = None,  # open or closed
  org_name: str = GITHUB_ORGS_OPTIONS,
) -> Dict[str, Any]:
  """
  Asynchronously updates a pull request.

  Args:
    org_name (str): The owner of the repository.
    repo (str): The name of the repository.
    pull_number (int): The pull request number.
    title (Optional[str]): The new title of the pull request.
    description (Optional[str]): The new body/description of the pull request.
    state (Optional[str]): The state of the pull request ("open" or "closed").

  Returns:
    Dict[str, Any]: The updated pull request as a dictionary.
  """
  g = Github(auth=auth)
  try:
    repo = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo}")
    logging.info(f"Updating pull request {pull_number} in repo {repo} in org {org_name}")
    pull_request = await asyncio.to_thread(repo.get_pull, number=pull_number)
    payload: Dict[str, Any] = {}
    if title:
      payload["title"] = title
    if description:
      payload["body"] = description
    if state:
      payload["state"] = state

    updated_pull_request = await asyncio.to_thread(pull_request.edit, **payload)
    logging.info(f"Updated pull request details: {updated_pull_request.raw_data}")
    logging.info(f"Successfully updated pull request {pull_number} in repo {repo} in org {org_name}")
  except Exception as e:
    logging.error(f"Error updating pull request {pull_number} in repo {repo} in org {org_name}: {e}")
    raise Exception(f"Error updating pull request {pull_number} in repo {repo} in org {org_name}: {e}")
  finally:
    g.close()
  return f"Successfully updated pull request {pull_number} in repo {repo} in org {org_name}"


async def add_pull_request_comment(
  repo: str,
  pull_number: int,
  comment: str,
  org_name: str = GITHUB_ORGS_OPTIONS,
) -> Dict[str, Any]:
  """
  Asynchronously adds a comment to a pull request.

  Args:
    org_name (str): The owner of the repository.
    repo (str): The name of the repository.
    pull_number (int): The pull request number.
    comment (str): The content of the comment.

  Returns:
    Dict[str, Any]: The created comment as a dictionary.
  """
  g = Github(auth=auth)
  try:
    repo = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo}")
    logging.info(f"Adding comment to pull request {pull_number} in repo {repo} in org {org_name}")
    pull_request = await asyncio.to_thread(repo.get_pull, number=pull_number)
    comment = await asyncio.to_thread(pull_request.create_issue_comment, body=comment)
    logging.info(f"Successfully added comment to pull request {pull_number} in repo {repo} in org {org_name}")
  except Exception as e:
    logging.error(f"Error adding comment to pull request {pull_number} in repo {repo} in org {org_name}: {e}")
    raise Exception(f"Error adding comment to pull request {pull_number} in repo {repo} in org {org_name}: {e}")
  finally:
    g.close()
  return comment.raw_data


async def read_latest_pull_request_comments(
  repo: str,
  pull_number: int,
  limit: int = 1,
  org_name: str = GITHUB_ORGS_OPTIONS,
) -> List[Dict[str, Any]]:
  """
  Asynchronously reads the latest comments from a pull request.

  Args:
    org_name (str): The owner of the repository.
    repo (str): The name of the repository.
    pull_number (int): The pull request number.

  Returns:
    List[Dict[str, Any]]: A list of comments, each as a dictionary.
  """
  g = Github(auth=auth)
  try:
    repo = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo}")
    logging.info(f"Reading latest comments from pull request {pull_number} in repo {repo} in org {org_name}")
    pull_request = await asyncio.to_thread(repo.get_pull, number=pull_number)
    comments = await asyncio.to_thread(pull_request.get_issue_comments)
    logging.info(f"Successfully read latest comments from pull request {pull_number} in repo {repo} in org {org_name}")
  except Exception as e:
    logging.error(f"Error reading latest comments from pull request {pull_number} in repo {repo} in org {org_name}: {e}")
    raise Exception(f"Error reading latest comments from pull request {pull_number} in repo {repo} in org {org_name}: {e}")
  finally:
    g.close()
  return [comment.raw_data for comment in comments[:limit]]
