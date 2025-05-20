# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import traceback
from langchain_core.messages import AIMessage

from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.llm_factory import get_llm_connection_with_tools
from multi_agent_jarvis.state import AgentState
from multi_agent_jarvis.utils import process_llm_response
from multi_agent_jarvis.agents.backstage_agent.sys_msg import backstage_sys_msg
from multi_agent_jarvis.agents.backstage_agent.tools import backstage_tools

async def backstage_agent(state: AgentState):
  try:
    llm = await get_llm_connection_with_tools(backstage_tools)
    response = await llm.ainvoke([backstage_sys_msg] + state["messages"])
    return process_llm_response(response, backstage_tools)
  except Exception as e:
    logging.error(f"Error during backstage agent invoke: {traceback.format_exc()}")
    return {"messages": [AIMessage(f"{type(e).__name__}: {e}")]}
