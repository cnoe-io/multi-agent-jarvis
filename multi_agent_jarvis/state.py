# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from typing import List, Literal

from langgraph.graph import MessagesState

from multi_agent_jarvis.models import JarvisResponseMetadata
from multi_agent_jarvis.globals import GraphState

# AgentState
class AgentState(MessagesState):
  # The next agent to call
  next: Literal[
    GraphState.ARGOCD,
    GraphState.BACKSTAGE,
    GraphState.GITHUB,
    GraphState.PAGERDUTY,
    GraphState.JIRA,
    GraphState.NOTHING,
  ]

  metadata: List[JarvisResponseMetadata]
  # The local path of the target Github repo for the K8s agent
  target_repo: str
  # The iteration for K8s code generation
  i: int
  times_continued: int
  code_gen_tool_calls: int
  kubectl_tool_calls: int