from __future__ import annotations

from squadron_sdk import InvocationMetadata, current_invocation
from squadron_sdk.invocation import (
    _from_grpc_metadata,
    _reset_current,
    _set_current,
    _to_grpc_metadata,
)


def test_invocation_metadata_round_trip_and_scope():
    want = InvocationMetadata(
        run_id="run-1",
        task_name="collect",
        attempt_id="attempt-1",
        tool_use_id="call-1",
        idempotency_key="key-1",
    )
    got = _from_grpc_metadata(_to_grpc_metadata(want).items())
    assert got == want

    token = _set_current(got)
    try:
        assert current_invocation() == want
    finally:
        _reset_current(token)
    assert current_invocation() is None


def test_partial_invocation_metadata_is_not_exposed():
    assert _from_grpc_metadata([("squadron-run-id", "run-1")]) is None
