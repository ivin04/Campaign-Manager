from models.entity import Entity
from models.world_state import WorldState

from operations.world_operations import (
    CreateRelationOperation,
)

from services.world_extraction_service import (
    WorldExtractionService,
)


class FakeWorldService:

    def __init__(self, world):
        self.world = world
        self.applied_operations = []
        self.save_calls = 0

    def get_world(self):
        return self.world

    def apply_operations(self, operations):
        self.applied_operations.extend(operations)

        return {
            "success": True,
            "results": [],
            "world": self.world,
        }

    def apply_operations_and_save(self, operations):
        self.applied_operations.extend(operations)
        self.save_calls += 1

        return {
            "success": True,
            "results": [],
            "world": self.world,
        }


def build_world():
    return WorldState(
        entities={
            1: Entity(
                id=1,
                name="Fungoso",
                entity_type="character",
            ),
            2: Entity(
                id=2,
                name="Goblin",
                entity_type="creature",
            ),
        }
    )


def test_empty_text_is_ignored():

    service = WorldExtractionService(
        extractor=lambda text, world: []
    )

    result = service.extract(
        "",
        build_world(),
    )

    assert result.operations == []
    assert result.ignored is True


def test_whitespace_text_is_ignored():

    service = WorldExtractionService(
        extractor=lambda text, world: []
    )

    result = service.extract(
        "   ",
        build_world(),
    )

    assert result.operations == []
    assert result.ignored is True


def test_extractor_receives_text_and_world():

    received = {}

    def extractor(text, world):

        received["text"] = text
        received["world"] = world

        return []

    world = build_world()

    service = WorldExtractionService(
        extractor=extractor,
    )

    service.extract(
        "Fungoso entra en la taberna.",
        world,
    )

    assert received["text"] == "Fungoso entra en la taberna."
    assert received["world"] is world


def test_extractor_operations_are_returned():

    operation = CreateRelationOperation(
        relation_id="fungoso-goblin",
        subject_id=1,
        relation_type="enemy_of",
        target_id=2,
    )

    service = WorldExtractionService(
        extractor=lambda text, world: [operation]
    )

    result = service.extract(
        "El goblin se convierte en enemigo de Fungoso.",
        build_world(),
    )

    assert result.ignored is False
    assert len(result.operations) == 1
    assert result.operations[0] is operation


def test_none_from_extractor_means_no_operations():

    service = WorldExtractionService(
        extractor=lambda text, world: None
    )

    result = service.extract(
        "La lluvia cae sobre la ciudad.",
        build_world(),
    )

    assert result.operations == []
    assert result.ignored is True


def test_extract_and_apply():

    operation = CreateRelationOperation(
        relation_id="fungoso-goblin",
        subject_id=1,
        relation_type="enemy_of",
        target_id=2,
    )

    service = WorldExtractionService(
        extractor=lambda text, world: [operation]
    )

    world_service = FakeWorldService(
        build_world()
    )

    result = service.extract_and_apply(
        "El goblin se convierte en enemigo de Fungoso.",
        world_service,
    )

    assert result.operations == [operation]

    assert world_service.applied_operations == [
        operation
    ]

    assert world_service.save_calls == 0


def test_extract_and_apply_and_save():

    operation = CreateRelationOperation(
        relation_id="fungoso-goblin",
        subject_id=1,
        relation_type="enemy_of",
        target_id=2,
    )

    service = WorldExtractionService(
        extractor=lambda text, world: [operation]
    )

    world_service = FakeWorldService(
        build_world()
    )

    result = service.extract_and_apply_and_save(
        "El goblin se convierte en enemigo de Fungoso.",
        world_service,
    )

    assert result.operations == [operation]

    assert world_service.applied_operations == [
        operation
    ]

    assert world_service.save_calls == 1


def test_extract_and_apply_and_save_does_not_save_if_nothing_changed():

    service = WorldExtractionService(
        extractor=lambda text, world: []
    )

    world_service = FakeWorldService(
        build_world()
    )

    result = service.extract_and_apply_and_save(
        "La lluvia cae sobre la ciudad.",
        world_service,
    )

    assert result.operations == []

    assert world_service.applied_operations == []

    assert world_service.save_calls == 0