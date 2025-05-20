# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from fastapi import BackgroundTasks, FastAPI, Depends, HTTPException, Request
import traceback
from sse_starlette import EventSourceResponse
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from multi_agent_jarvis.webex.webex import jarvis_webex
from urllib.parse import urlparse
import asyncio
from asyncio.subprocess import PIPE
from concurrent.futures import ThreadPoolExecutor
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import MemorySaver
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.memory import InMemoryStore
from jarvis_agent.aigateway_agent.models import BootstrapRequest
from jarvis_agent.aigateway_agent.api import bootstrap_project
from multi_agent_jarvis.globals import PROJECT_NAME_TO_UUID
import uuid
import time
import json
from jarvis_agent.jarvis_agent import JarvisAgent
from multi_agent_jarvis.async_http_utils import AsyncHttpSession
from prometheus_client import start_http_server, Summary, Counter, Gauge
from jarvis_agent.verify_jwt import validate_token
import os
from multi_agent_jarvis.models import ChatBotQuestion, Feedback
from multi_agent_jarvis.webex.webex_util import send_feedback_to_webex
from jarvis_agent.aigateway_agent.api import list_supported_llm_providers_and_models
from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.globals import PROVIDER_MODELS_MAP
from kubernetes import client, config
import hmac
import hashlib
from multi_agent_jarvis.agents.jira_agent.models.jira_issue_model import JiraPayload
from jarvis_agent.jarvis_utils import print_banner

from multi_agent_jarvis.agents.jira_agent import (
  process_jira_webhook,
  _add_jira_comment,
  jira_comment_body_adf,
  _get_jira_reporter_email,
)

jarvis_agent = None


def generate_uuid():
  return str(uuid.uuid4())


DB_URI = os.getenv("DB_URI")
LANGGRAPH_CHECKPOINT_MEMORY_SAVER = os.getenv("LANGGRAPH_CHECKPOINT_MEMORY_SAVER", "memory")


async def update_kubeconfig():
  # Retrieve cluster name and region from environment variables
  cluster_name = os.getenv("TARGET_CLUSTER_NAME")
  cluster_region = os.getenv("TARGET_CLUSTER_REGION")

  if not cluster_name or not cluster_region:
    raise ValueError("TARGET_CLUSTER_NAME and TARGET_CLUSTER_REGION environment variables must be set.")

  # Construct the AWS CLI command
  command = [
    "aws",
    "eks",
    "update-kubeconfig",
    "--name",
    cluster_name,
    "--region",
    cluster_region,
    "--alias",
    cluster_name,
  ]

  # Run the command asynchronously
  process = await asyncio.create_subprocess_exec(*command, stdout=PIPE, stderr=PIPE)

  # Capture the output
  stdout, stderr = await process.communicate()

  if process.returncode == 0:
    logging.info(f"Kubeconfig updated successfully: {stdout.decode().strip()}")
  else:
    err = stderr.decode().strip()
    logging.error(err)
    raise ValueError(f"Failed to update kubeconfig: {err}")


