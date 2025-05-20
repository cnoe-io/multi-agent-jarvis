# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import os
from langchain_openai import AzureChatOpenAI
from multi_agent_jarvis.setup_logging import logging
from multi_agent_jarvis.models import JarvisResponse


class JarvisLLMFactory:
  """
  A factory class to create instances of language models based on the specified model name.

  Attributes:
    model_name (str): The name of the model to be used.

  Methods:
    get_llm_connection(response_format=None):
      Creates and returns an instance of a language model based on the model_name attribute.
      Supported models:
        - "gpt-4o"
        - "gpt-4o-mini"
        - "gpt-o1"
        - "gpt-o1-mini"
      Args:
        response_format (str, optional): The format of the response expected from the language model.
      Raises:
        ValueError: If the model_name is not supported.
  """

  def __init__(self, model_name: str):
    self.model_name = model_name

  def get_llm_connection(self, response_format=None):
    if self.model_name not in ["gpt-4o", "gpt-4o-mini", "gpt-o1", "gpt-o1-mini"]:
      raise ValueError(f"Unsupported model name: {self.model_name}")

    deployment = os.getenv(f"AZURE_OPENAI_DEPLOYMENT_{self.model_name.replace('-', '_').upper()}")
    api_version = os.getenv(f"AZURE_OPENAI_API_VERSION_{self.model_name.replace('-', '_').upper()}")
    logging.info(f"Using model: {self.model_name}, deployment: {deployment}, api_version: {api_version}")

    temperature = 0 if self.model_name in ["gpt-4o", "gpt-4o-mini"] else 1

    return AzureChatOpenAI(
      azure_deployment=deployment,
      api_version=api_version,
      temperature=temperature,
      max_tokens=None,
      timeout=None,
      max_retries=5,
      model_kwargs=({"response_format": response_format} if response_format else dict()),
    )


async def get_llm_connection_with_tools(tools, response_format=JarvisResponse):
  model_name = os.getenv("JARVIS_LLM_MODEL_NAME", "gpt-4o-mini")
  llm_factory = JarvisLLMFactory(model_name)
  return llm_factory.get_llm_connection(response_format=response_format).bind_tools(tools, strict=True)
