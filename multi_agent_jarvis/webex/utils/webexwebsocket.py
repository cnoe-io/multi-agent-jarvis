# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
import json
import asyncio
import string
import random
from multi_agent_jarvis.setup_logging import logging
import uuid
import websockets
from webexteamssdk import WebexTeamsAPI
import os
import pickle
import tempfile


# If you get an invalid HTTP status code - delete the .device-data (or / and) rename "system-name" below
DEVICES_URL = "https://wdm-a.wbx2.com/wdm/api/v1/devices"
device_file = os.path.join(tempfile.gettempdir(), ".device_data")
if os.path.isfile(device_file):
  with open(device_file, "rb") as f:
    DEVICE_DATA = pickle.load(f)
else:
  DEVICE_DATA = {
    "deviceName": "pywebsocket-client",
    "deviceType": "DESKTOP",
    "localizedModel": "python",
    "model": "python",
    "name": f"cnp-webex-client-{''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))}",
    "systemName": "outshift-support-chatbot",
    "systemVersion": "0.1",
  }
  with open(device_file, "wb") as f:
    pickle.dump(DEVICE_DATA, f)


class WebexMessage(object):
  def __init__(self, access_token, on_message=None, on_card=None):
    self.access_token = access_token
    self.webex = WebexTeamsAPI(access_token=access_token)
    self.device_info = None
    self.on_message = on_message
    self.on_card = on_card
    self.share_id = None

  def _process_message(self, msg):
    logging.debug(f"------------------ EVENT: {msg['data']['eventType']}")
    if msg["data"]["eventType"] == "conversation.activity":
      activity = msg["data"]["activity"]
      if activity["verb"] in ["post", "update"]:
        space_id = self._get_base64_message_id(activity)
        webex_msg_object = self.webex.messages.get(space_id)
        # ___Skip messages from the bot itself
        if webex_msg_object.personEmail in self.my_emails:
          logging.debug(">>> message is from myself, ignoring")
          return
        # ___Process message
        if self.on_message:
          self.on_message(webex_msg_object)
      elif activity["verb"] == "share":
        logging.debug(f"activity={activity}")
        self.share_id = activity["id"]
      elif activity["verb"] == "cardAction":
        space_id = self._get_base64_message_id(activity)
        action = self.webex.attachment_actions.get(space_id)
        # ___Process card
        if self.on_card:
          self.on_card(action)

  def _get_base64_message_id(self, activity):
    """
    In order to geo-locate the correct DC to fetch the message from, you need to use the base64 Id of the
    message.
    @param activity: incoming websocket data
    @return: base 64 message id
    """
    activity_id = activity["id"]
    logging.debug(f"activity verb={activity['verb']}. message id={activity_id}")
    conversation_url = activity["target"]["url"]
    conv_target_id = activity["target"]["id"]
    verb = "messages" if activity["verb"] in ["post", "update"] else "attachment/actions"
    if activity["verb"] == "update" and self.share_id is not None:
      activity_id = self.share_id
      self.share_id = None
    logging.debug(f"activity_id={activity_id}")
    conversation_message_url = conversation_url.replace(f"conversations/{conv_target_id}", f"{verb}/{activity_id}")
    conversation_message = self.webex._session.get(conversation_message_url)
    logging.debug(f"conversation_message={conversation_message}")
    return conversation_message["id"]

  def _get_device_info(self):
    logging.debug(">>> getting device list")
    try:
      resp = self.webex._session.get(DEVICES_URL)
      for device in resp["devices"]:
        if device["name"] == DEVICE_DATA["name"]:
          self.device_info = device
          return device
    except Exception:
      pass

    logging.info(">>> device does not exist, creating")

    resp = self.webex._session.post(DEVICES_URL, json=DEVICE_DATA)
    if resp is None:
      logging.error(">>> **ERROR** could not create device")

    self.device_info = resp
    return resp

  def run(self):
    if self.device_info is None:
      if self._get_device_info() is None:
        logging.error(">>> could not get/create device info")
        return

    self.my_emails = self.webex.people.me().emails

    async def _connect_and_listen():
      logging.debug(">>> Opening websocket connection to %s" % self.device_info["webSocketUrl"])
      logging.info(f"WEBSOCKET URL: {self.device_info['webSocketUrl']}\n")

      try:
        async with websockets.connect(self.device_info["webSocketUrl"]) as ws:
          logging.info(">>> WebSocket Opened\n")
          msg = {
            "id": str(uuid.uuid4()),
            "type": "authorization",
            "data": {"token": "Bearer " + self.access_token},
          }
          await ws.send(json.dumps(msg))

          while True:
            message = await ws.recv()
            logging.debug(">>> WebSocket Received Message(raw): %s\n" % message)
            try:
              msg = json.loads(message)
              loop = asyncio.get_event_loop()
              loop.run_in_executor(None, self._process_message, msg)
            except Exception:
              logging.warning(">>> **ERROR** An exception occurred while processing message. Ignoring. ")

      except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError):
        logging.warning(">>> WebSocket connection closed or timeout occurred, attempting to reconnect...")
        await asyncio.sleep(5)  # Wait before reconnecting

    async def _run_forever():
      while True:
        await _connect_and_listen()

    asyncio.get_event_loop().run_until_complete(_run_forever())
