# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os

async def _urlify_jira_issue_id(issue_id: str) -> str:
  """
  Convert a Jira issue ID to a URL.

  Args:
    issue_id (str): The Jira issue ID.

  Returns:
    str: The URL of the Jira issue.
  """
  jira_server = os.getenv("JIRA_SERVER")
  return f"{jira_server}/browse/{issue_id}"

async def _create_jira_urlified_list(issues) -> list:
  """
    Create a list of Jira issues in Markdown format with clickable links.

    Args:
        issues (list): A list of Jira issue objects. Each object is expected to have a 'key' attribute
                       representing the issue key (e.g., "PROJECT-123").

    Returns:
        list: A list of strings, where each string is a Markdown-formatted link to a Jira issue.
              The format is "[ISSUE_KEY](ISSUE_URL)".
  """
  issues_md = []
  for issue in issues:
    issue_link = await _urlify_jira_issue_id(issue.key)
    issue_summary = issue.fields.summary
    issues_md.append(f"[{issue.key}: {issue_summary}]({issue_link})")
  return issues_md
