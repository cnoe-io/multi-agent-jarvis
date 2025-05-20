# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from multi_agent_jarvis.setup_logging import logging as log
import traceback
from typing import Any, Literal, Union
from pydantic import BaseModel
from multi_agent_jarvis.setup_logging import logging
from langchain_core.messages import SystemMessage, AnyMessage, AIMessage
from multi_agent_jarvis.globals import SUPERVISOR_AGENT
from multi_agent_jarvis.models import JarvisResponseMetadata

def print_banner(message: str, sub_message: str = ""):
  banner_width = 60  # Adjust as needed
  message_len = len(message)
  sub_message_len = len(sub_message)
  message_padding = (banner_width - message_len) // 2
  sub_message_padding = (banner_width - sub_message_len) // 2
  message_centered = " " * message_padding + message + " " * (banner_width - message_len - message_padding - 2)
  sub_message_centered = (
    " " * sub_message_padding + sub_message + " " * (banner_width - sub_message_len - sub_message_padding - 2)
  )

  banner = f"""
  ############################################################
  #                                                          #
  #{message_centered}#
  #                                                          #
  #{sub_message_centered}#
  ############################################################
  """
  print(banner)


def custom_tools_condition(tools_node: str, end_node: str = "__end__"):
  """Return a function that returns the tools_node if the last message has tool calls. Otherwise return the end_node."""

  def custom_tools_condition_fn(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = "messages",
  ) -> Literal[tools_node, end_node]:
    if isinstance(state, list):
      ai_message = state[-1]
    elif isinstance(state, dict) and (messages := state.get(messages_key, [])):
      ai_message = messages[-1]
    elif messages := getattr(state, messages_key, []):
      ai_message = messages[-1]
    else:
      raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
      return tools_node
    return end_node

  return custom_tools_condition_fn


def tool_call_response(structured_response, response, tools_list, tool_call_counter=None, tool_call_count=0):
  """Returns either a tool call response or jumps to target_node if a tool name is invalid. Optionally keeps track of tool call counts."""
  logging.info("Entering tool_call_response function.")
  try:
    if structured_response:
      # Parse out structured response in addition to tool calls.
      logging.info("Structured response found, updating response content.")
      response.content = structured_response.answer
    # Check for a bad tool name from the LLM
    for t in response.tool_calls:
      tool_name = t["name"]
      logging.info(f"Checking tool name: {tool_name}")
      # Jump to target_node if tool_name not in tools_list.
      valid_tools = []
      for t in tools_list:
        if hasattr(t, "name"):
          valid_tools.append(t.name)
        else:
          logging.warning(f"Not a tool: {t}")
      if tool_name not in valid_tools:
        logging.warning("Bad tool name")
        return {
          "messages": [SystemMessage(f"Invalid tool: {tool_name}, try another agent.")],
          "metadata": [JarvisResponseMetadata(user_input=False, input_fields=[])],
        }
    result = {"messages": [response], "metadata": [JarvisResponseMetadata(user_input=False, input_fields=[])]}
    if tool_call_counter not in [None, "messages", "metadata"]:
      result[tool_call_counter] = tool_call_count + len(response.tool_calls)
    logging.info("Returning tool call response.")
    logging.info(f"tool_call_response result: {result}")
    return result
  except Exception:
    logging.error(f"Error during tool_call_response function: {traceback.format_exc()}")
    raise


def process_llm_response(response, tools):
  logging.info("Processing LLM response...")
  structured_response = response.additional_kwargs["parsed"]
  if response.tool_calls:
    logging.info("Tool calls found in response.")
    return tool_call_response(structured_response, response, tools, SUPERVISOR_AGENT)
  elif structured_response:
    logging.info("Structured response found, no tool calls.")
    return {"messages": [AIMessage(structured_response.answer)], "metadata": [structured_response.metadata]}
  else:
    logging.warning("Neither tool calls nor structured response found.")
    raise ValueError("Need either tool calls or structured response")
