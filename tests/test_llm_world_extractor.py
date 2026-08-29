import json

import pytest

from models.world_state import WorldState
from models.operation_result import OperationResult
from operations.world_operations import CreateEntityOperation, WorldOperation
from services.llm_world_extractor import (
    LLMExtractionError,
    LLMWorldExtractor,
)

class FakeOperation(WorldOperation):
    pass


class FakeProvider:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, prompt):
        self.calls.append(prompt)
        return self.response


class FakeParser:
    def __init__(
        self,
        operations=None,
        exception=None,
    ):
        self.operations = (
            []
            if operations is None
            else operations
        )

        self.exception = exception
        self.calls = []

    def parse(self, payload):
        self.calls.append(payload)

        if self.exception is not None:
            raise self.exception

        return self.operations


def make_extractor(response, operation):
    provider_calls = []

    def provider(prompt):
        provider_calls.append(prompt)
        return response

    parser = FakeParser(
        operations=[operation]
    )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=parser,
    )

    return (
        extractor,
        provider_calls,
        parser,
    )


def test_valid_response_returns_operations():
    operation = FakeOperation()

    response = json.dumps(
        {
            "operations": [
                {
                    "type": "create_entity",
                    "name": "Aldric",
                }
            ]
        }
    )

    extractor, provider_calls, parser = (
        make_extractor(
            response,
            operation,
        )
    )

    result = extractor.extract(
        "Aldric entra en la taberna.",
        WorldState(),
    )

    assert result == [operation]

    assert len(provider_calls) == 1

    assert parser.calls == [
        {
            "operations": [
                {
                    "type": "create_entity",
                    "name": "Aldric",
                }
            ]
        }
    ]


def test_empty_text_does_not_call_provider():
    called = False

    def provider(prompt):
        nonlocal called
        called = True
        return "{}"

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=FakeParser(
            FakeOperation()
        ),
    )

    result = extractor.extract(
        "   ",
        WorldState(),
    )

    assert result == []
    assert called is False


def test_invalid_provider_response_type_fails():
    def provider(prompt):
        return None

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=FakeParser(
            FakeOperation()
        ),
    )

    with pytest.raises(
        LLMExtractionError,
        match="must be a string",
    ):
        extractor.extract(
            "algo ocurrió",
            WorldState(),
        )


def test_empty_provider_response_fails():
    def provider(prompt):
        return "   "

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=FakeParser(
            FakeOperation()
        ),
    )

    with pytest.raises(
        LLMExtractionError,
        match="empty response",
    ):
        extractor.extract(
            "algo ocurrió",
            WorldState(),
        )


def test_invalid_json_fails():
    def provider(prompt):
        return "esto no es json"

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=FakeParser(
            FakeOperation()
        ),
    )

    with pytest.raises(
        LLMExtractionError,
        match="valid JSON",
    ):
        extractor.extract(
            "algo ocurrió",
            WorldState(),
        )


def test_json_array_fails():
    def provider(prompt):
        return "[]"

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=FakeParser(
            FakeOperation()
        ),
    )

    with pytest.raises(
        LLMExtractionError,
        match="JSON object",
    ):
        extractor.extract(
            "algo ocurrió",
            WorldState(),
        )


def test_missing_operations_fails():
    def provider(prompt):
        return json.dumps(
            {
                "something": []
            }
        )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=FakeParser(
            FakeOperation()
        ),
    )

    with pytest.raises(
        LLMExtractionError,
        match="Missing",
    ):
        extractor.extract(
            "algo ocurrió",
            WorldState(),
        )


def test_operations_must_be_list():
    def provider(prompt):
        return json.dumps(
            {
                "operations": {}
            }
        )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=FakeParser(
            FakeOperation()
        ),
    )

    with pytest.raises(
        LLMExtractionError,
        match="must be a list",
    ):
        extractor.extract(
            "algo ocurrió",
            WorldState(),
        )


def test_parser_rejects_invalid_operation():
    class FailingParser:
        def parse(self, data):
            raise ValueError(
                "Operation must be an object"
            )

    def provider(prompt):
        return json.dumps(
            {
                "operations": [
                    "invalid"
                ]
            }
        )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=FailingParser(),
    )

    with pytest.raises(
        LLMExtractionError,
        match="Failed to parse operations",
    ):
        extractor.extract(
            "algo ocurrió",
            WorldState(),
        )


def test_parser_failure_becomes_extraction_error():
    class FailingParser:
        def parse(self, data):
            raise ValueError(
                "invalid operation"
            )

    def provider(prompt):
        return json.dumps(
            {
                "operations": [
                    {
                        "type": "invalid"
                    }
                ]
            }
        )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=FailingParser(),
    )

    with pytest.raises(
        LLMExtractionError,
        match="Failed to parse operations",
    ):
        extractor.extract(
            "algo ocurrió",
            WorldState(),
        )


def test_parser_result_must_be_world_operation():
    class BadParser:
        def parse(self, data):
            return "not an operation"

    def provider(prompt):
        return json.dumps(
            {
                "operations": [
                    {
                        "type": "something"
                    }
                ]
            }
        )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=BadParser(),
    )

    with pytest.raises(
        LLMExtractionError,
        match="invalid result",
    ):
        extractor.extract(
            "algo ocurrió",
            WorldState(),
        )


def test_extractor_does_not_modify_world():
    operation = FakeOperation()

    response = json.dumps(
        {
            "operations": [
                {
                    "type": "create_entity"
                }
            ]
        }
    )

    extractor, _, _ = make_extractor(
        response,
        operation,
    )

    world = WorldState()

    before = repr(world)

    extractor.extract(
        "Aldric aparece.",
        world,
    )

    after = repr(world)

    assert after == before


