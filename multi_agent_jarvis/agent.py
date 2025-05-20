# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
import datetime
from pydantic import BaseModel, Field

import traceback
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, RemoveMessage
from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode

from multi_agent_jarvis.setup_logging import logging

from multi_agent_jarvis.globals import (
  SUPERVISOR_AGENT,
  REFLECTION_AGENT,
  WHAT_CAN_YOU_DO_AGENT,
  ARGOCD_AGENT,
  ARGOCD_TOOLS,
  BACKSTAGE_AGENT,
  BACKSTAGE_TOOLS,
  GITHUB_AGENT,
  GITHUB_TOOLS,
  JIRA_AGENT,
  JIRA_TOOLS,
  PAGERDUTY_AGENT,
  PAGERDUTY_TOOLS,
)
from multi_agent_jarvis.globals import GRAPH_STATE_TO_NEXT_ACTIONS
from multi_agent_jarvis.models import JarvisResponseMetadata, JarvisResponse, SupervisorAction
from multi_agent_jarvis.state import AgentState
from multi_agent_jarvis.utils import custom_tools_condition
from multi_agent_jarvis.prompts import sys_msg_supervisor, sys_msg_reflection

from multi_agent_jarvis.llm_factory import JarvisLLMFactory
from langchain_core.runnables.config import RunnableConfig

from multi_agent_jarvis.agents.argocd_agent.agent import argocd_agent
from multi_agent_jarvis.agents.argocd_agent.tools import tools as argocd_tools

from multi_agent_jarvis.agents.backstage_agent.agent import backstage_agent
from multi_agent_jarvis.agents.backstage_agent.tools import backstage_tools

from multi_agent_jarvis.agents.github_agent.agent import github_agent
from multi_agent_jarvis.agents.github_agent.tools import tools as github_tools

from multi_agent_jarvis.agents.jira_agent.agent import jira_agent
from multi_agent_jarvis.agents.jira_agent.tools import tools as jira_tools

from multi_agent_jarvis.agents.pagerduty_agent.agent import pagerduty_agent
from multi_agent_jarvis.agents.pagerduty_agent.tools import tools as pagerduty_tools

