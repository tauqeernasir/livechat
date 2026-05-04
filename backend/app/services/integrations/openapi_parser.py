"""OpenAPI spec parsing and operation extraction.

Uses prance for $ref resolution and openapi-spec-validator for validation.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import prance
from openapi_spec_validator import validate
from openapi_spec_validator.exceptions import OpenAPISpecValidatorError

from app.core.logging import logger


# Maximum number of operations to extract from a single spec
MAX_OPERATIONS = 100

# Allowed HTTP methods for read-only v1
ALLOWED_METHODS = {"get", "head"}


def validate_openapi_spec(spec: dict) -> Tuple[bool, Optional[str]]:
    """Validate that a dict is a valid OpenAPI 3.x spec using openapi-spec-validator.

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(spec, dict):
        return False, "Spec must be a JSON object"

    openapi_version = spec.get("openapi", "")
    if not openapi_version.startswith("3."):
        return False, f"Only OpenAPI 3.x is supported, got: {openapi_version or 'missing'}"

    try:
        validate(spec)
    except OpenAPISpecValidatorError as e:
        # Extract the core message without the full schema dump
        msg = str(e).split("\n")[0][:500]
        return False, f"Spec validation failed: {msg}"
    except Exception as e:
        return False, f"Spec validation error: {str(e)[:500]}"

    return True, None


def resolve_refs(spec: dict) -> dict:
    """Resolve all $ref pointers in an OpenAPI spec using prance.

    Returns a fully dereferenced spec dict.
    """
    resolver = prance.ResolvingParser(spec_string=_spec_to_yaml(spec), backend="openapi-spec-validator")
    return resolver.specification


def extract_base_url(spec: dict) -> Optional[str]:
    """Extract the first server URL from the spec."""
    servers = spec.get("servers", [])
    if servers and isinstance(servers, list) and isinstance(servers[0], dict):
        url = servers[0].get("url", "")
        return url.rstrip("/") if url else None
    return None


def _spec_to_yaml(spec: dict) -> str:
    """Convert spec dict to YAML string for prance."""
    import json
    # prance accepts JSON string as spec_string when using spec_string param
    return json.dumps(spec)


def _build_parameters_schema(
    parameters: List[dict], response_schema: Optional[dict] = None
) -> Optional[dict]:
    """Build a flat JSON schema for tool parameters from resolved path/query params.

    Since $refs are already resolved by prance, we can directly read schemas.
    """
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for param in parameters or []:
        name = param.get("name")
        location = param.get("in")
        if not name or location not in ("path", "query", "header"):
            continue

        schema = param.get("schema", {"type": "string"})
        prop: Dict[str, Any] = {"type": schema.get("type", "string")}

        # Collect description from param or its schema
        desc = param.get("description") or schema.get("description")
        if desc:
            prop["description"] = _sanitize_text(desc, 500)

        # Include enum values if present
        if "enum" in schema:
            prop["enum"] = schema["enum"]

        # Include example if present
        example = param.get("example") or schema.get("example")
        if example is not None:
            prop["example"] = example

        properties[name] = prop
        if param.get("required"):
            required.append(name)

    if not properties:
        return None

    result: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        result["required"] = required
    return result


def _sanitize_text(text: Optional[str], max_length: int = 500) -> Optional[str]:
    """Strip HTML tags and truncate."""
    if not text:
        return None
    clean = re.sub(r"<[^>]*>", "", str(text))
    return clean[:max_length].strip() or None


def _build_description(operation: dict, path: str, method: str) -> Optional[str]:
    """Build a rich description for the LLM from operation metadata.

    Combines summary, description, and response schema hints.
    """
    parts: List[str] = []

    summary = operation.get("summary")
    if summary:
        parts.append(summary.strip())

    description = operation.get("description")
    if description:
        desc_clean = _sanitize_text(description, 800)
        if desc_clean and desc_clean != summary:
            parts.append(desc_clean)

    # Add response content hint so the LLM knows what data to expect
    responses = operation.get("responses", {})
    success_response = responses.get("200") or responses.get("201") or responses.get("default")
    if success_response and isinstance(success_response, dict):
        resp_desc = success_response.get("description")
        if resp_desc and resp_desc not in parts:
            parts.append(f"Returns: {_sanitize_text(resp_desc, 200)}")

        # Describe response schema properties if available
        content = success_response.get("content", {})
        json_content = content.get("application/json", {})
        resp_schema = json_content.get("schema", {})
        if resp_schema:
            schema_hint = _describe_schema(resp_schema)
            if schema_hint:
                parts.append(f"Response fields: {schema_hint}")

    return " | ".join(parts) if parts else None


