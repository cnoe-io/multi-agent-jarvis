# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from requests.auth import HTTPBasicAuth
from multi_agent_jarvis.setup_logging import logging
from jira import JIRA

class JiraInstanceManager:
  """Singleton class to manage the JIRA instance and HTTPBasicAuth."""

  _jira_instance = None
  _auth_instance = None
  _jira_server_url = os.getenv('JIRA_SERVER')
  _jira_headers =   headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
  }

  @classmethod
  def get_jira_instance(cls):
    if cls._jira_instance is None:
      jira_token = os.getenv("JARVIS_JIRA_ACCESS_TOKEN")
      jira_user = os.getenv("JARVIS_JIRA_USER_EMAIL")
      jira_server = os.getenv("JIRA_SERVER")

      logging.info(f"Creating new JIRA instance with server: {jira_server}, user: {jira_user}")
      cls._jira_instance = JIRA(server=jira_server, basic_auth=(jira_user, jira_token))

    logging.info("Returning JIRA instance")
    return cls._jira_instance

  @classmethod
  def get_auth_instance(cls):
    if cls._auth_instance is None:
      user_email = os.getenv('JARVIS_JIRA_USER_EMAIL')
      access_token = os.getenv('JARVIS_JIRA_ACCESS_TOKEN')

      logging.info(f"Creating new HTTPBasicAuth instance for server: {cls._jira_server_url}, user: {user_email}")
      cls._auth_instance = HTTPBasicAuth(user_email, access_token)

    logging.info("Returning HTTPBasicAuth instance")
    return cls._jira_server_url, cls._auth_instance, cls._jira_headers
