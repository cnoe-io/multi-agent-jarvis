# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import traceback
from langchain_core.messages import AIMessage
from multi_agent_jarvis.llm_factory import get_llm_connection_with_tools
from multi_agent_jarvis.state import AgentState
from multi_agent_jarvis.utils import process_llm_response

from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.agents.argocd_agent.tools import tools
from multi_agent_jarvis.agents.argocd_agent.sys_msg import sys_msg

async def argocd_agent(state: AgentState):
  try:
    llm_argocd = await get_llm_connection_with_tools(tools)
    response = await llm_argocd.ainvoke([sys_msg] + state["messages"])
    return process_llm_response(response, tools)
  except Exception as e:
    logging.error(f"Error during argocd agent invoke: {traceback.format_exc()}")
    return {"messages": [AIMessage(f"{type(e).__name__}: {e}")]}
