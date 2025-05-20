# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os

BACKSTAGE_URL = os.getenv("BACKSTAGE_URL", "http://localhost:7007")
class BackstageUserDoesNotBelongToProjectError(Exception):
  """
  Exception raised when the user does not belong to a specific project in Backstage.
  """
  pass