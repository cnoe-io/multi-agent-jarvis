import os
import random
import httpx
from httpx_sse import connect_sse
import string
import sys

import requests

email = os.getenv("LOCAL_USER_EMAIL", "noone@cisco.com")


def send_post_request(url, chat_id, question):
  try:
    response = requests.post(
      url,
      json={"chat_id": chat_id, "question": question},
      headers={"Content-Type": "application/json", "USER_EMAIL": email},
    )
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()
  except requests.exceptions.RequestException as e:
    return {"error": str(e)}


def get_response(chat_id):
  response = requests.get(f"http://127.0.0.1:8000/get_answer/{chat_id}", headers={"USER_EMAIL": email})
  return response.json()


def print_response_stream(chat_id):
  with httpx.Client() as client:
    with connect_sse(
      client, "GET", f"http://127.0.0.1:8000/get_answer_stream/{chat_id}", headers={"USER_EMAIL": email}, timeout=60.0
    ) as event_source:
      for sse in event_source.iter_sse():
        print(sse)


def run():
  print("Ask a question to the agent, type 'exit' to quit")
  if os.getenv("LOCAL_CHAT_ID"):
    chat_id = os.getenv("LOCAL_CHAT_ID")
  else:
    chat_id = "local_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=15))
  print(f"Chat ID: {chat_id}")
  while True:
    question = input("> ")
    if question == "exit":
      sys.exit(0)
    response = send_post_request("http://127.0.0.1:8000/submit_question", chat_id, question)
    print(response)
    print("Fetching answer...")
    print_response_stream(chat_id)
    response = get_response(chat_id)
    print(response)
    if "answer" in response and response["answer"]:
      print(f"---\n>> {response['answer']}\n---")


if __name__ == "__main__":
  try:
    run()
  except KeyboardInterrupt:
    print("Goodbye!")
    sys.exit(0)
