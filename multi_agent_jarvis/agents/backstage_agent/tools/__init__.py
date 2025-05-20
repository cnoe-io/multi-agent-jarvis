# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from multi_agent_jarvis.agents.backstage_agent.tools.tools import (
  tool_get_backstage_catalog_entities,
  tool_get_backstage_groups_by_user,
  tool_get_backstage_projects_by_user,
)

backstage_tools = [
  tool_get_backstage_catalog_entities,
  tool_get_backstage_groups_by_user,
  tool_get_backstage_projects_by_user,
]
