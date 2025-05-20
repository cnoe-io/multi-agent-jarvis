# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from multi_agent_jarvis.setup_logging import logging
from langchain_core.tools import tool

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


@tool
async def deploy_app_to_common_cluster_using_argocd(
  app_name: str,
  user_email: str,
) -> str:
  """
  Deploys an application to the common cluster using ArgoCD.

  Args:
      app_name (str): Name of the application.

  Returns:
      str: Result message of the deployment process.

  Raises:
      ValueError: If the repository or organization name is missing, or if the project name is invalid.
  """
  pass