# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

from fastapi import HTTPException
import aiohttp
import jwt
from pyjwt_key_fetcher import AsyncKeyFetcher
from pyjwt_key_fetcher.errors import JWTKeyFetcherError
from cachetools import TTLCache
from asyncache import cached
from multi_agent_jarvis.setup_logging import logging
import os

# Set up JWT
JWKS_PRIVATE_URL = os.getenv("JWKS_PRIVATE_URL", "http://localhost:7007")
JWKS_PUBLIC_URL = os.getenv("JWKS_PUBLIC_URL", "http://localhost:7007")
JWT_ENABLE_GROUPS_VERIFICATION = os.getenv("JWT_ENABLE_GROUPS_VERIFICATION", "false").lower() == "true"
JWT_VERIFICATION_GROUPS = os.getenv("JWT_VERIFICATION_GROUPS", "outshift")

JWT_ALGORITHMS = ["ES256"]
JWT_AUDIENCE = "backstage"
JWKS_URL = f"{JWKS_PRIVATE_URL}/api/auth/.well-known/jwks.json"
JWT_ISSUER = f"{JWKS_PUBLIC_URL}/api/auth"

logging.info(f"JWKS_PRIVATE_URL: {JWKS_PRIVATE_URL}")
logging.info(f"JWKS_PUBLIC_URL: {JWKS_PUBLIC_URL}")
logging.info(f"JWT_ALGORITHMS: {JWT_ALGORITHMS}")
logging.info(f"JWT_AUDIENCE: {JWT_AUDIENCE}")
logging.info(f"JWKS_URL: {JWKS_URL}")
logging.info(f"JWT_ISSUER: {JWT_ISSUER}")

# Cache for JWKS
jwks_cache = TTLCache(maxsize=100, ttl=1800)  # 30 minutes


@cached(jwks_cache)
async def get_jwks(token: str):
  """
  Fetches the JSON Web Key Set (JWKS) and obtains the signing key from a given JWT token.

  This function uses a cached JWKS client to fetch the JWKS from a predefined URL and extract the signing key
  required to verify the JWT token. It handles various exceptions that may occur during the process and logs
  appropriate error messages.

  Args:
    token (str): The JWT token for which the signing key needs to be fetched.

  Returns:
    PyJWKClient.SigningKey: The signing key extracted from the JWKS.

  Raises:
    HTTPException: If there is an error fetching the JWKS or obtaining the signing key.
      - status_code=500: Raised for RequestException, PyJWKClientError, or any unexpected errors.
  """
  try:
    logging.info(f"Fetching JWKS with custom headers from {JWKS_URL}.")
    jwks_client = AsyncKeyFetcher(
      static_issuer_config={
        JWT_ISSUER: {
          "jwks_url": JWKS_URL,
        },
      },
    )
    signing_key = await jwks_client.get_key(token)
    logging.info("Successfully fetched JWKS and obtained signing key.")
    return signing_key
  except aiohttp.ClientResponseError as e:
    logging.error(f"ClientResponseError while fetching JWKS: {e}")
    raise HTTPException(status_code=500, detail="Error fetching JWKS")
  except JWTKeyFetcherError as e:
    logging.error(f"JWTKeyFetcherError while fetching signing key: {e}")
    raise HTTPException(status_code=500, detail="Error fetching signing key")
  except Exception as e:
    logging.error(f"An unexpected error occurred: {e}")
    raise HTTPException(status_code=500, detail="Unexpected error")


async def decode_jwt(token: str):
  """
  Decodes a JWT (JSON Web Token) by verifying its signature.

  Args:
    token (str): The JWT token to decode.

  Returns:
    dict: The decoded payload of the JWT if successful.
        If the token has expired, returns a dictionary with an "error" key and a message indicating the token has expired.
        If the token is invalid, returns a dictionary with an "error" key and a message indicating the token is invalid.
        If any other error occurs, returns a dictionary with an "error" key and a message indicating an error occurred while decoding the token.

  Raises:
    HTTPException: If the token has expired, is invalid, or any other error occurs during decoding.
    jwt.ExpiredSignatureError: If the token has expired.
    jwt.InvalidTokenError: If the token is invalid.
    Exception: If any other error occurs during decoding.

  Note:
    The function assumes the presence of the following:
    - `get_jwks(token)`: A function that retrieves the signing key for the token.
    - `JWT_ALGORITHMS`: A list of algorithms to use for decoding the token.
    - `JWT_AUDIENCE`: The expected audience of the token.
  """
  signing_key = await get_jwks(token)
  try:
    payload = jwt.decode(jwt=token, audience=JWT_AUDIENCE, options={"verify_signature": True}, **signing_key)
    # logging.debug(f"JWT Payload: {payload}")
    return payload
  except jwt.ExpiredSignatureError as e:
    logging.error(f"Token has expired: {e}")
    raise HTTPException(status_code=401, detail="Token has expired")
  except jwt.InvalidTokenError as e:
    logging.error(f"Invalid token: {e}")
    raise HTTPException(status_code=401, detail="Invalid token")
  except Exception as e:
    logging.error(f"An error occurred while decoding the token: {e}")
    raise HTTPException(status_code=401, detail="An error occurred while decoding the token")


async def validate_token(token: str):
  """
  Validates a given JWT token by decoding and verifying the signature.

  This function attempts to decode the provided JWT token.
  If the decoding is successful, it returns the payload of the token. If an error occurs
  during the decoding process, an HTTPException with a 401 status code is raised.

  Args:
    token (str): The JWT token to be validated.

  Returns:
    dict: The decoded payload of the JWT token if validation is successful.

  Raises:
    HTTPException: If an error occurs during token validation, an HTTPException with
             a 401 status code and 'Invalid token' detail is raised.
  """
  logging.debug(f"Validating token: {token}")
  try:
    # Decode the token without verifying the signature
    logging.info("Attempting to decode the token without verification.")
    payload = await decode_jwt(token)
    user_ent = [ent.replace("user:default/", "") for ent in payload.get("ent", []) if ent.startswith("user:")]
    group_ent = [ent.replace("group:default/", "") for ent in payload.get("ent", []) if ent.startswith("group:")]

    logging.info(f"User ent: {user_ent}")
    logging.info(f"Group ent: {group_ent}")
    logging.debug(f"Decoded token: {payload}")

    # Validate groups if JWT_ENABLE_GROUPS_VERIFICATION is enabled
    if JWT_ENABLE_GROUPS_VERIFICATION:
      required_groups = JWT_VERIFICATION_GROUPS.split(",")
      if not any(group in group_ent for group in required_groups):
        logging.error(f"User does not belong to any of the required groups: {required_groups}, hence unauthorized")
        raise HTTPException(
          status_code=401,
          detail=f"User does not belong to any of the required groups: {required_groups}, hence unauthorized",
        )

    logging.info(f"Token validation successful for {user_ent}")
    return user_ent, group_ent
  except Exception as e:
    logging.error(f"An error occurred during token validation: {e}")
    raise HTTPException(status_code=401, detail="Invalid token")
