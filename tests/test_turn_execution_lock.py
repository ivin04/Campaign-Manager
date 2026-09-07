from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from services.turn_execution_lock import TurnExecutionLock


def test_turn_execution_lock_serializes_concurrent_turns() -> None:
    """
    Two concurrent turn executions must never run at the same time.

    This protects the shared in-memory WorldState from races between
    /turn and /integration/turn.
    """
    turn_lock = TurnExecutionLock()

    active_turns = 0
    max_active_turns = 0

    state_lock = threading.Lock()
    both_started = threading.Barrier(2)

    def execute_turn() -> None:
        nonlocal active_turns, max_active_turns

        both_started.wait()

        with turn_lock.acquire():
            with state_lock:
                active_turns += 1
                max_active_turns = max(max_active_turns, active_turns)

            # Keep the critical section open long enough for the other
            # thread to attempt entering it.
            time.sleep(0.05)

            with state_lock:
                active_turns -= 1

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(execute_turn),
            executor.submit(execute_turn),
        ]

        for future in futures:
            future.result()

    assert max_active_turns == 1

def test_campaign_and_integration_turns_share_execution_lock(
    campaign_turn_service,
    silly_tavern_integration_service,
) -> None:
    """
    /turn and /integration/turn must share the same execution lock.

    The test deliberately starts both paths concurrently and verifies
    that their critical turn execution sections never overlap.
    """
    active_turns = 0
    max_active_turns = 0

    state_lock = threading.Lock()
    both_started = threading.Barrier(2)

    original_campaign_play_turn = campaign_turn_service._play_turn_locked
    original_integration_process_turn = (
        silly_tavern_integration_service._process_turn_locked
    )

    def wrapped_campaign_turn(*args, **kwargs):
        nonlocal active_turns, max_active_turns

        both_started.wait()

        with state_lock:
            active_turns += 1
            max_active_turns = max(max_active_turns, active_turns)

        try:
            time.sleep(0.05)
            return original_campaign_play_turn(*args, **kwargs)
        finally:
            with state_lock:
                active_turns -= 1

    def wrapped_integration_turn(*args, **kwargs):
        nonlocal active_turns, max_active_turns

        both_started.wait()

        with state_lock:
            active_turns += 1
            max_active_turns = max(max_active_turns, active_turns)

        try:
            time.sleep(0.05)
            return original_integration_process_turn(*args, **kwargs)
        finally:
            with state_lock:
                active_turns -= 1

    campaign_turn_service._play_turn_locked = wrapped_campaign_turn
    silly_tavern_integration_service._process_turn_locked = (
        wrapped_integration_turn
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                campaign_turn_service.play_turn,
                "first turn",
            ),
            executor.submit(
                silly_tavern_integration_service.process_turn,
                player_input="second turn",
                narrative="second narrative",
            ),
        ]

        for future in futures:
            future.result()

    assert max_active_turns == 1