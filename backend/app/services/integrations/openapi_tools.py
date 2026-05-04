"""OpenAPI tool adapter — converts integration operations into LangChain tools."""

import json
import re
from typing import Any, Dict, List, Optional

import httpx
from langchain_core.tools import StructuredTool

from app.core.logging import logger
from app.services.integrations.credentials import decrypt_credential


# Maximum response body size to return to the model (truncated)
MAX_RESPONSE_SIZE = 4000

# Timeout for external API calls
API_CALL_TIMEOUT = 30


def _build_tool_func(
    *,
    base_url: str,
    method: str,
    path: str,
    auth_type: str,
    auth_header_name: str,
    encrypted_credentials: Optional[str],
    integration_name: str,
    operation_id: str,
):
    """Create an async callable for a single OpenAPI operation."""

    async def _call(**kwargs: Any) -> str:
        # Build URL with path parameters
        url = base_url + path
        path_params = re.findall(r"\{(\w+)\}", path)
        query_params: Dict[str, Any] = {}

        for key in list(kwargs.keys()):
            if key in path_params:
                url = url.replace(f"{{{key}}}", str(kwargs.pop(key)))

        # Remaining kwargs become query parameters
        query_params = kwargs

        # Auth headers
        headers: Dict[str, str] = {"Accept": "application/json"}
        if auth_type != "none" and encrypted_credentials:
            credential = decrypt_credential(encrypted_credentials)
            if credential:
                if auth_type == "bearer":
                    headers[auth_header_name] = f"Bearer {credential}"
                elif auth_type in ("api_key", "header"):
                    headers[auth_header_name] = credential

        try:
            async with httpx.AsyncClient(
                timeout=API_CALL_TIMEOUT, follow_redirects=True
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=query_params if query_params else None,
                    headers=headers,
                )
                response.raise_for_status()

                body = response.text[:MAX_RESPONSE_SIZE]
                # Try to produce compact JSON
                try:
                    parsed = json.loads(body)
                    body = json.dumps(parsed, indent=None, ensure_ascii=False)
                    if len(body) > MAX_RESPONSE_SIZE:
                        body = body[:MAX_RESPONSE_SIZE] + "…[truncated]"
                except (json.JSONDecodeError, ValueError):
                    pass

                return body

        except httpx.HTTPStatusError as e:
            logger.warning(
                "integration_api_error",
                integration=integration_name,
                operation=operation_id,
                status_code=e.response.status_code,
            )
            return f"API error {e.response.status_code}: {e.response.text[:500]}"
        except Exception as e:
            logger.error(
                "integration_api_call_failed",
                integration=integration_name,
                operation=operation_id,
                error=str(e),
            )
            return f"Failed to call {integration_name}/{operation_id}: {str(e)[:200]}"

    return _call


def build_openapi_tools(operations: List[dict]) -> List[StructuredTool]:
    """Convert a list of enabled operation dicts into LangChain StructuredTool instances.

    Args:
        operations: List of operation dicts from IntegrationService.get_enabled_operations().

    Returns:
        List of StructuredTool instances ready for LLM binding.
    """
    tools: List[StructuredTool] = []

    for op in operations:
        base_url = op.get("base_url")
        if not base_url:
            logger.warning(
                "skipping_operation_no_base_url",
                operation_id=op["operation_id"],
                integration_name=op["integration_name"],
            )
            continue

        # Build a unique tool name: integration_name__operation_id (sanitized)
        raw_name = f"{op['integration_name']}__{op['operation_id']}"
        tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name)[:64]

        description = op.get("summary") or op.get("description") or f"{op['method']} {op['path']}"
        description = f"[{op['integration_name']}] {description}"

        func = _build_tool_func(
            base_url=base_url,
            method=op["method"],
            path=op["path"],
            auth_type=op["auth_type"],
            auth_header_name=op["auth_header_name"],
            encrypted_credentials=op.get("encrypted_credentials"),
            integration_name=op["integration_name"],
            operation_id=op["operation_id"],
        )

        # Build args_schema from parameters_schema if available
        args_schema = None
        params_schema = op.get("parameters_schema")
        if params_schema and params_schema.get("properties"):
            # Dynamically create a Pydantic model for the tool args
            from pydantic import create_model

            field_definitions = {}
            required_fields = set(params_schema.get("required", []))
            for field_name, field_spec in params_schema["properties"].items():
                field_type = str  # default to string
                default = ... if field_name in required_fields else None
                field_definitions[field_name] = (
                    Optional[field_type] if field_name not in required_fields else field_type,
                    default,
                )
            if field_definitions:
                args_schema = create_model(f"{tool_name}_Args", **field_definitions)

        tool = StructuredTool.from_function(
            coroutine=func,
            name=tool_name,
            description=description[:1024],
            args_schema=args_schema,
        )
        tools.append(tool)

    return tools