@asynccontextmanager
async def lifespan(app: FastAPI):
  if os.getenv("JARVIS_DRYRUN", "false").lower() == "true":
    print_banner("JARVIS DRY RUN MODE ENABLED", "Tools will not be executed. This is a dry run.")

  if os.getenv("ENABLE_KNOWLEDGE_GRAPH", "false").lower() != "true":
    print_banner("KNOWLEDGE GRAPH DISABLED", "Knowledge graph features will not be available.")
  # Create global async HTTP session
  await AsyncHttpSession.get_instance()
  await update_kubeconfig()
  config.load_kube_config()
  # Prepare a list of tasks for bootstrapping projects
  tasks = []

  for project_name, project_id in PROJECT_NAME_TO_UUID.items():
    # hack to avoid bootstrapping the "other" project which is the default one
    if project_name != "other":
      if str(uuid.UUID(project_id, version=4)) != project_id:
        logging.error(f"project ID {project_id} is not a valid UUID4, it might encounter onboarding issues")
      bootstrap_request = BootstrapRequest(
        org_id="c646e079-6c27-4dcb-9c6b-5b8b12d8c0d1",  # Static root org ID for all projects
        project_id=project_id,
        project_name=project_name,
        project_owner="sraradhy@cisco.com",
        update_existing_models=True,
      )
      tasks.append(bootstrap_project(bootstrap_request))

  # Execute all tasks concurrently
  results = await asyncio.gather(*tasks, return_exceptions=True)

  # Handle exceptions and log errors
  for i, result in enumerate(results):
    if isinstance(result, Exception):
      project_name = list(PROJECT_NAME_TO_UUID.keys())[i]
      project_id = list(PROJECT_NAME_TO_UUID.values())[i]
      logging.error(f"Failed to bootstrap project: {project_name} with ID: {project_id}. Error: {str(result)}")

  try:
    # cache the supported LLM providers and models
    await list_supported_llm_providers_and_models()
  except Exception as e:
    logging.error(f"Failed to list supported llm providers and models: {e}")

  #######################################
  ######### Add Memory Checkpoint #######
  #######################################

  global jarvis_agent
  logging.info("Using InMemoryStore.")
  store = InMemoryStore()
  checkpointer = None
  if LANGGRAPH_CHECKPOINT_MEMORY_SAVER == "memory":
    logging.info("Using MemorySaver for checkpointing.")
    checkpointer = MemorySaver()
    jarvis_agent = JarvisAgent(checkpointer, store)
    # Not resource intensive, just need to get around GIL
    p = ProcessPoolExecutor(max_workers=1)
    p.submit(jarvis_webex)
    yield
  elif LANGGRAPH_CHECKPOINT_MEMORY_SAVER == "postgres":
    logging.info("Using PostgresSaver for checkpointing.")

    connection_kwargs = {
      "autocommit": True,
      "prepare_threshold": 0,
    }

    p = urlparse(DB_URI)

    conninfo = {
      "dbname": p.path[1:],
      "user": p.username,
      "password": p.password,
      "port": p.port,
      "host": p.hostname,
    }

    conninfo = "\n".join([f"{k}={v}" for k, v in conninfo.items()])

    async with AsyncConnectionPool(
      conninfo=conninfo,
      max_size=5,
      kwargs=connection_kwargs,
    ) as pool:
      checkpointer = AsyncPostgresSaver(pool)

      await checkpointer.setup()
      jarvis_agent = JarvisAgent(checkpointer, store)
      # Not resource intensive, just need to get around GIL
      p = ProcessPoolExecutor(max_workers=1)
      p.submit(jarvis_webex)

      # Yield inside context so that the DB connections stay active
      yield
  # Any cleanup tasks can be added here if needed
  await AsyncHttpSession.close()
  p.shutdown(wait=False, cancel_futures=True)


async def task_submit_question(question: ChatBotQuestion, user_email: str):
  try:
    question.question += f" (asked by user_email: {user_email})"
    logging.info(f"Received question: {question.question}")
    async for message in jarvis_agent.interact(
      human_message=question.question, thread_id=question.chat_id, user_email=user_email, user_files=question.user_files
    ):
      await message_queues[question.chat_id].put(message)
      full_responses[question.chat_id].append(message)
    task_status[question.chat_id] = "completed"
  except Exception as e:
    logging.error(f"Error in task_submit_question method: {traceback.format_exc()}")
    logging.error(f"{type(e).__name__}: {e}")
    await message_queues[question.chat_id].put(
      {"answer": "Jarvis Agent is not available right now. Please try again later!"}
    )


app = FastAPI(lifespan=lifespan)
# Prometheus metrics
REQUEST_TIME = Summary("request_processing_seconds", "Time spent processing request")
REQUEST_COUNT = Counter("request_count", "Total number of requests")
STARTUP_TIME = Gauge("startup_time", "Time when the application started")