class JarvisMultiAgentSystem:
  """
  JarvisMultiAgentSystem orchestrates a modular, multi-agent architecture inspired by the design described in
  a technical deep dive blog. It coordinates specialized agents—each encapsulating domain expertise
  (e.g., GitHub, Jira, ArgoCD, PagerDuty, Backstage)—to collaboratively solve complex user requests.

  Key Features:
    - Supervisor Agent: Acts as the central orchestrator, decomposing user queries, delegating tasks, and managing agent interactions.
    - Specialized Task Agents: Each agent (e.g., GitHub, Jira) is responsible for a specific domain, encapsulating its own tools and logic.
    - Reflection Agent: Provides self-reflection and loop control, ensuring the system avoids redundant actions and halts gracefully.
    - Tool Nodes: Integrate external APIs and actions as modular, reusable components.
    - StateGraph Orchestration: Uses a state machine to manage agent transitions, memory, and task flow, enabling dynamic, context-aware decision making.
    - Extensibility: New agents and tools can be added with minimal changes, supporting evolving workflows and integrations.

  Attributes:
    checkpointer: Manages persistent state across agent interactions.
    store: Backend storage for agent state and memory.
    builder: StateGraph instance defining agent nodes, edges, and transitions.
    react_graph_memory: Compiled state graph for executing multi-agent workflows.

  Methods:
    get_state(thread_id: str): Retrieve the current state for a conversation thread.
    get_state_history(thread_id: str): Retrieve the full state history for a thread.
    interact(human_message: str, thread_id: str, user_email: str): Process a user message through the multi-agent system.
    create_graph_image(): Generate and save a visual representation of the agent state graph.
    get_graph(): Access the underlying state graph object.

  Example:
    multi_agent_jarvis = JarvisMultiAgentSystem(checkpointer, store)
    state = await multi_agent_jarvis.get_state(thread_id="12345")
    async for response in multi_agent_jarvis.interact("Deploy my app", thread_id="12345", user_email="user@example.com"):
        print(response)

  For more details, see:
    https://outshift.cisco.com/blog/architecting-jarvis-technical-deep-dive-into-its-multi-agent-system-design
  """

  def __init__(self, checkpointer, store):
    # Initialize JarvisLLMFactory with the desired model name
    model_name = os.getenv("JARVIS_LLM_MODEL_NAME", "gpt-4o-mini")
    llm_factory = JarvisLLMFactory(model_name)

    llm_supervisor = llm_factory.get_llm_connection().with_structured_output(SupervisorAction, strict=True)
    llm_what_can_you_do = llm_factory.get_llm_connection(response_format=JarvisResponse)

    class ShouldContinue(BaseModel):
      should_continue: bool = Field(description="Whether to continue processing the request.")
      reason: str = Field(description="Reason for decision whether to continue the request.")

    llm_reflection = llm_factory.get_llm_connection().with_structured_output(ShouldContinue, strict=True)

    # Node
    async def supervisor_agent(state: AgentState, config: RunnableConfig):
      try:
        logging.info("Entering supervisor agent")
        logging.debug(f"sys_msg_supervisor: {sys_msg_supervisor.content}")
        response = await llm_supervisor.ainvoke(
          [sys_msg_supervisor] + state["messages"]
        )
        logging.info("*" * 50)
        logging.info(response)
        logging.info("*" * 50)
        # Generate the list of messages to delete
        max_messages = int(os.getenv("JARVIS_MAX_MESSAGES", "20"))
        # Check if the last message exists and if it is a tool message
        if len(state["messages"]) >= max_messages and isinstance(state["messages"][-max_messages], ToolMessage):
          # Keep one more as it's the message with tool_calls
          max_messages += 1
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-max_messages]]
        return {"next": response.action, "messages": delete_messages}
      except Exception:
        logging.error(f"Error during supervisor agent invoke: {traceback.format_exc()}")
        return {"next": "what can you do"}

    # Node
    async def what_can_you_do_agent(state: AgentState, config: RunnableConfig):
      try:
        response = await llm_what_can_you_do.ainvoke(
          [sys_msg_supervisor] + state["messages"]
        )
        response = response.additional_kwargs["parsed"]
        logging.info({"messages": [AIMessage(response.answer)], "metadata": [response.metadata]})
        return {"messages": [AIMessage(response.answer)], "metadata": [response.metadata]}
      except Exception as e:
        logging.error(f"Error during 'what can you do' agent invoke: {traceback.format_exc()}")
        return {
          "messages": [AIMessage(f"{type(e).__name__}: {e}")],
          "metadata": [JarvisResponseMetadata(user_input=False, input_fields=[])],
        }

    # Node
    async def reflection_agent(state: AgentState, config: RunnableConfig):
      try:
        response = await llm_reflection.ainvoke(
          [sys_msg_reflection] + state["messages"]
        )
        logging.info(f"Reflection agent response: {response}")
        is_duplicate_message = (
          len(state["messages"]) > 2 and state["messages"][-1].content == state["messages"][-3].content
        )
        is_user_input_required = state["metadata"][-1].user_input
        should_continue = response.should_continue and not is_user_input_required and not is_duplicate_message
        logging.info(f"Should continue: {should_continue}")
        next_node = SUPERVISOR_AGENT if should_continue else END
        logging.info(f"Next node: {next_node}")
        return {
          "next": next_node,
          "messages": [SystemMessage(content=response.reason)],
          "metadata": [JarvisResponseMetadata(user_input=False, input_fields=[])],
        }
      except Exception:
        logging.error(f"Error during reflection agent invoke: {traceback.format_exc()}")
        return {"next": END}

    # Graph
    self.builder = StateGraph(AgentState)

    # Define nodes: They do the actual work
    self.builder.add_node(SUPERVISOR_AGENT, supervisor_agent)
    self.builder.add_node(WHAT_CAN_YOU_DO_AGENT, what_can_you_do_agent)
    self.builder.add_node(REFLECTION_AGENT, reflection_agent)

    # Task Agent Nodes and Tools

    ## ArgoCD
    self.builder.add_node(ARGOCD_AGENT, argocd_agent)
    self.builder.add_node(ARGOCD_TOOLS, ToolNode(argocd_tools))

    ## Backstage
    self.builder.add_node(BACKSTAGE_AGENT, backstage_agent)
    self.builder.add_node(BACKSTAGE_TOOLS, ToolNode(backstage_tools))

    ## GitHub
    self.builder.add_node(GITHUB_AGENT, github_agent)
    self.builder.add_node(GITHUB_TOOLS, ToolNode(github_tools))

    ## Jira
    self.builder.add_node(JIRA_AGENT, jira_agent)
    self.builder.add_node(JIRA_TOOLS, ToolNode(jira_tools))

    ## PagerDuty
    self.builder.add_node(PAGERDUTY_AGENT, pagerduty_agent)
    self.builder.add_node(PAGERDUTY_TOOLS, ToolNode(pagerduty_tools))

    #######################################
    ######### Jarvis Assistant Graph ######
    #######################################
    self.builder.add_edge(START, SUPERVISOR_AGENT)
    self.builder.add_conditional_edges(
      SUPERVISOR_AGENT,
      lambda state: state["next"],
      GRAPH_STATE_TO_NEXT_ACTIONS,
    )

    # What Can You Do Agent Transitions
    # what_can_you_do_agent ==> END
    self.builder.add_edge(WHAT_CAN_YOU_DO_AGENT, END)

    # ArgoCD Agent Transitions
    self.builder.add_conditional_edges(ARGOCD_AGENT, custom_tools_condition(ARGOCD_TOOLS, REFLECTION_AGENT))
    # argocd_tools ==> argocd_agent
    self.builder.add_edge(ARGOCD_TOOLS, ARGOCD_AGENT)

    # Backstage Agent Transitions
    self.builder.add_conditional_edges(BACKSTAGE_AGENT, custom_tools_condition(BACKSTAGE_TOOLS, REFLECTION_AGENT))
    # backstage_tools ==> backstage_agent
    self.builder.add_edge(BACKSTAGE_TOOLS, BACKSTAGE_AGENT)

    # GitHub Agent Transitions
    self.builder.add_conditional_edges(GITHUB_AGENT, custom_tools_condition(GITHUB_TOOLS, REFLECTION_AGENT))
    # github_tools ==> github_agent
    self.builder.add_edge(GITHUB_TOOLS, GITHUB_AGENT)

    # Jira Agent Transitions
    self.builder.add_conditional_edges(JIRA_AGENT, custom_tools_condition(JIRA_TOOLS, REFLECTION_AGENT))
    # jira_tools ==> jira_agent
    self.builder.add_edge(JIRA_TOOLS, JIRA_AGENT)

    # PagerDuty Agent Transitions
    self.builder.add_conditional_edges(PAGERDUTY_AGENT, custom_tools_condition(PAGERDUTY_TOOLS, REFLECTION_AGENT))
    # pagerduty_tools ==> pagerduty_agent
    self.builder.add_edge(PAGERDUTY_TOOLS, PAGERDUTY_AGENT)

    # Compile Graph
    self.react_graph_memory = self.builder.compile(checkpointer=checkpointer, store=store)

  async def get_state(self, thread_id: str):
    """Retrieves the state for a given thread ID."""
    config = {"configurable": {"thread_id": thread_id}}
    return self.react_graph_memory.get_state(config=config)

  async def get_state_history(self, thread_id: str):
    """Retrieves the state history for a given thread ID."""
    config = {"configurable": {"thread_id": thread_id}}
    return self.react_graph_memory.get_state_history(config=config)

  async def interact(self, human_message: str, thread_id: str, user_email: str):
    # Log the arguments
    logging.info(f"Arguments - human_message: {human_message}, thread_id: {thread_id}, user_email: {user_email}")
    try:
      # Specify a thread
      config = {
        "recursion_limit": int(os.getenv("JARVIS_RECURSION_LIMIT", "30")),
        "configurable": {
          "thread_id": thread_id,
        },
      }

      # Specify an input
      messages = [HumanMessage(content=human_message)]
      # Log the incoming human message
      logging.info(f"Received human message: {human_message}")

      # Log the initial messages
      logging.debug(f"Initial messages: {messages}")

      all_messages = []
      async for chunk in self.react_graph_memory.astream({"messages": messages}, config=config, stream_mode="updates"):
        for node, values in chunk.items():
          logging.debug(f"Receiving update from node: '{node}'")
          logging.debug(values)
          if "messages" in values:
            all_messages.extend(values["messages"])
            message = "\n".join(
              m.content
              for m in values["messages"]
              if not isinstance(m, SystemMessage)
              and (
                node
                not in [
                  ARGOCD_TOOLS,
                  BACKSTAGE_TOOLS,
                  GITHUB_TOOLS,
                  JIRA_TOOLS,
                  PAGERDUTY_TOOLS,
                ]
              )
            )
            if "metadata" in values and len(values["metadata"]) > 0:
              metadata = values["metadata"][-1].model_dump()
            else:
              metadata = {}
            if message:
              yield {"answer": message, "metadata": metadata}
      yield {}
    except Exception as e:
      logging.error(f"Error in interact method: {traceback.format_exc()}")
      logging.error(f"{type(e).__name__}: {e}")
      yield {"answer": "Jarvis Agent is not available right now. Please try again later!"}

  def create_graph_image(self):
    graph_image = self.react_graph_memory.get_graph(xray=1).draw_mermaid_png()
    timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    filename = f"multi_agent_jarvis_{timestamp}.png"
    with open(filename, "wb") as f:
      f.write(graph_image)
    print(f"Graph image saved as '{filename}'. Open this file to view the graph.")

  def get_graph(self):
    return self.react_graph_memory


if __name__ == "__main__":
  JarvisAgent(None, None).create_graph_image()
