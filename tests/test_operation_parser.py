import pytest

from services.operation_parser import OperationParser, OperationParseError

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