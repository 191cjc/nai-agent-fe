"""Isolated, bounded MCP subscription reader; never invokes a generation tool."""

import json
import re
import time
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import ValidationError

from ._http_response import (
    InvalidResponseBody,
    ResponseDeadlineExceeded,
    check_deadline,
    read_bounded_body,
)
from .account_balance import MAX_SAFE_INTEGER, AccountBalance, BalanceFailure

PROTOCOL_VERSION = "2025-06-18"
MAX_RESPONSE_BYTES = 1024 * 1024
QUERY_SECONDS = 15.0
SCHEMA_ANNOTATIONS = frozenset({
    "title", "description", "default", "$comment", "examples", "deprecated",
    "readOnly", "writeOnly",
})


def _json_object(body: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(body)
    except (ValueError, UnicodeError, RecursionError):
        raise BalanceFailure("balance_bad_response") from None
    if not isinstance(value, dict):
        raise BalanceFailure("balance_bad_response")
    return value


def _message(body: bytes, content_type: str, request_id: int) -> dict[str, Any]:
    if content_type == "application/json":
        message = _json_object(body)
    elif content_type == "text/event-stream":
        try:
            events = re.split(r"\r?\n\r?\n", body.decode("utf-8"))
        except UnicodeError:
            raise BalanceFailure("balance_bad_response") from None
        matches = []
        for event in events:
            data = "\n".join(
                line[5:].lstrip() for line in event.splitlines() if line.startswith("data:")
            )
            if data:
                value = _json_object(data)
                if value.get("id") == request_id:
                    matches.append(value)
        if len(matches) != 1:
            raise BalanceFailure("balance_bad_response")
        message = matches[0]
    else:
        raise BalanceFailure("balance_bad_response")
    if (
        message.get("jsonrpc") != "2.0"
        or type(message.get("id")) is not int
        or message["id"] != request_id
        or "error" in message
        or not isinstance(message.get("result"), dict)
    ):
        raise BalanceFailure("balance_bad_response")
    return message["result"]


def _empty_input_schema(schema: Any) -> bool:
    if not isinstance(schema, dict):
        return False
    return (
        (set(schema) - SCHEMA_ANNOTATIONS).issubset({
            "type", "properties", "required", "additionalProperties",
        })
        and schema.get("type") == "object"
        and schema.get("properties") == {}
        and schema.get("required", []) == []
        and type(schema.get("additionalProperties", True)) is bool
    )


class NovelAiMcpBalanceProvider:
    def __init__(
        self, url: str, token: str, *, transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self.url = url
        self.token = token
        self.transport = transport
        self.clock = clock
        self.wall_clock = wall_clock

    def fetch(self) -> AccountBalance:
        deadline = self.clock() + QUERY_SECONDS
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/event-stream",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
        }
        session_id: str | None = None
        request_id = 0

        def send(
            client: httpx.Client, method: str, params: dict | None = None,
            *, notification: bool = False,
        ) -> dict:
            nonlocal session_id, request_id
            check_deadline(deadline, self.clock)
            payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
            if not notification:
                request_id += 1
                payload["id"] = request_id
            if params is not None:
                payload["params"] = params
            if session_id is not None:
                headers["Mcp-Session-Id"] = session_id
            if method != "initialize":
                headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
            remaining = deadline - self.clock()
            check_deadline(deadline, self.clock)
            with client.stream(
                "POST", self.url, json=payload, headers=headers,
                timeout=httpx.Timeout(remaining, connect=min(5.0, remaining)),
            ) as response:
                check_deadline(deadline, self.clock)
                allowed = (200, 202, 204) if notification else (200,)
                if response.status_code not in allowed:
                    self._check_status(response.status_code)
                session_id = response.headers.get("Mcp-Session-Id", session_id)
                body = read_bounded_body(
                    response, max_bytes=MAX_RESPONSE_BYTES, deadline=deadline, clock=self.clock,
                )
                if notification:
                    return {}
                result = _message(
                    body, response.headers.get("Content-Type", "").split(";")[0].strip().lower(),
                    request_id,
                )
                check_deadline(deadline, self.clock)
                return result

        try:
            with httpx.Client(
                transport=self.transport, timeout=httpx.Timeout(QUERY_SECONDS, connect=5.0),
                follow_redirects=False,
            ) as client:
                initialized = send(client, "initialize", {
                    "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                    "clientInfo": {"name": "novelai-workspace-balance", "version": "0.1.0"},
                })
                if initialized.get("protocolVersion") != PROTOCOL_VERSION:
                    raise BalanceFailure("balance_bad_response")
                send(client, "notifications/initialized", notification=True)
                available = send(client, "tools/list", {})
                tools = available.get("tools")
                if not isinstance(tools, list):
                    raise BalanceFailure("balance_bad_response")
                matching = [
                    tool for tool in tools
                    if isinstance(tool, dict) and tool.get("name") == "get_subscription"
                ]
                if len(matching) != 1 or not _empty_input_schema(matching[0].get("inputSchema")):
                    raise BalanceFailure()
                result = send(client, "tools/call", {"name": "get_subscription", "arguments": {}})
                balance = self._balance(result)
                check_deadline(deadline, self.clock)
                return balance
        except ResponseDeadlineExceeded:
            raise BalanceFailure("balance_timeout") from None
        except httpx.TimeoutException:
            raise BalanceFailure("balance_timeout") from None
        except httpx.RequestError:
            raise BalanceFailure() from None
        except InvalidResponseBody:
            raise BalanceFailure("balance_bad_response") from None

    def _balance(self, result: dict) -> AccountBalance:
        if type(result.get("isError", False)) is not bool or result.get("isError", False):
            raise BalanceFailure("balance_bad_response")
        if "structuredContent" in result:
            subscription = result["structuredContent"]
        else:
            content = result.get("content")
            if (
                not isinstance(content, list) or len(content) != 1
                or not isinstance(content[0], dict) or content[0].get("type") != "text"
                or not isinstance(content[0].get("text"), str)
            ):
                raise BalanceFailure("balance_bad_response")
            subscription = _json_object(content[0]["text"])
        if not isinstance(subscription, dict):
            raise BalanceFailure("balance_bad_response")
        steps = subscription.get("trainingStepsLeft")
        if not isinstance(steps, dict):
            raise BalanceFailure("balance_bad_response")
        fixed = steps.get("fixedTrainingStepsLeft")
        purchased = steps.get("purchasedTrainingSteps")
        if any(type(count) is not int or not 0 <= count <= MAX_SAFE_INTEGER
               for count in (fixed, purchased)):
            raise BalanceFailure("balance_bad_response")
        try:
            return AccountBalance(
                fixed=fixed, purchased=purchased, total=fixed + purchased,
                fetched_at=int(self.wall_clock()),
            )
        except (ValidationError, ValueError, OverflowError):
            raise BalanceFailure("balance_bad_response") from None

    @staticmethod
    def _check_status(status: int) -> None:
        if status in (401, 403):
            raise BalanceFailure("balance_auth_error")
        if status == 429:
            raise BalanceFailure("balance_rate_limited")
        if status in (408, 504):
            raise BalanceFailure("balance_timeout")
        if 500 <= status <= 599:
            raise BalanceFailure()
        raise BalanceFailure("balance_bad_response")
