# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

jira_sys_msg = """## Jira
- Find Jira Account ID for a given email.
- Create a Jira service desk ticket.
- Get Jira service desk tickets
- Retrieve the latest n Jiras for a given user and project.
- Create and assign Jira issues
- Comment on Jira issues
- Get last comment from Jira issues
- Get Jira issue details
- Get reporter and assignee info
- Transition Jira issues
- Search for multiple Jira issues using JQL

Jira only LLM Instructions:
- Always convert email to account_id before using it in Jira API calls.
- If the assignee or reporter is an email, convert it to account_id before using it in Jira API calls."""
