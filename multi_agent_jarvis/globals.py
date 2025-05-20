# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import sys
from typing import Literal
from enum import Enum


### Graph States
class GraphState(Enum):
  ARGOCD = sys.intern("argocd")
  BACKSTAGE = sys.intern("backstage")
  GITHUB = sys.intern("github")
  JIRA = sys.intern("jira")
  PAGERDUTY = sys.intern("pagerduty")
  WHAT_CAN_YOU_DO = sys.intern("what can you do")
  NOTHING = sys.intern("nothing")


RouterNextActions = Literal[
  GraphState.ARGOCD.value,
  GraphState.BACKSTAGE.value,
  GraphState.GITHUB.value,
  GraphState.JIRA.value,
  GraphState.PAGERDUTY.value,
  GraphState.WHAT_CAN_YOU_DO.value,
]


### Graph Node Labels

# String interning is a method of storing only one copy of each distinct
# string value, which must be immutable. Interning strings can save memory
# and speed up string comparisons.

# Router Agent Nodes
SUPERVISOR_AGENT = sys.intern("supervisor_agent")
# Helper Agent Nodes
WHAT_CAN_YOU_DO_AGENT = sys.intern("what_can_you_do_agent")
# Observation Agent Nodes
REFLECTION_AGENT = sys.intern("reflection_agent")

# Agent Nodes
ARGOCD_AGENT = sys.intern("argocd_agent")
AWS_AGENT = sys.intern("aws_agent")
BACKSTAGE_AGENT = sys.intern("backstage_agent")
GITHUB_AGENT = sys.intern("github_agent")
JIRA_AGENT = sys.intern("jira_agent")
PAGERDUTY_AGENT = sys.intern("pagerduty_agent")

# Agent Tools
ARGOCD_TOOLS = sys.intern("argocd_tools")
BACKSTAGE_TOOLS = sys.intern("backstage_tools")
GITHUB_TOOLS = sys.intern("github_tools")
JIRA_TOOLS = sys.intern("jira_tools")
PAGERDUTY_TOOLS = sys.intern("pagerduty_tools")

# Agent States Mapping
GRAPH_STATE_TO_NEXT_ACTIONS = {
  GraphState.ARGOCD.value: ARGOCD_AGENT,
  GraphState.BACKSTAGE.value: BACKSTAGE_AGENT,
  GraphState.GITHUB.value: GITHUB_AGENT,
  GraphState.JIRA.value: JIRA_AGENT,
  GraphState.PAGERDUTY.value: PAGERDUTY_AGENT,
  GraphState.WHAT_CAN_YOU_DO.value: WHAT_CAN_YOU_DO_AGENT,
}


RouterNextActions = Literal[
  GraphState.ARGOCD.value,
  GraphState.BACKSTAGE.value,
  GraphState.GITHUB.value,
  GraphState.JIRA.value,
  GraphState.PAGERDUTY.value,
  GraphState.WHAT_CAN_YOU_DO.value,
]