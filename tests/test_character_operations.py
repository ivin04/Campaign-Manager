from operations.character_operations import (
    ChangeCharacterHpOperation,
    CharacterOperation,
)


def test_change_character_hp_operation_is_character_operation():

    operation = ChangeCharacterHpOperation(
        entity_id=10,
        amount=-4,
    )

    assert isinstance(
        operation,
        CharacterOperation,
    )


def test_change_character_hp_operation_stores_damage():

    operation = ChangeCharacterHpOperation(
        entity_id=10,
        amount=-4,
    )

    assert operation.entity_id == 10
    assert operation.amount == -4


def test_change_character_hp_operation_stores_healing():

    operation = ChangeCharacterHpOperation(
        entity_id=10,
        amount=6,
    )

    assert operation.entity_id == 10
    assert operation.amount == 6