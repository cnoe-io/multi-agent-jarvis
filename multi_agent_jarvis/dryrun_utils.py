# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from multi_agent_jarvis.setup_logging import logging

def dryrun_response(mock_response):
  def dryrun_response_decorator(func):
    async def dryrun_response_wrapper(*args, **kwargs):
      if os.getenv("JARVIS_DRYRUN") == "true":
        logging.info("Running in dry-run mode, returning mock data.")
        return mock_response
      return await func(*args, **kwargs)
    return dryrun_response_wrapper
  return dryrun_response_decorator
