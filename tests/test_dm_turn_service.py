from __future__ import annotations

import pytest

from models.dm_turn_result import DMTurnResult
from models.world_state import WorldState
from services.dm_service import DMService
from services.dm_turn_service import (
    DMTurnService,
    DMTurnServiceError,
)


class FakeDMService(DMService):
    """
    Fake mínimo para probar DMTurnService sin tocar ningún LLM.
    """

    def __init__(
        self,
        response: str = "El camino continúa bajo la lluvia.",
    ) -> None:
        self.response = response
        self.calls: list[tuple[WorldState, str]] = []

    def generate(
        self,
        world: WorldState,
        player_input: str,
    ) -> str:
        self.calls.append(
            (
                world,
                player_input,
            )
        )

        return self.response


class FailingDMService(DMService):

    def __init__(
        self,
        error: Exception | None = None,
    ) -> None:
        self.error = (
            error
            or RuntimeError("boom")
        )

    def generate(
        self,
        world: WorldState,
        player_input: str,
    ) -> str:
        raise self.error


# ============================================================
# CONSTRUCTION
# ============================================================


def test_requires_dm_service():
    with pytest.raises(TypeError):
        DMTurnService(
            object()  # type: ignore[arg-type]
        )


def test_accepts_dm_service():
    dm = FakeDMService()

    service = DMTurnService(dm)

    assert service.dm_service is dm


# ============================================================
# VALIDATION
# ============================================================


def test_rejects_invalid_world():
    service = DMTurnService(
        FakeDMService()
    )

    with pytest.raises(
        TypeError,
        match="world must be a WorldState",
    ):
        service.run_turn(
            object(),  # type: ignore[arg-type]
            "Exploro la cueva.",
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        123,
        [],
        {},
    ],
)
def test_rejects_non_string_player_input(value):
    service = DMTurnService(
        FakeDMService()
    )

    with pytest.raises(
        TypeError,
        match="player_input must be a string",
    ):
        service.run_turn(
            WorldState(),
            value,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "\t",
        "\n",
        "   \n\t  ",
    ],
)
def test_rejects_empty_player_input(value):
    service = DMTurnService(
        FakeDMService()
    )

    with pytest.raises(
        DMTurnServiceError,
        match="player_input must not be empty",
    ):
        service.run_turn(
            WorldState(),
            value,
        )


# ============================================================
# NORMAL TURN
# ============================================================


def test_run_turn_returns_dm_turn_result():
    dm = FakeDMService(
        "Una figura emerge de la niebla."
    )

    service = DMTurnService(dm)

    world = WorldState()

    result = service.run_turn(
        world,
        "Miro hacia la niebla.",
    )

    assert isinstance(
        result,
        DMTurnResult,
    )

    assert result.player_input == (
        "Miro hacia la niebla."
    )

    assert result.narrative == (
        "Una figura emerge de la niebla."
    )


def test_player_input_is_stripped():
    dm = FakeDMService()

    service = DMTurnService(dm)

    service.run_turn(
        WorldState(),
        "   Abro la puerta.   ",
    )

    assert dm.calls[0][1] == (
        "Abro la puerta."
    )


def test_narrative_is_stripped():
    dm = FakeDMService(
        "   La puerta se abre.   "
    )

    service = DMTurnService(dm)

    result = service.run_turn(
        WorldState(),
        "Abro la puerta.",
    )

    assert result.narrative == (
        "La puerta se abre."
    )


def test_provider_is_called_exactly_once():
    dm = FakeDMService()

    service = DMTurnService(dm)

    world = WorldState()

    service.run_turn(
        world,
        "Avanzo.",
    )

    assert len(dm.calls) == 1
    assert dm.calls[0] == (
        world,
        "Avanzo.",
    )


# ============================================================
# ERRORS
# ============================================================


def test_dm_service_failure_is_wrapped():
    dm = FailingDMService(
        RuntimeError("LLM failed")
    )

    service = DMTurnService(dm)

    with pytest.raises(
        DMTurnServiceError,
        match="DMService failed to generate the turn",
    ) as exc_info:

        service.run_turn(
            WorldState(),
            "Ataco.",
        )

    assert isinstance(
        exc_info.value.__cause__,
        RuntimeError,
    )


def test_dm_service_returning_non_string_fails():
    class InvalidDMService(DMService):

        def __init__(self):
            pass

        def generate(
            self,
            world,
            player_input,
        ):
            return 123  # type: ignore[return-value]

    service = DMTurnService(
        InvalidDMService()
    )

    with pytest.raises(
        DMTurnServiceError,
        match="non-string narrative",
    ):
        service.run_turn(
            WorldState(),
            "Pruebo algo.",
        )


def test_dm_service_returning_empty_string_fails():
    dm = FakeDMService("   ")

    service = DMTurnService(dm)

    with pytest.raises(
        DMTurnServiceError,
        match="empty narrative",
    ):
        service.run_turn(
            WorldState(),
            "Espero.",
        )


# ============================================================
# CALLABLE API
# ============================================================


def test_service_is_callable():
    dm = FakeDMService(
        "El viento cambia."
    )

    service = DMTurnService(dm)

    result = service(
        WorldState(),
        "Escucho el viento.",
    )

    assert isinstance(
        result,
        DMTurnResult,
    )

    assert result.narrative == (
        "El viento cambia."
    )


# ============================================================
# WORLD IMMUTABILITY
# ============================================================


def test_run_turn_does_not_replace_world():
    dm = FakeDMService()

    service = DMTurnService(dm)

    world = WorldState()

    before = world

    service.run_turn(
        world,
        "Camino.",
    )

    assert world is before


def test_run_turn_does_not_modify_world_collections():
    dm = FakeDMService()

    service = DMTurnService(dm)

    world = WorldState()

    entities_before = dict(
        world.entities
    )

    items_before = dict(
        world.items
    )

    relations_before = dict(
        world.relations
    )

    events_before = dict(
        world.events
    )

    service.run_turn(
        world,
        "Exploro.",
    )

    assert world.entities == entities_before
    assert world.items == items_before
    assert world.relations == relations_before
    assert world.events == events_before


# ============================================================
# RESULT
# ============================================================


def test_result_response_is_alias_for_narrative():
    result = DMTurnResult(
        player_input="Avanzo.",
        narrative="Encuentras una puerta.",
    )

    assert result.response == (
        result.narrative
    )


def test_result_is_immutable():
    result = DMTurnResult(
        player_input="Avanzo.",
        narrative="Encuentras una puerta.",
    )

    with pytest.raises(
        AttributeError
    ):
        result.narrative = "Otra cosa."  # type: ignore[misc]