# Record the startup time
STARTUP_TIME.set_to_current_time()

# Start Prometheus metrics server
if os.getenv("START_METRICS_SERVER", "false").lower() == "true":
  start_http_server(8001)

submit_feedback_executor = ThreadPoolExecutor(max_workers=10)
task_status = {}
message_queues = {}
full_responses = {}

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

JARVIS_UNAVAILABLE_MESSAGE = {
  "answer": "Jarvis Agent is not available right now. Please try again later!",
  "metadata": None,
}

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


async def _extract_token(request: Request) -> str:
  logging.info(f"Request URL: {request.url}")
  logging.debug(f"Request headers: {request.headers}")
  auth_header = request.headers.get("Authorization")
  # Don't check auth for requests coming from 127.0.0.1 as this is the Webex Bot process
  if request.client.host == "127.0.0.1" and "USER_EMAIL" in request.headers:
    return request.headers["USER_EMAIL"]
  if not auth_header or not auth_header.startswith("Bearer "):
    raise HTTPException(status_code=401, detail="Token missing or invalid")
  token = auth_header[len("Bearer ") :]
  logging.debug(f"Extracted token: {token}")

  # Verify the JWT token
  user_ent, _ = await validate_token(token)
  user_email = f"{user_ent[0]}@cisco.com"
  return user_email


@app.get("/get_answer/{chat_id}")
async def get_answer(chat_id: str, user_email: str = Depends(_extract_token)):
  REQUEST_COUNT.inc()
  request_start_time = time.time()
  try:
    timeout = 600
    task_start_time = time.time()
    while time.time() - task_start_time < timeout:
      status = task_status.get(chat_id)
      if status == "completed":
        break
      await asyncio.sleep(0.5)
    else:
      return JARVIS_UNAVAILABLE_MESSAGE
    # Strip the end of stream message and use the last message's metadata
    answer_message_dict = {
      "answer": "\n".join([m["answer"] for m in full_responses[chat_id][:-1]]),
      "metadata": full_responses[chat_id][:-1][-1]["metadata"],
    }
    logging.info(f"Retrieved answer message: {json.dumps(answer_message_dict, indent=2)}")
    full_responses.pop(chat_id)
    return answer_message_dict
  except Exception as e:
    logging.error(f"Error in get_answer method: {traceback.format_exc()}")
    logging.error(f"{type(e).__name__}: {e}")
    return JARVIS_UNAVAILABLE_MESSAGE
  finally:
    REQUEST_TIME.observe(time.time() - request_start_time)


@app.get("/get_answer_stream/{chat_id}")
async def get_answer_stream(chat_id: str, user_email: str = Depends(_extract_token)):
  async def message_stream():
    REQUEST_COUNT.inc()
    request_start_time = time.time()
    try:
      timeout = 600
      task_start_time = time.time()
      while time.time() - task_start_time < timeout:
        # Get message from the queue
        queue = message_queues.get(chat_id)
        if queue is None:
          # Missing chat_id
          break
        answer_message_dict = await queue.get()
        if answer_message_dict:
          logging.info(f"Retrieved answer message: {answer_message_dict}")
          yield {"event": "data", "data": json.dumps(answer_message_dict)}
        else:
          logging.info("End of stream")
          yield {"event": "end"}
          break
      else:
        logging.warning("Timed out")
        yield {"event": "error", "data": json.dumps(JARVIS_UNAVAILABLE_MESSAGE)}
    except Exception as e:
      logging.error(f"Error in get_answer_stream method: {traceback.format_exc()}")
      logging.error(f"{type(e).__name__}: {e}")
      yield {"event": "error", "data": json.dumps(JARVIS_UNAVAILABLE_MESSAGE)}
    finally:
      REQUEST_TIME.observe(time.time() - request_start_time)

  return EventSourceResponse(message_stream())


