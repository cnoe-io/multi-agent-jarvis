# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from multi_agent_jarvis.globals import PROJECT_NAME_TO_UUID

# Static mapping of email addresses to application names and projects
email_to_app_project = {
  "sraradhy@cisco.com": {
    "application_name": "outshift_infrastructure",
    "component": "jarvis",
    "resource_owner": "openg",
  },
}


def get_app_project_by_email(email):
  return email_to_app_project.get(
    email,
    {
      "application_name": "outshift_infrastructure",
      "component": "jarvis",
      "resource_owner": "openg",
    },
  )


def get_project_id_by_user_email(user_email: str):
  get_app_project_by_email(user_email).get("id")


def get_project_id_by_name(project_name: str):
  # Static mapping of project names to UUIDs
  if project_name not in PROJECT_NAME_TO_UUID:
    raise ValueError("Project not supported")
  return PROJECT_NAME_TO_UUID.get(project_name)
