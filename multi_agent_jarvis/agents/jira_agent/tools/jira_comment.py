# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import requests
import json
from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.agents.jira_agent.tools._jira_instance import JiraInstanceManager
from typing import Union
from langchain_core.tools import tool
from multi_agent_jarvis.agents.jira_agent.models.jira_adf_model import (
  JiraADFModel,
  ParagraphContent,
  TextContent,
  TableContent,
  TableAttrs,
  TableRowContent,
  TableCellContent
)

async def _add_jira_comment(issue_key: str, input: Union[str, JiraADFModel]):
  """
  Add a comment to a JIRA ticket.

  Args:
    issue_key (str): Jira Issue Key.
    input (Union[str, JiraADFModel]): The comment to add to the JIRA issue.
      This can be a plain string or an instance of JiraADFModel.

  Returns:
    None

  Raises:
    ValueError: If the input is neither a string nor an instance of JiraADFModel.
  """
  jira_server_url, auth, headers = JiraInstanceManager.get_auth_instance()

  comment_url = f'{jira_server_url}/rest/api/3/issue/{issue_key}/comment'

  if isinstance(input, str):
    logging.info("Input is a string.")
    payload = json.dumps({
      'body': {
        'version': 1,
        'type': 'doc',
        'content': [
          {
            'type': 'paragraph',
            'content': [
              {
                'type': 'text',
                'text': input
              }
            ]
          }
        ]
      }
    })
  elif isinstance(input, JiraADFModel):
    logging.info("Input is an instance of JiraADFModel.")
    payload = json.dumps({'body': json.loads(input.model_dump_json(exclude_none=True))})
  else:
    logging.error("Input must be either a string or an instance of JiraADFModel.")
    raise ValueError("Input must be either a string or an instance of JiraADFModel")

  logging.info(f"comment_url: {comment_url}")
  logging.info(f"payload: {payload}")
  logging.info(f"headers: {headers}")
  logging.info(f"auth: {auth}")
  comment_response = requests.post(comment_url,
                   data=payload,
                   headers=headers,
                   auth=auth)
  if comment_response.status_code == 201:
    logging.info('Comment added to JIRA ticket successfully.')
  else:
    logging.info(f'Failed to add comment to JIRA ticket. Status code: {comment_response.status_code}, Response: {comment_response.text}')

@tool
async def add_comment_string_to_jira_ticket(issue_key: str, input: str):
  """
  Add a comment to a JIRA ticket.

  Args:
    issue_key (str): Jira Issue Key.
    input (str): Comment string.

  Returns:
    str: A message indicating the result of the transition.

  Raises:
    ValueError: If the input is neither a string nor an instance of JiraADFModel.
  """
  return await _add_jira_comment(issue_key, input)

async def add_comment_adf_to_jira_ticket(issue_key: str, input: JiraADFModel):
  """
  Add a comment to a JIRA ticket.

  Args:
    issue_key (str): Jira Issue Key.
    input JiraADFModel: Instance of JiraADFModel.

  Returns:
    str: A message indicating the result of the transition.

  Raises:
    ValueError: If the input is neither a string nor an instance of JiraADFModel.
  """
  return await _add_jira_comment(issue_key, input)

@tool
async def get_last_jira_comment(issue_key: str):
  """
  Get the last comment from a JIRA ticket.

  Args:
    issue_key (str): Jira Issue Key.

  Returns:
    dict: The last comment on the JIRA issue.
  """
  jira_server_url, auth, headers = JiraInstanceManager.get_auth_instance()

  comment_url = f'{jira_server_url}/rest/api/3/issue/{issue_key}/comment'
  logging.info(f"Fetching comments from: {comment_url}")

  response = requests.get(comment_url, headers=headers, auth=auth)
  if response.status_code == 200:
    comments = response.json().get('comments', [])
    if comments:
      last_comment = comments[-1]
      logging.info(f"Last comment: {last_comment}")
      return last_comment
    else:
      logging.info("No comments found on the JIRA ticket.")
      return {}
  else:
    logging.error(f"Failed to fetch comments. Status code: {response.status_code}, Response: {response.text}")
    return {}

############################################################################################################
# Utility functions for working with JIRA comments                                                         #
############################################################################################################


async def jira_comment_body_adf(message):
  """
  Formats the answer to be posted as a comment in JIRA.
  Args:
    answer: The answer to be posted.
    metadata: The metadata associated with the answer.
  Returns:
    str: The formatted comment body.
  """
  logging.info("Creating paragraph content for the answer.")
  paragraph = ParagraphContent(
    type="paragraph",
    content=[TextContent(type="text", text=message.get("answer"))]
  )

  logging.info("Creating table content for the metadata.")
  table_rows = []

  table_cells = [
    TableCellContent(type="tableHeader", content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text="Input Field")])]),
    TableCellContent(type="tableHeader", content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text="Description")])]),
    TableCellContent(type="tableHeader", content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text="Accepted Values")])])
  ]
  table_rows.append(TableRowContent(type="tableRow", content=table_cells))
  message_metadata = message.get("metadata")
  input_fields = message_metadata.get("input_fields", [])
  logging.info(f"Input fields: {input_fields}")
  for field in input_fields:
    logging.info(f"Processing field: {field}")
    table_cells = [
      TableCellContent(type="tableCell", content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text=field.get("field_name"))])]),
      TableCellContent(type="tableCell", content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text=field.get("field_description"))])]),
      TableCellContent(type="tableCell", content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text=", ".join(field.get("field_values")) if isinstance(field.get("field_values") , list) else field.get("field_values"))])])
    ]
    table_rows.append(TableRowContent(type="tableRow", content=table_cells))

  logging.info("Creating table content.")
  table = TableContent(
    type="table",
    attrs=TableAttrs(isNumberColumnEnabled=True, layout="default"),
    content=table_rows
  )

  logging.info("Creating JiraADFModel.")
  jira_adf_model = JiraADFModel(
    version=1,
    type="doc",
    content=[paragraph, table]
  )
  logging.debug(f"JiraADFModel JSON: {jira_adf_model.model_dump_json(indent=2, exclude_none=True)}")
  return jira_adf_model