@app.post("/submit_question")
async def submit_question(
  request: Request,
  question: ChatBotQuestion,
  background_tasks: BackgroundTasks,
  user_email: str = Depends(_extract_token),
):
  REQUEST_COUNT.inc()
  start_time = time.time()
  try:
    task_status[question.chat_id] = "in progress"
    message_queues[question.chat_id] = asyncio.Queue()
    full_responses[question.chat_id] = []
    background_tasks.add_task(task_submit_question, question, user_email)
    return {"chat_id": question.chat_id, "suggestions": ""}
  except Exception as e:
    logging.error(f"Error in submit_question method: {traceback.format_exc()}")
    logging.error(f"{type(e).__name__}: {e}")
    return {
      "chat_id": question.chat_id,
      "suggestions": "Jarvis Agent is a friendly AI that can help you with your questions!",
    }
  finally:
    REQUEST_TIME.observe(time.time() - start_time)


@app.post("/submit_feedback")
async def submit_feedback(
  feedback: Feedback,
  background_tasks: BackgroundTasks,
  user_email: str = Depends(_extract_token),
):
  REQUEST_COUNT.inc()
  start_time = time.time()
  logging.info(f"Received feedback from user: {user_email}")
  logging.debug(f"Feedback details: {feedback}")
  try:
    background_tasks.add_task(
      submit_feedback_executor.submit,
      send_feedback_to_webex,
      feedback,
      user_email,
    )
    logging.info("Processing feedback submission")
    response = {
      "status": "success",
      "message": "Feedback submitted successfully",
      "feedback": feedback.model_dump(),
    }
    logging.info("Feedback submission successful")
    return response
  except Exception as e:
    logging.error(f"Error submitting feedback: {str(e)}")
    return {"status": "error", "message": "Failed to submit feedback"}
  finally:
    REQUEST_TIME.observe(time.time() - start_time)
    logging.info("Feedback submission request processing time recorded")


@app.get("/llm-providers")
async def get_llm_providers_and_models():
  REQUEST_COUNT.inc()
  start_time = time.time()
  logging.info("Received request to get LLM providers and models")
  try:
    # TODO: Ensure the Ostinato Control Plane json config is up-to-date with the latest supported providers and models
    # providers_and_models = await list_supported_llm_providers_and_models()
    providers_and_models = PROVIDER_MODELS_MAP
    logging.info("Successfully retrieved LLM providers and models")
    return {"status": "success", "data": providers_and_models}
  except Exception as e:
    logging.error(f"Error retrieving LLM providers and models: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to retrieve LLM providers and models")
  finally:
    REQUEST_TIME.observe(time.time() - start_time)
    logging.info("LLM providers and models request processing time recorded")


@app.get("/projects")
async def get_projects():
  REQUEST_COUNT.inc()
  start_time = time.time()
  logging.info("Received request to get project names and UUIDs")
  try:
    projects = [{"name": name, "id": uuid} for name, uuid in PROJECT_NAME_TO_UUID.items()]
    logging.info("Successfully retrieved project names and UUIDs")
    return {"status": "success", "data": projects}
  except Exception as e:
    logging.error(f"Error retrieving project names and UUIDs: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to retrieve project names and UUIDs")
  finally:
    REQUEST_TIME.observe(time.time() - start_time)
    logging.info("Project names and UUIDs request processing time recorded")


@app.get("/sandbox/configmap")
async def sandbox_configmap_get(
  name: str = None,
  user_email: str = Depends(_extract_token),
):
  user_sandbox = "sandbox-" + user_email.split("@")[0]
  if user_sandbox == "sandbox-":
    raise HTTPException(status_code=400, detail="Invalid user email")
  # proc = await asyncio.create_subprocess_exec("kubectl", "get", "cm", "--namespace", user_sandbox, stdout=PIPE, stderr=PIPE)
  # out, err = await proc.communicate()
  # if proc.returncode != 0:
  #   raise HTTPException(status_code=400, detail="Error listing configmaps")
  v1 = client.CoreV1Api()
  if name is None or name == "":
    try:
      configmap_list = v1.list_namespaced_config_map(namespace=user_sandbox)
      return configmap_list.to_dict()
    except client.rest.ApiException as e:
      logging.error(f"Error listing configmaps: {str(e)}")
      raise HTTPException(status_code=400, detail="Error listing configmaps")
  try:
    configmap = v1.read_namespaced_config_map(name=name, namespace=user_sandbox)
    return configmap.to_dict()
  except client.rest.ApiException as e:
    logging.error(f"Error listing configmaps: {str(e)}")
    raise HTTPException(status_code=400, detail="Error listing configmaps")


