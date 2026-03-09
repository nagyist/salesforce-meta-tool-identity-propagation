"""Chat App backend — bridges browser MSAL auth to Foundry agent via Responses API.

Endpoints:
  GET  /health           — Health check
  GET  /api/config       — MSAL config (from env vars, no hardcoded values)
  POST /api/chat         — Send message to agent (OBO flow)
  POST /api/chat/approve — Approve MCP tool calls
  GET  /                 — Static SPA (index.html)
"""

import asyncio
import logging
import os
import sys
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.foundry_helpers import call_agent, approve_tools  # noqa: E402

# --- Azure Monitor OpenTelemetry ---
_conn_str = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
if _conn_str:
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(connection_string=_conn_str)
    # OTel adds handler at WARNING level; lower to INFO for app logs.
    # Add StreamHandler so logs also appear in container logs.
    _root = logging.getLogger()
    _root.setLevel(logging.INFO)
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    _root.addHandler(_h)
    # Suppress verbose Azure SDK HTTP logging
    logging.getLogger("azure").setLevel(logging.WARNING)
    print("Azure Monitor OpenTelemetry configured for chat-app")
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="Chat App", docs_url=None, redoc_url=None)

# Explicit instrumentation — auto-discovery may fail with vendored deps (pip --target)
if _conn_str:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/config")
async def config():
    """Return MSAL config from environment variables."""
    client_id = os.environ.get("CHAT_APP_ENTRA_CLIENT_ID", "")
    tenant_id = os.environ.get("TENANT_ID", "")

    if not client_id or not tenant_id:
        raise HTTPException(
            status_code=500,
            detail="CHAT_APP_ENTRA_CLIENT_ID or TENANT_ID not configured",
        )

    return {
        "clientId": client_id,
        "authority": f"https://login.microsoftonline.com/{tenant_id}",
        "scopes": ["https://ai.azure.com/.default"],
        "appInsightsConnectionString": os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", ""),
    }


@app.post("/api/chat")
async def chat(request: Request):
    """Send a message to the Foundry agent via the Responses API."""
    body = await request.json()
    access_token = body.get("access_token")
    message = body.get("message", "")
    previous_response_id = body.get("previous_response_id")
    session_id = body.get("session_id", "unknown")

    if not access_token:
        raise HTTPException(status_code=401, detail="access_token required")

    logger.info("chat_request session_id=%s", session_id)

    try:
        result = await call_agent(
            access_token=access_token,
            message=message,
            previous_response_id=previous_response_id,
        )
        return result
    except asyncio.TimeoutError:
        logger.error("Agent call timed out session_id=%s", session_id)
        raise HTTPException(status_code=504, detail="Agent call timed out")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Agent call failed session_id=%s", session_id)
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/chat/approve")
async def chat_approve(request: Request):
    """Approve MCP tool calls and continue the conversation."""
    body = await request.json()
    access_token = body.get("access_token")
    previous_response_id = body.get("previous_response_id")
    approval_id_list = body.get("approval_ids", [])

    if not access_token:
        raise HTTPException(status_code=401, detail="access_token required")
    if not previous_response_id:
        raise HTTPException(status_code=400, detail="previous_response_id required")

    try:
        result = await approve_tools(
            access_token=access_token,
            previous_response_id=previous_response_id,
            approval_ids=approval_id_list,
        )
        return result
    except asyncio.TimeoutError:
        logger.error("Approval call timed out")
        raise HTTPException(status_code=504, detail="Approval call timed out")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Approval call failed")
        raise HTTPException(status_code=502, detail=str(e))


# ---------------------------------------------------------------------------
# Static files (SPA) — must be mounted after API routes
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")
