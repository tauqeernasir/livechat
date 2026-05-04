"""OpenAPI spec parsing and operation extraction."""

import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger


# Maximum number of operations to extract from a single spec
MAX_OPERATIONS = 100

# Allowed HTTP methods for read-only v1
ALLOWED_METHODS = {"get", "head"}


def validate_openapi_spec(spec: dict) -> Tuple[bool, Optional[str]]:
    """Validate that a dict is a valid OpenAPI 3.x spec.

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(spec, dict):
        return False, "Spec must be a JSON object"

    openapi_version = spec.get("openapi", "")
    if not openapi_version.startswith("3."):
        return False, f"Only OpenAPI 3.x is supported, got: {openapi_version or 'missing'}"

    info = spec.get("info")
    if not isinstance(info, dict) or "title" not in info:
        return False, "Spec must have an info.title field"

    paths = spec.get("paths")
    if not isinstance(paths, dict) or len(paths) == 0:
        return False, "Spec must have at least one path"

    return True, None


def extract_base_url(spec: dict) -> Optional[str]:
    """Extract the first server URL from the spec."""
    servers = spec.get("servers", [])
    if servers and isinstance(servers, list) and isinstance(servers[0], dict):
        url = servers[0].get("url", "")
        # Strip trailing slash
        return url.rstrip("/") if url else None
    return None


def _resolve_ref(spec: dict, ref: str) -> Optional[dict]:
    """Resolve a simple $ref pointer (no recursion beyond 3 levels)."""
    if not ref.startswith("#/"):
        return None
    parts = ref.lstrip("#/").split("/")
    current = spec
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current if isinstance(current, dict) else None


def _build_parameters_schema(
    spec: dict, parameters: List[dict], request_body: Optional[dict]
) -> Optional[dict]:
    """Build a flat JSON schema for tool parameters from path/query params and request body."""
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for param in parameters or []:
        if "$ref" in param:
            param = _resolve_ref(spec, param["$ref"]) or param
        name = param.get("name")
        location = param.get("in")
        if not name or location not in ("path", "query", "header"):
            continue
        schema = param.get("schema", {"type": "string"})
        if "$ref" in schema:
            schema = _resolve_ref(spec, schema["$ref"]) or {"type": "string"}
        prop: Dict[str, Any] = {"type": schema.get("type", "string")}
        desc = param.get("description") or schema.get("description")
        if desc:
            prop["description"] = desc[:500]
        properties[name] = prop
        if param.get("required"):
            required.append(name)

    if not properties:
        return None

    schema: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _sanitize_text(text: Optional[str], max_length: int = 500) -> Optional[str]:
    """Strip HTML tags and truncate."""
    if not text:
        return None
    clean = re.sub(r"<[^>]*>", "", str(text))
    return clean[:max_length].strip() or None


def extract_operations(spec: dict) -> List[dict]:
    """Extract callable operations from an OpenAPI spec.

    Returns a list of dicts with keys:
        operation_id, method, path, summary, description, parameters_schema
    """
    operations: List[dict] = []
    paths = spec.get("paths", {})

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method in ALLOWED_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue

            op_id = operation.get("operationId")
            if not op_id:
                # Generate an operationId from method + path
                op_id = f"{method}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"

            summary = _sanitize_text(operation.get("summary"))
            description = _sanitize_text(operation.get("description"), max_length=1000)

            params = list(path_item.get("parameters", [])) + list(
                operation.get("parameters", [])
            )
            params_schema = _build_parameters_schema(spec, params, operation.get("requestBody"))

            operations.append(
                {
                    "operation_id": op_id,
                    "method": method.upper(),
                    "path": path,
                    "summary": summary,
                    "description": description,
                    "parameters_schema": params_schema,
                }
            )

            if len(operations) >= MAX_OPERATIONS:
                logger.warning(
                    "openapi_operations_truncated",
                    max_operations=MAX_OPERATIONS,
                    total_paths=len(paths),
                )
                return operations

    return operations
