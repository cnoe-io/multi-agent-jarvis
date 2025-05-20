# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

# Jira Comment
from .jira_comment import (
  _add_jira_comment,
  add_comment_string_to_jira_ticket,
  add_comment_adf_to_jira_ticket,
  get_last_jira_comment
)
# Jira Issue
from .jira_issue import (
  create_jira_issue,
  assign_jira,
  update_issue_reporter,
  add_new_label_to_issue,
  _add_new_label_to_issue,
  get_jira_issue_details,
)
# Jira Search
from .jira_search import (
  retrieve_multiple_jira_issues,
  search_jira_using_jql,
)
# Jira User
from .jira_user import (
  get_jira_assignee,
  get_jira_reporter_displayname,
  get_jira_reporter_account_id,
  get_account_id_from_email,
  get_jira_reporter_email,
  _get_jira_reporter_email
)
# Jira Transitions
from .jira_transitions import (
  get_jira_transitions,
  perform_jira_transition
)
# Outshift SRE Jira Utils
from .outshift_sre_jira_utils import (
  create_outshift_service_desk_ticket,
  _create_outshift_service_desk_ticket,
  retrieve_outshift_service_desk_tickets
)
# Utils
from .jira_webhook_utils import (
  process_jira_webhook
)
from .jira_comment import (
  jira_comment_body_adf
)

tools =[
  ## Jira Comment
  add_comment_string_to_jira_ticket,
  get_last_jira_comment,
  # ## Jira Issue
  create_jira_issue,
  assign_jira,
  update_issue_reporter,
  get_jira_issue_details,
  add_new_label_to_issue,
  ## Jira User
  get_jira_assignee,
  get_jira_reporter_displayname,
  get_jira_reporter_email,
  get_account_id_from_email,
  ## Jira Transitions
  get_jira_transitions,
  perform_jira_transition,
  ## Jira Search
  retrieve_multiple_jira_issues,
  search_jira_using_jql,
  # Outshift SRE Jira Utils
  create_outshift_service_desk_ticket,
  retrieve_outshift_service_desk_tickets,
]

__all__ = [
  '_add_jira_comment',
  'add_comment_string_to_jira_ticket',
  'add_comment_adf_to_jira_ticket',
  'get_last_jira_comment',
  'create_jira_issue',
  'assign_jira',
  'update_issue_reporter',
  'add_new_label_to_issue',
  '_add_new_label_to_issue',
  'get_jira_issue_details',

  'retrieve_multiple_jira_issues',
  'search_jira_using_jql',
  'get_jira_assignee',
  'get_jira_reporter_displayname',
  'get_jira_reporter_account_id',
  'get_account_id_from_email',
  'get_jira_reporter_email',
  '_get_jira_reporter_email',
  'get_jira_transitions',
  'perform_jira_transition',
  'create_outshift_service_desk_ticket',
  '_create_outshift_service_desk_ticket',
  'retrieve_outshift_service_desk_tickets',
  'process_jira_webhook',
  'jira_comment_body_adf',
]