# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.async_http_utils import with_async_http_session
from multi_agent_jarvis.dryrun_utils import dryrun_response
import aiohttp
import os
from io import BytesIO
import zipfile
from github import Github, Auth
from multi_agent_jarvis.agents.github_agent.api.dryrun.mock_responses import (
  MOCK_GET_CI_LOGS_RESPONSE,
  MOCK_GET_WORKFLOW_RUN_STATUS_RESPONSE,
  MOCK_TRIGGER_GITHUB_WORKFLOW_RESPONSE,
)
import asyncio
from datetime import datetime, timezone

# Optional: GitHub API URL
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")

# Required environment variables
GITHUB_ORGS_OPTIONS = os.getenv("GITHUB_ORGS_OPTIONS")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


@dryrun_response(MOCK_GET_CI_LOGS_RESPONSE)
@with_async_http_session
async def get_ci_logs(session, repo_name: str, org_name: GITHUB_ORGS_OPTIONS, last_n_logs: int) -> list:
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
  if not repo_name or not org_name:
    raise ValueError("Repository name and organization name must be provided.")

  logging.debug("Starting CI logs retrieval process.")
  GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
  headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
  }

  formatted_output = ""
  try:
    # Get workflows
    workflows_url = f"{GITHUB_API_URL}/repos/{org_name}/{repo_name}/actions/workflows"
    async with session.get(workflows_url, headers=headers) as workflows_response:
      workflows_response.raise_for_status()
      workflows_data = await workflows_response.json()
    workflows = workflows_data.get("workflows", [])

    if not workflows:
      logging.warning(f"No workflows found for repo '{repo_name}'.")
      return "No workflows found."

    workflow_list = [{"id": workflow["id"], "name": workflow["name"]} for workflow in workflows]
    logging.info(f"Available workflows: {workflow_list}")

    for i, workflow in enumerate(workflows):
      formatted_output += f"{i+1}. ID: {workflow['id']}, Name: {workflow['name']}\n"

      # Get latest run for the workflow
      runs_url = f"{GITHUB_API_URL}/repos/{org_name}/{repo_name}/actions/workflows/{workflow['id']}/runs"
      async with session.get(runs_url, headers=headers) as runs_response:
        runs_response.raise_for_status()
        runs_data = await runs_response.json()
        runs = runs_data.get("workflow_runs", [])

      if not runs:
        logging.warning(f"No runs found for workflow '{workflow['name']}' in repo '{repo_name}'.")
        formatted_output += "No runs found for this workflow.\n"
      else:
        latest_run = runs[0]
        logs_url = latest_run["logs_url"]
        async with session.get(logs_url, headers=headers) as logs_response:
          logs_response.raise_for_status()

          logging.info(f"Logs URL for the latest run: {logs_url}")
          formatted_output += f"Logs URL for the latest run: {logs_url}\n"

          count = 0
          with zipfile.ZipFile(BytesIO(logs_response.content)) as z:
            log_files = z.namelist()
            for log_file in log_files:
              with z.open(log_file) as f:
                log_content = f.read().decode("utf-8")
                log_lines = log_content.splitlines()
                log_lines.reverse()  # Reverse the order of log lines
                count += 1
                if count > last_n_logs:
                  break
                formatted_output += "\n".join(log_lines) + "\n"
                logging.debug(f"Log content from file '{log_file}' in reverse order: {log_lines}")
  except aiohttp.ClientResponseError as e:
    logging.error(f"Failed to format CI logs: {str(e)}")
    raise Exception(f"Failed to format CI logs: {str(e)}")
  return formatted_output


@dryrun_response(MOCK_GET_WORKFLOW_RUN_STATUS_RESPONSE)
@with_async_http_session
async def get_workflow_run_status(session, owner: str, repo: str, run_id: int, headers: dict) -> tuple:
  """
  Gets the status and conclusion of a specific workflow run.
  Args:
    owner (str): The account owner of the repository.
    repo (str): The name of the repository.
    run_id (int): The unique identifier of the workflow run.
    headers (dict): The headers to include in the request.
  Returns:
    tuple: The status and conclusion of the workflow run.
  """
  run_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/actions/runs/{run_id}"
  async with session.get(run_url, headers=headers) as run_response:
    run_response.raise_for_status()
    run_data = await run_response.json()
  return run_data.get("status"), run_data.get("conclusion")


