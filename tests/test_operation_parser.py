import pytest

from services.operation_parser import OperationParser, OperationParseError

from operations.operation_reference import OperationReference
from operations.referenced_operation import ReferencedOperation

def test_operation_parser_normalizes_update_entity_id_from_string():
    parser = OperationParser()

    operations = parser.parse(
        {
            "operations": [
                {
                    "type": "update_entity",
                    "entity_id": "12",
                    "description": "Ahora está herido.",
                }
            ]
        }
    )

    assert len(operations) == 1
    assert operations[0].entity_id == 12
    assert isinstance(operations[0].entity_id, int)


def test_operation_parser_rejects_boolean_update_entity_id():
    parser = OperationParser()

    with pytest.raises(OperationParseError):
        parser.parse(
            {
                "operations": [
                    {
                        "type": "update_entity",
                        "entity_id": True,
                    }
                ]
            }
        )

def test_parser_accepts_operation_reference():
    parser = OperationParser()

    operations = parser.parse(
        {
            "operations": [
                {
                    "ref": "sword",
                    "type": "create_item",
                    "name": "Espada oxidada",
                },
                {
                    "type": "create_item_instance",
                    "item_id": "$sword",
                    "owner_id": 7,
                },
            ]
        }
    )

    assert len(operations) == 2

    first = operations[0]
    second = operations[1]

    assert isinstance(
        first,
        ReferencedOperation,
    )
    assert first.ref == "sword"

    assert isinstance(
        second.item_id,
        OperationReference,
    )
    assert second.item_id.name == "sword"