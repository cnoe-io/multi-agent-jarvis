# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class User(BaseModel):
  accountId: str
  displayName: str
  active: bool
  self: HttpUrl
  timeZone: str
  accountType: str

class Reporter(User):
  pass

class Creator(User):
  pass

class Assignee(User):
  pass

class Author(User):
  pass

class Project(BaseModel):
  key: str

class Priority(BaseModel):
  name: str

class Status(BaseModel):
  name: str

class Comment(BaseModel):
  self: HttpUrl
  id: str
  author: Author
  body: str
  updateAuthor: Author
  created: str
  updated: str
  jsdPublic: bool

class Fields(BaseModel):
  labels: Optional[List[str]] = []
  issuelinks: Optional[List[str]] = []
  assignee: Optional[Assignee]
  components: Optional[List[str]] = []
  subtasks: Optional[List[str]] = []
  reporter: Optional[Reporter] = None
  project: Project
  summary: Optional[str]
  description: Optional[str] = None
  priority: Optional[Priority]
  status: Optional[Status]
  creator: Optional[Creator] = None

class Issue(BaseModel):
  id: str
  self: HttpUrl
  key: str
  fields: Fields

class JiraPayload(BaseModel):
  timestamp: int
  webhookEvent: Optional[str]
  issue_event_type_name: Optional[str] = None
  user: Optional[User] = None
  issue: Optional[Issue] = None
  comment: Optional[Comment] = None

  def get_timestamp(self):
    return self.timestamp

  def get_issue_key(self):
    return self.issue.key

  def get_issue_summary(self):
    return self.issue.fields.summary if hasattr(self.issue.fields, 'summary') else None

  def get_issue_description(self):
    return self.issue.fields.description if hasattr(self.issue.fields, 'description') else None

  def get_webhook_event(self):
    return self.webhookEvent

  def get_issue_event_type_name(self):
    return self.issue_event_type_name

  def get_comment_author(self):
    if self.comment:
        return self.comment.author.displayName
    return None

  def get_comment_body(self):
    if self.comment:
        return self.comment.body
    return None

  def get_assigned_user_displayname(self):
    if self.issue.fields.assignee:
        return self.issue.fields.assignee.displayName
    return None

  def get_labels(self):
    return self.issue.fields.labels
