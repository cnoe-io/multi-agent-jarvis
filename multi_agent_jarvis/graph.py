# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from multi_agent_jarvis.agent import JarvisMultiAgentSystem

"""
This script initializes a JarvisMultiAgentSystem and retrieves its graph representation.

- Imports the `JarvisMultiAgentSystem` class from the `multi_agent_jarvis.agent` module.
- Instantiates a `JarvisMultiAgentSystem` object with `checkpointer` and `store` set to `None`.
  By default, LangGraph uses an in-memory checkpointer and memory store.
- Calls the `get_graph()` method on the agent to obtain the system's graph.

Returns:
    The graph representation of the Jarvis multi-agent system.
"""

jarvis_agent = JarvisMultiAgentSystem(checkpointer = None, store = None)
graph = jarvis_agent.get_graph()
