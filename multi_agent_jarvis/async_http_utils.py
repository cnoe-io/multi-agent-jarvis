# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from aiohttp import ClientSession, ClientTimeout
import os
from multi_agent_jarvis.setup_logging import logging as log


def with_async_http_session(func):
  async def with_async_http_session_wrapper(*args, **kwargs):
    session_timeout = int(os.getenv("JARVIS_GLOBAL_SESSION_TIMEOUT", "30"))
    async with ClientSession(timeout=ClientTimeout(session_timeout)) as session:
      try:
        return await func(session, *args, **kwargs)
      finally:
        log.info(f"Closing AsyncHttpSession in function: {func.__name__}")
        await session.close()

  return with_async_http_session_wrapper


class AsyncHttpSession:
  """Singleton class to manage the Async HTTP Session instance."""

  _instance = None

  @classmethod
  async def get_instance(cls):
    """Get or create the singleton instance. This function has to be async so that it shares the same event loop as FastAPI."""
    if cls._instance is None:
      session_timeout = int(os.getenv("JARVIS_GLOBAL_SESSION_TIMEOUT", "30"))

      log.info(f"Creating new AsyncHttpSession instance with a global timeout {session_timeout}s")
      cls._instance = ClientSession(timeout=ClientTimeout(session_timeout))
    return cls._instance

  @classmethod
  async def close(cls):
    """Close the aiohttp session."""
    if cls._instance is None:
      log.error("Can't close as AsyncHttpSession instance doesn't exist")
    else:
      log.info("Closing AsyncHttpSession")
      await cls._instance.close()
