# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

MOCK_GET_CI_LOGS_RESPONSE = [
  "Log message 1",
  "Log message 2",
  "Log message 3",
]

MOCK_GET_WORKFLOW_RUN_STATUS_RESPONSE = (
  "completed", # status
  "succeeded", # conclusion
)

MOCK_TRIGGER_GITHUB_WORKFLOW_RESPONSE = (
  "url", # url
  "logs", # logs
)