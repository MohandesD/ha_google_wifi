"""Correlate explicit Google actions without treating acknowledgement as completion."""

from datetime import UTC, datetime

MONITORED_ACTIONS = {"restart_network", "restart_point", "test_internet", "test_mesh", "test_local", "test_clients"}
OPERATION_PHASES = ["none", "queued", "sending", "accepted", "running", "completed", "failed", "cancelled", "unconfirmed"]
TERMINAL_STATES = {"DONE", "ERROR", "FAILED", "CANCELLED", "REJECTED", "DELIVERY_UNCONFIRMED", "PENDING_UNCONFIRMED"}
MONITOR_SECONDS = 600


def now_iso():
    return datetime.now(UTC).isoformat()


def phase(operation):
    state = operation.get("state")
    if state == "ACCEPTED_UNCONFIRMED":
        return "accepted" if operation.get("operation_id") else "unconfirmed"
    return {"QUEUED": "queued", "SENDING": "sending", "CREATED": "accepted", "PENDING": "accepted",
            "RUNNING": "running", "IN_PROGRESS": "running", "DONE": "completed", "ERROR": "failed",
            "FAILED": "failed", "REJECTED": "failed", "CANCELLED": "cancelled"}.get(state, "unconfirmed" if state else "none")


def pending(operation):
    return operation.get("state") not in TERMINAL_STATES and (
        operation.get("state") in {"QUEUED", "SENDING"} or bool(operation.get("operation_id")))


def summary(operation):
    if not operation:
        return None
    # Opaque Google operation IDs can contain large serialized command bodies.
    result = {key: operation[key] for key in (
        "request_id", "action", "target_kind", "target_id", "target_name", "state",
        "requested_at", "updated_at", "finished_at", "http_status", "status_error",
    ) if key in operation}
    return {**result, "phase": phase(operation)}


def latest(network, kind, item_id, action=None):
    operations = network.get("operations", [])
    return next((operation for operation in reversed(operations)
                 if operation.get("action") in MONITORED_ACTIONS
                 and (action is None or operation.get("action") == action)
                 and (kind == "network" and action is None or
                      operation.get("target_kind") == kind and operation.get("target_id") == item_id)), None)