@dryrun_response(MOCK_GET_CI_LOGS_RESPONSE)
@with_async_http_session
async def download_workflow_run_logs(session, run_id: int, repo_name: str, org_name: str, headers: dict) -> str:
  logs_url = f"{GITHUB_API_URL}/repos/{org_name}/{repo_name}/actions/runs/{run_id}/logs"
  async with session.get(logs_url, headers=headers, allow_redirects=False) as logs_response:
    if logs_response.status == 302:
      download_url = logs_response.headers["Location"]
      async with aiohttp.ClientSession() as session:
        async with session.get(download_url) as download_response:
          download_response.raise_for_status()
          logs_content = await download_response.read()
      with zipfile.ZipFile(BytesIO(logs_content)) as z:
        log_files = z.namelist()
        for log_file in log_files:
          with z.open(log_file) as f:
            log_data = f.read().decode("utf-8")
            if "##[endgroup]" in log_data and "Post job cleanup." in log_data:
              start_index = log_data.rfind("##[endgroup]") + len("##[endgroup]")
              end_index = log_data.find("Post job cleanup.")
              return log_data[start_index:end_index].strip()
  return "Relevant log content not found."


@dryrun_response(MOCK_TRIGGER_GITHUB_WORKFLOW_RESPONSE)
@with_async_http_session
async def trigger_github_workflow(session, workflow_name: str, workflow_logs: bool = False, **kwargs) -> str:
  """
  Triggers a specified GitHub Actions workflow in a repo. Supports the JARVIS_DRYRUN env var.
  Args:
    workflow_name (str): The name of the workflow to trigger.
    workflow_logs (bool, optional): Optionally return the workflow run logs. If not true, returns only the URI of the run.
    **kwargs: Additional keyword arguments for repo details.
      - org_name (str): The name of the organization. Options: cisco-eti, outshift-platform, cisco-platform
      - workflow_repo_name (str): The name of the repo where the workflow is located.
      - workflow_branch (str): The branch of the repo where the workflow is located.
  Returns:
    str: The URI of the triggered workflow run
  Raises:
    ValueError: If the repo name, organization name, or workflow name is invalid.
    Exception: For any other errors that occur during the triggering process.
  """
  logs = ""
  runs_url = ""
  workflow_org_name = kwargs.get("org_name", "cisco-eti")
  workflow_repo_name = kwargs.get("repo_name", "jarvis-workflows")
  workflow_branch = kwargs.get("branch", "main")

  logging.info(
    f"Triggering workflow '{workflow_name}' in repo '{workflow_repo_name}' from branch: '{workflow_branch}' "
    f"under organization '{workflow_org_name}' with inputs: '{kwargs}' "
  )

  logging.debug("Starting GitHub workflow trigger process.")
  headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
  }

  try:
    # Get workflows
    workflows_url = f"{GITHUB_API_URL}/repos/{workflow_org_name}/{workflow_repo_name}/actions/workflows"
    async with session.get(workflows_url, headers=headers) as workflows_response:
      workflows_response.raise_for_status()
      workflows = (await workflows_response.json()).get("workflows", [])

    workflow = next((wf for wf in workflows if wf["name"] == workflow_name), None)
    if not workflow:
      raise ValueError(f"Workflow '{workflow_name}' not found in repo '{workflow_repo_name}'.")

    logging.info(f"Found workflow: {workflow_name}")

    # Trigger the workflow
    trigger_url = (
      f"{GITHUB_API_URL}/repos/{workflow_org_name}/{workflow_repo_name}/actions/workflows/{workflow['id']}/dispatches"
    )

    payload = {"ref": workflow_branch, "inputs": {}}

    # Add additional inputs from kwargs
    for key, value in kwargs.items():
      if key not in payload["inputs"]:
        payload["inputs"][key] = value

    logging.info(f"Trigger URL: {trigger_url}")
    logging.info(f"Trigger payload: {payload}")

    async with session.post(trigger_url, headers=headers, json=payload) as trigger_response:
      trigger_response.raise_for_status()

    # Get the current time to compare with the run creation time
    current_time = datetime.now(timezone.utc)

    # Poll for the latest run that was created at or after the current time
    latest_run = None
    for _ in range(10):  # Retry up to 10 times
      await asyncio.sleep(5)  # Wait for 5 seconds before retrying
      runs_url = f"{GITHUB_API_URL}/repos/{workflow_org_name}/{workflow_repo_name}/actions/runs"
      async with session.get(runs_url, headers=headers) as runs_response:
        runs_response.raise_for_status()
        runs_data = await runs_response.json()
      logging.debug(runs_data)  # Log the response for debugging
      runs = runs_data.get("workflow_runs", [])

      latest_run = next(
        (run for run in runs if datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")) >= current_time), None
      )
      if latest_run:
        break

    if not latest_run:
      raise Exception(f"No workflow runs found for workflow '{workflow_name}' triggered at or after {current_time}.")

    action_run_url = latest_run.get("html_url")
    run_id = latest_run.get("id")
    logging.info(f"Workflow run URL: {action_run_url}")

    if not workflow_logs:
      # If not specified, return the URI of the run
      logging.info(f"Workflow '{workflow_name}' triggered successfully. {action_run_url}")
      return action_run_url

    # Poll for the workflow run URL to be available
    for _ in range(10):  # Retry up to 10 times
      try:
        async with session.get(action_run_url, headers=headers) as run_response:
          run_response.raise_for_status()
        break
      except aiohttp.ClientResponseError as e:
        logging.warning(f"Failed to retrieve workflow run URL: {str(e)}")
        if e.status == 404:
          await asyncio.sleep(5)  # Wait for 5 seconds before retrying
        else:
          raise

    # Poll for the workflow completion
    status, conclusion = await get_workflow_run_status(workflow_org_name, workflow_repo_name, run_id, headers)
    while status not in ["completed", "failure", "cancelled"]:
      await asyncio.sleep(10)
      status, conclusion = await get_workflow_run_status(workflow_org_name, workflow_repo_name, run_id, headers)

    if conclusion != "success":
      raise Exception(f"Workflow run did not complete successfully: {conclusion}")

    # Retrieve the logs for the workflow run
    logs = await download_workflow_run_logs(run_id, workflow_repo_name, workflow_org_name, headers)
    logging.info(f"Workflow '{workflow_name}' triggered successfully.")
    return action_run_url, logs
  except aiohttp.ClientResponseError as e:
    logging.error(f"Failed to trigger workflow: {str(e)}")
    logging.error(logs)
    raise Exception(f"Failed to trigger workflow: {str(e)}, {logs}, {runs_url}")


async def retrieve_ci_status(repo_name: str, workflow_name: str, org_name: GITHUB_ORGS_OPTIONS) -> str:
  """
  Retrieves the CI status of the last run for a specified workflow in a GitHub repo.
  Args:
    repo_name (str): The name of the repo.
    workflow_name (str): The name of the workflow.
    org_name (str): The name of the organization. Defaults to cisco-eti.
  Returns:
    str: The status of the last run of the specified workflow.
  Raises:
    ValueError: If the repo name, organization name, or workflow name is invalid.
    Exception: For any other errors that occur during the retrieval process.
  """
  if not repo_name or not org_name or not workflow_name:
    raise ValueError("Repository name, organization name, and workflow name must be provided.")

  logging.info("Starting CI status retrieval process.")
  GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

  # using an access token
  auth = Auth.Token(GITHUB_TOKEN)

  # Public Web Github
  g = Github(auth=auth)

  try:
    logging.info(f"Retrieved repo: {repo_name} under organization: {org_name}, workflow: {workflow_name}")

    repo = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo_name}")

    workflows = await asyncio.to_thread(repo.get_workflows)
    workflow = next((wf for wf in workflows if wf.name == workflow_name), None)
    if not workflow:
      raise ValueError(f"Workflow '{workflow_name}' not found in repo '{repo_name}'.")

    logging.info(f"Found workflow: {workflow_name}")

    runs = await asyncio.to_thread(workflow.get_runs)
    if runs.totalCount == 0:
      logging.warning(f"No runs found for workflow '{workflow_name}' in repo '{repo_name}'.")
      return f"No runs found for workflow '{workflow_name}' in repo '{repo_name}'."

    last_run = runs[0]
    status = last_run.conclusion or "unknown"
    logging.info(f"Last run status for workflow '{workflow_name}': {status}")
  except Exception as e:
    logging.error(f"Failed to retrieve CI status: {str(e)}")
    raise Exception(f"Failed to retrieve CI status: {str(e)}")
  finally:
    await asyncio.to_thread(g.close)

  return f"The last run of workflow '{workflow_name}' in repo '{repo_name}' concluded with status: {status}"


