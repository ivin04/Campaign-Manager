import json

import pytest

from models.world_state import WorldState
from models.operation_result import OperationResult
from operations.world_operations import WorldOperation
from services.llm_world_extractor import (
    LLMExtractionError,
    LLMWorldExtractor,
)

from services.fake_llm_provider import (
    FakeLLMProvider,
)

class FakeOperation(WorldOperation):
    pass


class FakeParser:
    def __init__(self, operation):
        self.operation = operation
        self.calls = []

    def parse(self, data):
        self.calls.append(data)
        return self.operation


def make_extractor(response, operation):
    provider_calls = []

    def provider(prompt):
        provider_calls.append(prompt)
        return response

    parser = FakeParser(operation)

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
            "type": "create_entity",
            "name": "Aldric",
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


def test_operation_must_be_object():
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
        operation_parser=FakeParser(
            FakeOperation()
        ),
    )

    with pytest.raises(
        LLMExtractionError,
        match="must be an object",
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
        match="Invalid operation",
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
        match="invalid WorldOperation",
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