def test_callable_interface_matches_extractor():
    operation = FakeOperation()

    response = json.dumps(
        {
            "operations": [
                {
                    "type": "create_entity"
                }
            ]
        }
    )

    extractor, _, _ = make_extractor(
        response,
        operation,
    )

    result = extractor(
        "Aldric aparece.",
        WorldState(),
    )

    assert result == [operation]

def test_parser_receives_complete_payload():
    operation = CreateEntityOperation(
        name="Aldric",
        entity_type="npc",
        description="Un guerrero.",
        notes="",
        active=True,
    )

    parser = FakeParser(
        operations=[operation]
    )

    provider = FakeProvider(
        json.dumps(
            {
                "operations": [
                    {
                        "type": "create_entity",
                        "name": "Aldric",
                        "entity_type": "npc",
                        "description": "Un guerrero.",
                        "notes": "",
                        "active": True,
                    }
                ]
            }
        )
    )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=parser,
    )

    extractor.extract(
        "Aldric aparece en la taberna.",
        WorldState(),
    )

    assert len(parser.calls) == 1

    assert parser.calls[0] == {
        "operations": [
            {
                "type": "create_entity",
                "name": "Aldric",
                "entity_type": "npc",
                "description": "Un guerrero.",
                "notes": "",
                "active": True,
            }
        ]
    }

def test_parser_failure_is_wrapped():
    parser = FakeParser(
        exception=ValueError("invalid operation")
    )

    provider = FakeProvider(
        '{"operations": []}'
    )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=parser,
    )

    with pytest.raises(
        LLMExtractionError,
        match="Failed to parse operations",
    ):
        extractor.extract(
            "Algo ocurre.",
            WorldState(),
        )

def test_multiple_operations_are_returned():
    operation_1 = CreateEntityOperation(
        name="Aldric",
        entity_type="npc",
        description="Guerrero.",
        notes="",
        active=True,
    )

    operation_2 = CreateEntityOperation(
        name="Mara",
        entity_type="npc",
        description="Mercader.",
        notes="",
        active=True,
    )

    parser = FakeParser(
        operations=[
            operation_1,
            operation_2,
        ]
    )

    provider = FakeProvider(
        '{"operations": ['
        '{"type": "create_entity"},'
        '{"type": "create_entity"}'
        ']}'
    )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=parser,
    )

    result = extractor.extract(
        "Aldric y Mara aparecen.",
        WorldState(),
    )

    assert result == [
        operation_1,
        operation_2,
    ]

def test_prompt_includes_known_entity_ids():
    provider = FakeProvider(
        '{"operations": []}'
    )

    parser = FakeParser()

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=parser,
    )

    world = WorldState()

    entity = world.entities[1] = type(
        "Entity",
        (),
        {
            "name": "Aldric",
            "entity_type": "npc",
        },
    )()

    extractor.extract(
        "Aldric aparece.",
        world,
    )

    assert len(provider.calls) == 1

    assert "ID 1" in provider.calls[0]
    assert "Aldric" in provider.calls[0]
    assert "npc" in provider.calls[0]

def test_prompt_does_not_include_unrelated_world_state():
    provider = FakeProvider(
        '{"operations": []}'
    )

    parser = FakeParser()

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=parser,
    )

    world = WorldState()

    world.entities[1] = type(
        "Entity",
        (),
        {
            "name": "Aldric",
            "entity_type": "npc",
            "description": "Mercader de Vorder's Hold.",
        },
    )()

    extractor.extract(
        "Aldric aparece.",
        world,
    )

    prompt = provider.calls[0]

    assert "Aldric" in prompt
    assert "Mercader de Vorder's Hold" not in prompt

def test_extractor_accepts_turn_context(
    monkeypatch,
):
    from models.turn_context import TurnContext
    from services.llm_world_extractor import (
        LLMWorldExtractor,
    )

    context = make_turn_context()

    captured = {}

    def fake_provider(prompt):
        captured["prompt"] = prompt

        return """
        {
            "operations": []
        }
        """

    extractor = LLMWorldExtractor(
        provider=fake_provider,
        operation_parser=FakeOperationParser(),
    )

    result = extractor.extract(
        "El personaje descansa.",
        context,
    )

    assert result == []

    assert "PERSONAJE ACTIVO" in captured["prompt"]
    assert "HP actual" in captured["prompt"]
    assert "HP máximo" in captured["prompt"]

def test_extractor_prompt_contains_active_character_id(
    monkeypatch,
):
    from services.llm_world_extractor import (
        LLMWorldExtractor,
    )

    context = make_turn_context()

    captured = {}

    def fake_provider(prompt):
        captured["prompt"] = prompt

        return """
        {
            "operations": [
                {
                    "type": "change_character_hp",
                    "entity_id": 1,
                    "amount": -5
                }
            ]
        }
        """

    extractor = LLMWorldExtractor(
        provider=fake_provider,
        operation_parser=operation_parser,
    )

    operations = extractor.extract(
        "El personaje recibe un golpe y pierde 5 puntos de vida.",
        context,
    )

    assert len(operations) == 1

    operation = operations[0]

    assert operation.entity_id == 1
    assert operation.amount == -5

    assert "ID 1:" in captured["prompt"]
    assert "[PERSONAJE ACTIVO]" in captured["prompt"]

def test_extractor_prompt_handles_missing_active_character():
    context = make_turn_context(
        active_character=None,
    )

    prompt = LLMWorldExtractor._build_prompt(
        "La puerta se abre.",
        context,
    )

    assert "No hay personaje activo." in prompt