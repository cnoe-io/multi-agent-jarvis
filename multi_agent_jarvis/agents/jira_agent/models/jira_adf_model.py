# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel
from typing import List, Optional, Union
import json

class TextContent(BaseModel):
  # text, hardBreak, mention, emoji, codeBlock, link,
  type: str
  text: Optional[str] = None
  marks: Optional[List[dict]] = None

class ParagraphContent(BaseModel):
  # paragraph
  type: str
  content: List[TextContent]

class TableCellContent(BaseModel):
  # tableHeader, tableCell
  type: str
  attrs: Optional[dict] = None
  content: List[ParagraphContent]

class TableRowContent(BaseModel):
  # tableRow
  type: str
  attrs: Optional[dict] = None
  content: List[TableCellContent]

class TableAttrs(BaseModel):
  # Example:
  # "attrs": {
  # "isNumberColumnEnabled": false,
  # "layout": "default",
  # "localId": "63e16e13-41c0-41e6-bebe-78b0ae7eea38",
  # "width": 760
  # },
  isNumberColumnEnabled: Optional[bool] = None
  layout: Optional[str] = None

class TableContent(BaseModel):
  # table
  type: str
  attrs: Optional[TableAttrs] = None
  content: List[TableRowContent]

class JiraADFModel(BaseModel):
  version: int
  type: str
  content: List[Union[ParagraphContent, TableContent]]

if __name__ == "__main__":
  input_str = """
  {
    "answer": "To create an EC2 instance, I need some additional information from you.",
    "metadata": {
    "user_input": true,
    "input_fields": [
      {
      "field_name": "instance_name",
      "field_description": "The name of the EC2 instance. Must be lowercase and less than 20 characters.",
      "field_values": []
      },
      {
      "field_name": "region",
      "field_description": "The AWS region where the instance will be created.",
      "field_values": [
        "us-east-2",
        "-"
      ]
      },
      {
      "field_name": "instance_size",
      "field_description": "The size of the EC2 instance.",
      "field_values": [
        "t2.micro",
        "t3.micro",
        "t3a.large",
        "m6a.large",
        "t3a.xlarge",
        "m5a.xlarge"
      ]
      },
      {
      "field_name": "os",
      "field_description": "The operating system of the EC2 instance.",
      "field_values": [
        "UBUNTU",
        "AMAZON_LINUX"
      ]
      },
      {
      "field_name": "account_name",
      "field_description": "The AWS account name.",
      "field_values": [
        "outshift-common-dev",
        "-"
      ]
      }
    ]
    }
  }
  """
  data = json.loads(input_str)

  # Create paragraph content for the answer
  paragraph = ParagraphContent(
    type="paragraph",
    content=[TextContent(type="text", text=data["answer"], marks=[])]
  )

  # Create table content for the metadata
  table_rows = []

  table_cells = [
    TableCellContent(type="tableHeader", attrs={}, content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text="Input Field", marks=[])])]),
    TableCellContent(type="tableHeader", attrs={}, content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text="Description", marks=[])])]),
    TableCellContent(type="tableHeader", attrs={}, content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text="Accepted Values", marks=[])])])
  ]
  table_rows.append(TableRowContent(type="tableRow", attrs={}, content=table_cells))
  for field in data["metadata"]["input_fields"]:
    table_cells = [
    TableCellContent(type="tableCell", attrs={}, content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text=field["field_name"], marks=[])])]),
    TableCellContent(type="tableCell", attrs={}, content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text=field["field_description"], marks=[])])]),
    TableCellContent(type="tableCell", attrs={}, content=[ParagraphContent(type="paragraph", content=[TextContent(type="text", text=", ".join(field["field_values"]), marks=[])])])
    ]
    table_rows.append(TableRowContent(type="tableRow", attrs={}, content=table_cells))

  table = TableContent(
    type="table",
    attrs=TableAttrs(isNumberColumnEnabled=True, layout="default"),
    content=table_rows
  )

  # Create JiraADFModel
  jira_adf_model = JiraADFModel(
    version=1,
    type="doc",
    content=[paragraph, table]
  )

  print(jira_adf_model.model_dump_json(indent=2))
