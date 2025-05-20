# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os

from multi_agent_jarvis.setup_logging import logging

from multi_agent_jarvis.async_http_utils import with_async_http_session
from multi_agent_jarvis.dryrun_utils import dryrun_response
from multi_agent_jarvis.agents.backstage_agent.api.dryrun.mock_responses import (
  MOCK_GET_BACKSTAGE_CATALOG_ENTRIES_RESPONSE,
)
from multi_agent_jarvis.agents.backstage_agent.api.common import BACKSTAGE_URL

@dryrun_response(MOCK_GET_BACKSTAGE_CATALOG_ENTRIES_RESPONSE)
@with_async_http_session
async def get_backstage_catalog_entities(session, user_id: str):
  """
  Fetch backstage catalog entities.

  This function sends a GET request to the catalog API to retrieve entities
  associated with the specified user ID. The request is authenticated using
  an API token obtained from the environment variable 'BACKSTAGE_API_TOKEN'.

  Returns:
    dict: A dictionary containing the JSON response from the API if the request is successful.

  Raises:
    HTTPError: If the request fails with a status code other than 200.
  """
  BACKSTAGE_API_TOKEN = os.getenv("BACKSTAGE_API_TOKEN")
  url = f"{BACKSTAGE_URL}/api/catalog/entities/by-query?filter=kind=user,metadata.name={user_id}"
  logging.info(f"URL: {url}")
  headers = {"Authorization": f"Bearer {BACKSTAGE_API_TOKEN}"}

  logging.info(f"Fetching catalog entities for user_id: {user_id}")

  async with session.get(url, headers=headers) as response:
    response_text = await response.text()
    logging.info(f"Response: {response_text}")

    if response.status == 200:
      logging.info("Request successful")
      return await response.json()
    else:
      logging.error(f"Request failed with status code: {response.status}")
      response.raise_for_status()