@app.get("/sandbox/secret")
async def sandbox_secret_get(
  name: str = None,
  user_email: str = Depends(_extract_token),
):
  user_sandbox = "sandbox-" + user_email.split("@")[0]
  if user_sandbox == "sandbox-":
    raise HTTPException(status_code=400, detail="Invalid user email")
  v1 = client.CoreV1Api()
  if name is None or name == "":
    try:
      secret_list = v1.list_namespaced_secret(namespace=user_sandbox)
      return secret_list.to_dict()
    except client.rest.ApiException as e:
      logging.error(f"Error listing secrets: {str(e)}")
      raise HTTPException(status_code=400, detail="Error listing secrets")
  try:
    secret = v1.read_namespaced_secret(name=name, namespace=user_sandbox)
    return secret.to_dict()
  except client.rest.ApiException as e:
    logging.error(f"Error reading secret: {str(e)}")
    raise HTTPException(status_code=400, detail="Error reading secret")


@app.post("/sandbox/configmap")
async def sandbox_configmap_post(
  configmap: dict,
  user_email: str = Depends(_extract_token),
):
  user_sandbox = "sandbox-" + user_email.split("@")[0]
  if user_sandbox == "sandbox-":
    raise HTTPException(status_code=400, detail="Invalid user email")
  v1 = client.CoreV1Api()
  name = configmap["metadata"]["name"]
  v1.replace_namespaced_config_map(name=name, namespace=user_sandbox, body=configmap)


@app.post("/sandbox/secret")
async def sandbox_secret_post(
  secret: dict,
  user_email: str = Depends(_extract_token),
):
  user_sandbox = "sandbox-" + user_email.split("@")[0]
  if user_sandbox == "sandbox-":
    raise HTTPException(status_code=400, detail="Invalid user email")
  v1 = client.CoreV1Api()
  name = secret["metadata"]["name"]
  v1.replace_namespaced_secret(name=name, namespace=user_sandbox, body=secret)


