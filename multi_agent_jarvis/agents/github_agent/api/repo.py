# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from typing import List, Dict
import asyncio
import logging
from github import Github, Auth

# Required environment variables
GITHUB_ORGS_OPTIONS = os.getenv("GITHUB_ORGS_OPTIONS")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# using an access token
auth = Auth.Token(GITHUB_TOKEN)


async def get_repo_description(repo: str, org_name: str = GITHUB_ORGS_OPTIONS) -> str:
  """
  Asynchronously gets the description of a repository.

  Args:
    repo (str): The name of the repository.
    org_name (str): The owner of the repository.

  Returns:
    str: The repository description.
  """
  g = Github(auth=auth)
  try:
    repo_obj = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo}")
    description = await asyncio.to_thread(lambda: repo_obj.description)
    logging.info(f"Successfully retrieved description for repo {repo}")
    return description or ""
  except Exception as e:
    logging.error(f"Error getting repo description for {repo}: {e}")
    raise
  finally:
    g.close()


async def get_repo_topics(repo: str, org_name: str = GITHUB_ORGS_OPTIONS) -> List[str]:
  """
  Asynchronously gets the topics of a repository.

  Args:
    repo (str): The name of the repository.
    org_name (str): The owner of the repository.

  Returns:
    List[str]: List of repository topics.
  """
  g = Github(auth=auth)
  try:
    repo_obj = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo}")
    topics = await asyncio.to_thread(lambda: repo_obj.get_topics())
    logging.info(f"Successfully retrieved topics for repo {repo}")
    return topics
  except Exception as e:
    logging.error(f"Error getting repo topics for {repo}: {e}")
    raise
  finally:
    g.close()


async def get_repo_members(repo: str, org_name: str = GITHUB_ORGS_OPTIONS) -> Dict[str, List[str]]:
  """
  Asynchronously gets the members of a repository with their permissions.

  Args:
    repo (str): The name of the repository.
    org_name (str): The owner of the repository.

  Returns:
    Dict[str, List[str]]: Dictionary with 'read' and 'write' keys containing lists of usernames.
  """
  g = Github(auth=auth)
  try:
    logging.info(f"Fetching repository {repo} from organization {org_name}")
    repo_obj = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo}")
    logging.info(f"Fetching collaborators for repository {repo}")
    collaborators = await asyncio.to_thread(lambda: list(repo_obj.get_collaborators()))

    members = {"read": [], "write": []}

    for collab in collaborators:
      logging.info(f"Fetching permissions for collaborator {collab.login}")
      permissions = await asyncio.to_thread(lambda: repo_obj.get_collaborator_permission(collab))
      if permissions in ["admin", "write"]:
        members["write"].append(collab.login)
      elif permissions == "read":
        members["read"].append(collab.login)

    logging.info(f"Successfully retrieved members for repo {repo}")
    return members
  except Exception as e:
    logging.error(f"Error getting repo members for {repo}: {e}")
    raise
  finally:
    g.close()
