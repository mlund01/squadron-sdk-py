"""Durable tool invocation identity supplied by the Squadron runtime."""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from collections.abc import Iterable, Mapping


RUN_ID_METADATA_KEY = "squadron-run-id"
TASK_NAME_METADATA_KEY = "squadron-task-name"
ATTEMPT_ID_METADATA_KEY = "squadron-attempt-id"
TOOL_USE_ID_METADATA_KEY = "squadron-tool-use-id"
IDEMPOTENCY_METADATA_KEY = "squadron-idempotency-key"


@dataclass(frozen=True)
class InvocationMetadata:
    """Identity of one logical tool call across retries and restarts."""

    run_id: str
    task_name: str
    attempt_id: str
    tool_use_id: str
    idempotency_key: str


_current: ContextVar[InvocationMetadata | None] = ContextVar(
    "squadron_invocation", default=None
)


def current_invocation() -> InvocationMetadata | None:
    """Return the current call's durable identity, when called by a mission."""

    return _current.get()


def _from_grpc_metadata(
    metadata: Mapping[str, str] | Iterable[tuple[str, str]] | None,
) -> InvocationMetadata | None:
    values = dict(metadata.items()) if isinstance(metadata, Mapping) else dict(metadata or ())
    invocation = InvocationMetadata(
        run_id=values.get(RUN_ID_METADATA_KEY, ""),
        task_name=values.get(TASK_NAME_METADATA_KEY, ""),
        attempt_id=values.get(ATTEMPT_ID_METADATA_KEY, ""),
        tool_use_id=values.get(TOOL_USE_ID_METADATA_KEY, ""),
        idempotency_key=values.get(IDEMPOTENCY_METADATA_KEY, ""),
    )
    if not invocation.tool_use_id or not invocation.idempotency_key:
        return None
    return invocation


def _set_current(invocation: InvocationMetadata | None) -> Token:
    return _current.set(invocation)


def _reset_current(token: Token) -> None:
    _current.reset(token)


def _to_grpc_metadata(invocation: InvocationMetadata) -> dict[str, str]:
    return {
        RUN_ID_METADATA_KEY: invocation.run_id,
        TASK_NAME_METADATA_KEY: invocation.task_name,
        ATTEMPT_ID_METADATA_KEY: invocation.attempt_id,
        TOOL_USE_ID_METADATA_KEY: invocation.tool_use_id,
        IDEMPOTENCY_METADATA_KEY: invocation.idempotency_key,
    }