async def list_ci_workflows(repo_name: str, org_name: GITHUB_ORGS_OPTIONS) -> list:
  """
  Retrieves a list of CI workflows for a specified GitHub repo.
  Args:
    repo_name (str): The name of the repo.
    org_name (str): The name of the organization. Defaults to cisco-eti.
  Returns:
    list: A list of workflow names.
  Raises:
    ValueError: If the repo name or organization name is invalid.
    Exception: For any other errors that occur during the retrieval process.
  """
  if not repo_name or not org_name:
    raise ValueError("Repository name and organization name must be provided.")

  logging.debug("Starting CI workflows listing process.")
  GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

  # using an access token
  auth = Auth.Token(GITHUB_TOKEN)

  # Public Web Github
  g = Github(auth=auth)

  try:
    repo = await asyncio.to_thread(g.get_repo, f"{org_name}/{repo_name}")
    logging.info(f"Retrieved repo: {repo_name} under organization: {org_name}")

    workflows = await asyncio.to_thread(repo.get_workflows)
    workflow_names = [wf.name for wf in workflows]
    logging.info(f"Found workflows: {workflow_names}")
  except Exception as e:
    logging.error(f"Failed to retrieve workflows: {str(e)}")
    raise Exception(f"Failed to retrieve workflows: {str(e)}")
  finally:
    await asyncio.to_thread(g.close)

  return workflow_names
