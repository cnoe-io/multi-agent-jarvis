# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from .tools import (
  tool_create_github_repo,
  tool_add_existing_git_repo_to_backstage_component,
  tool_list_ci_workflows,
  tool_retrieve_ci_status,
  tool_retrieve_ci_logs,

  tool_list_pull_requests,
  tool_read_pull_request,
  tool_update_pull_request,
  tool_add_pull_request_comment,
  tool_read_latest_pull_request_comments,

  tool_get_repo_description,
  tool_get_repo_topics,
  tool_get_repo_members,

)

tools = [
  tool_create_github_repo,
  tool_add_existing_git_repo_to_backstage_component,
  tool_list_ci_workflows,
  tool_retrieve_ci_status,
  tool_retrieve_ci_logs,

  tool_list_pull_requests,
  tool_read_pull_request,
  tool_update_pull_request,
  tool_add_pull_request_comment,
  tool_read_latest_pull_request_comments,

  tool_get_repo_description,
  tool_get_repo_topics,
  tool_get_repo_members,
]