def _describe_schema(schema: dict, depth: int = 0) -> Optional[str]:
    """Produce a short human-readable summary of a JSON schema for the LLM."""
    if depth > 2 or not isinstance(schema, dict):
        return None

    schema_type = schema.get("type", "object")

    if schema_type == "array":
        items = schema.get("items", {})
        items_desc = _describe_schema(items, depth + 1)
        return f"array of [{items_desc}]" if items_desc else "array"

    if schema_type == "object":
        props = schema.get("properties", {})
        if not props:
            return None
        field_parts = []
        for name, prop in list(props.items())[:10]:  # limit fields
            ftype = prop.get("type", "any")
            fdesc = prop.get("description", "")
            example = prop.get("example")
            hint = f"{name}({ftype})"
            if fdesc:
                hint += f": {_sanitize_text(fdesc, 80)}"
            elif example is not None:
                hint += f" e.g. {example}"
            field_parts.append(hint)
        return ", ".join(field_parts)

    return schema_type


def _extract_response_schema(operation: dict) -> Optional[dict]:
    """Extract the JSON schema of the success response body.

    Returns the raw (already resolved) schema dict so the LLM can inspect
    field names, types, and structure.
    """
    responses = operation.get("responses", {})
    success = responses.get("200") or responses.get("201") or responses.get("default")
    if not success or not isinstance(success, dict):
        return None

    content = success.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema")
    if not schema or not isinstance(schema, dict):
        return None

    # Strip example/default values to keep it compact
    return _compact_schema(schema)


def _compact_schema(schema: dict, depth: int = 0) -> Optional[dict]:
    """Return a compact copy of a JSON schema (strip examples, keep structure)."""
    if depth > 5 or not isinstance(schema, dict):
        return schema

    out: Dict[str, Any] = {}
    for key in ("type", "format", "description", "enum", "required"):
        if key in schema:
            out[key] = schema[key]

    if "properties" in schema:
        out["properties"] = {
            k: _compact_schema(v, depth + 1)
            for k, v in list(schema["properties"].items())[:20]
        }

    if "items" in schema:
        out["items"] = _compact_schema(schema["items"], depth + 1)

    return out or None


def extract_operations(spec: dict) -> List[dict]:
    """Extract callable operations from an OpenAPI spec.

    Resolves all $refs first using prance, then extracts operations with
    full parameter schemas and rich descriptions.

    Returns a list of dicts with keys:
        operation_id, method, path, summary, description, parameters_schema, response_schema
    """
    # Resolve all $refs so we get complete schemas
    try:
        resolved = resolve_refs(spec)
    except Exception as e:
        logger.warning("ref_resolution_failed_using_raw_spec", error=str(e))
        resolved = spec

    operations: List[dict] = []
    paths = resolved.get("paths", {})

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        # Collect path-level parameters (inherited by all methods)
        path_params = path_item.get("parameters", [])

        for method in ALLOWED_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue

            op_id = operation.get("operationId")
            if not op_id:
                op_id = f"{method}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"

            summary = _sanitize_text(operation.get("summary"))
            description = _build_description(operation, path, method)

            # Merge path-level + operation-level parameters (operation wins on conflict)
            all_params = list(path_params)
            op_params = operation.get("parameters", [])
            existing_names = {(p.get("name"), p.get("in")) for p in op_params}
            all_params = [p for p in all_params if (p.get("name"), p.get("in")) not in existing_names]
            all_params.extend(op_params)

            params_schema = _build_parameters_schema(all_params)
            resp_schema = _extract_response_schema(operation)

            operations.append(
                {
                    "operation_id": op_id,
                    "method": method.upper(),
                    "path": path,
                    "summary": summary,
                    "description": description,
                    "parameters_schema": params_schema,
                    "response_schema": resp_schema,
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