@app.post("/jira/webhook")
async def webhook(request: Request):
  """
  Handle incoming webhook requests, verify their authenticity, and process the payload.

  This function performs the following steps:
  1. Logs the received request URL and headers.
  2. Verifies the presence of the `JIRA_WEBHOOK_SECRET` environment variable.
  3. Checks for the `x-hub-signature` header in the request.
  4. Computes the HMAC SHA256 signature of the request body using the `JIRA_WEBHOOK_SECRET`.
  5. Compares the computed signature with the `x-hub-signature` header to verify authenticity.
  6. If the signatures match, processes the webhook payload:
     - Parses the JSON payload.
     - Extracts the issue key and LLM question from the payload.
     - Comments on the Jira ticket indicating that processing has started.
     - Interacts with the Jarvis Agent to get responses based on the LLM question.
     - Comments on the Jira ticket with the responses from the Jarvis Agent.
  7. If the signatures do not match, logs an error and raises an HTTP 400 exception.

  Args:
    request (Request): The incoming HTTP request object.

  Returns:
    dict: A dictionary with a status key indicating the result of the processing.

  Raises:
    HTTPException: If the `JIRA_WEBHOOK_SECRET` environment variable is not set.
    HTTPException: If the `x-hub-signature` header is missing.
    HTTPException: If the `x-hub-signature` is invalid.
    HTTPException: If the payload is invalid.
  """
  logging.debug(f"Received webhook request: {request.url}")
  headers = dict(request.headers)
  # logging.debug(f"Webhook request headers: {json.dumps(headers, indent=2)}")

  # Verify the x-hub-signature header
  jira_webhook_secret = os.getenv("JIRA_WEBHOOK_SECRET")
  if not jira_webhook_secret:
    raise HTTPException(status_code=500, detail="JIRA_WEBHOOK_SECRET environment variable is not set")

  x_hub_signature = headers.get("x-hub-signature")
  if not x_hub_signature:
    logging.error("x-hub-signature header is missing")
    raise HTTPException(status_code=400, detail="x-hub-signature header is missing")

  # Compute the HMAC SHA256 signature
  logging.debug(f"x-hub-signature: {x_hub_signature}")
  body = await request.body()
  computed_signature = (
    "sha256=" + hmac.new(key=jira_webhook_secret.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
  )

  logging.debug(f"Computed signature: {computed_signature}")

  if hmac.compare_digest(computed_signature, x_hub_signature):
    try:
      payload = await request.json()
      # logging.debug(f"Webhook payload: {json.dumps(payload, indent=2)}")
      issue_key, llm_question, issue_event_type_name = await process_jira_webhook(JiraPayload(**payload))
      logging.info(f"Issue Key: {issue_key}")
      logging.info(f"LLM Question: {llm_question}")
      logging.info(f"Issue Event Type name: {issue_event_type_name}")

      if issue_key and llm_question and issue_event_type_name:
        logging.info(f"Issue Key: {issue_key}, LLM Question: {llm_question}")
        # Create a unique thread ID for jira webhook event.
        # Timestamp is used to ensure uniqueness in case of multiple events for the same issue key.
        thread_id = issue_key

        reporter_email = await _get_jira_reporter_email(issue_key)

        if issue_event_type_name == "issue_assigned":
          prompts = [
            f"Add comment to Jira {issue_key} asked by user_email: {reporter_email}: ⏳ Jarvis AI Agent is processing...",
            f"Add label to Jira {issue_key} asked by user_email: {reporter_email}: JARVIS_AGENT_AT_WORK",
            f"Transition Jira {issue_key} asked by user_email: {reporter_email}: If Jira project key is OPENSD transition to Acknowledge otherwise transition to In-Progress",
          ]

          for prompt in prompts:
            try:
              async for message in jarvis_agent.interact(
                human_message=prompt, thread_id=thread_id, user_email=reporter_email
              ):
                logging.info(f"LLM response: {message}")
            except Exception as e:
              logging.error(f"Error processing webhook prompts: {str(e)}")
              pass

        llm_question = f"{llm_question} (asked by user_email: {reporter_email} on Jira Issue ID: {issue_key})"
        logging.info(f"LLM Question: {llm_question}")

        async for message in jarvis_agent.interact(
          human_message=llm_question, thread_id=thread_id, user_email=reporter_email
        ):
          logging.info(f"LLM response: {message}")
          if message:
            message_answer = message.get("answer")
            message_metadata = message.get("metadata")
            markdown_string = f"{message_answer}\n" if message_answer else ""
            jira_comment = (
              await jira_comment_body_adf(message)
              if message_metadata and message_metadata.get("user_input", True)
              else markdown_string
            )
            if jira_comment and jira_comment != llm_question:
              await _add_jira_comment(issue_key, jira_comment)
      else:
        logging.info("[Jira Webhook] Skipping further processing of webhook payload")
    except Exception as e:
      logging.error(f"Error parsing webhook payload: {str(e)}")
      raise HTTPException(status_code=400, detail="Invalid payload")
    return {"status": "ok"}
  else:
    logging.error("Invalid x-hub-signature")
    raise HTTPException(status_code=400, detail="Invalid x-hub-signature")


@app.get("/healthz")
async def healthz():
  return {"status": "ok"}
