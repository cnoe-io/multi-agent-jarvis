# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import logging
import coloredlogs
import os

if os.getenv("HTTP_CLIENT_DEBUG", "0") == "1":
  import http.client as http_client

  http_client.HTTPConnection.debuglevel = 1

log_formatted_str = "%(asctime)s [%(name)s] [%(levelname)s] [%(funcName)s] %(message)s"
# You must initialize logging, otherwise you'll not see debug output.
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
  format=log_formatted_str,
  level=getattr(logging, log_level, logging.INFO),
)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(getattr(logging, log_level, logging.INFO))
requests_log.propagate = True

coloredlogs.install(level=log_level, fmt=log_formatted_str)
