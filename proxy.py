import os
import httpx
from typing import Tuple, Dict, Any
from dotenv import load_dotenv
import logging

logger = logging.getLogger("gateway")
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1/messages"

client = httpx.AsyncClient(timeout=60.0)

async def forward_request(body: Dict[str, Any], path: str) -> Tuple[Dict[str, Any], int]:
    """
    Takes the JSON payload from the incoming request,
    Sends it to Anthropic.
    """
    if not ANTHROPIC_API_KEY:
        return {"error": {"message": "ANTHROPIC_API_KEY environment variable not set"}}, 500

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # We pass the headers through that might be required by anthropic
    # but override the crucial auth headers.

    url = f"https://api.anthropic.com{path}"

    try:
        response = await client.post(
            url,
            json=body,
            headers=headers
        )
        return response.json(), response.status_code
    except httpx.RequestError as e:
        return {"error": {"message": f"Failed to forward request to Anthropic: {str(e)}"}}, 502
