from fastapi import HTTPException

VALID_TRANSITIONS: dict[str, set[str]] = {
    "issued": {"acknowledged", "cancelled"},
    "acknowledged": {"in_transit", "arrived", "cancelled", "no_show"},
    "in_transit": {"arrived", "cancelled", "no_show"},
    "arrived": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "no_show": set(),
}


def assert_valid_transition(current: str, new_status: str):
    allowed = VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {current} to {new_status}",
        )
