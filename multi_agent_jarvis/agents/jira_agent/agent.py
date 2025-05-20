# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
import traceback
from langchain_core.messages import AIMessage
from multi_agent_jarvis.globals import SUPERVISOR_AGENT
from multi_agent_jarvis.llm_factory import JarvisLLMFactory

from multi_agent_jarvis.state import AgentState
from multi_agent_jarvis.utils import tool_call_response
from multi_agent_jarvis.models import JarvisResponse
from multi_agent_jarvis.agents.jira_agent.jira_sys_msg import jira_sys_msg
from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.agents.jira_agent.tools import tools


async def get_llm_connection():
  model_name = os.getenv("JARVIS_LLM_MODEL_NAME", "gpt-4o-mini")
  llm_factory = JarvisLLMFactory(model_name)
  return llm_factory.get_llm_connection(response_format=JarvisResponse).bind_tools(tools, strict=True)


async def jira_agent(state: AgentState):
  try:
    llm_jira = await get_llm_connection()
    response = await llm_jira.ainvoke([jira_sys_msg] + state["messages"])
    structured_response = response.additional_kwargs["parsed"]
    if response.tool_calls:
      return tool_call_response(structured_response, response, tools, SUPERVISOR_AGENT)
    elif structured_response:
      return {"messages": [AIMessage(structured_response.answer)], "metadata": [structured_response.metadata]}
    else:
      raise ValueError("Need either tool calls or structured response")
  except Exception as e:
    logging.error(f"Error during jira agent invoke: {traceback.format_exc()}")
    return {"messages": [AIMessage(f"{type(e).__name__}: {e}")]}
