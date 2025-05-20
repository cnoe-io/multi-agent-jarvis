# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from webexteamssdk import WebexTeamsAPI


class WebexInstanceManager:
  """Singleton class to manage the Webex instance."""

  _instance = None

  @classmethod
  def get_instance(cls, access_token):
    if cls._instance is None:
      cls._instance = WebexTeamsAPI(access_token=access_token)

    return cls._instance
