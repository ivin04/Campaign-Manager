from models.schemas import CharacterCreate
from services.character_creation_service import CharacterCreationService


def test_create_character_creates_entity_and_character(
    db,
    campaign_repository,
    entity_repository,
    character_repository,
):
    service = CharacterCreationService(
        db=db,
        campaign_repository=campaign_repository,
        entity_repository=entity_repository,
        character_repository=character_repository,
    )

    data = CharacterCreate(
        name="Arannis",
        class_name="Fighter",
        level=1,
        max_hp=12,
        current_hp=12,
        armor_class=16,
        strength=16,
        dexterity=12,
        constitution=14,
        intelligence=10,
        wisdom=10,
        charisma=8,
        proficiency_bonus=2,
    )

    character = service.create_character(
        campaign_id="campaign-1",
        data=data,
        activate=True,
    )

    assert character.entity_id is not None
    assert character.current_hp == 12
    assert character.max_hp == 12
    assert character.class_name == "Fighter"

def test_create_character_activates_character(
    db,
    campaign_repository,
    entity_repository,
    character_repository,
):
    service = CharacterCreationService(
        db=db,
        campaign_repository=campaign_repository,
        entity_repository=entity_repository,
        character_repository=character_repository,
    )

    data = CharacterCreate(
        name="Arannis",
        class_name="Fighter",
        max_hp=12,
    )

    character = service.create_character(
        campaign_id="campaign-1",
        data=data,
        activate=True,
    )

    active_id = campaign_repository.get_active_character_id(
        "campaign-1"
    )

    assert active_id == character.entity_id

def test_character_creation_rolls_back_on_failure(
    db,
    campaign_repository,
    entity_repository,
    character_repository,
):
    service = CharacterCreationService(
        db=db,
        campaign_repository=campaign_repository,
        entity_repository=entity_repository,
        character_repository=character_repository,
    )

    data = CharacterCreate(
        name="Arannis",
        class_name="Fighter",
        max_hp=12,
    )

    original_save_character = (
        character_repository.save_character
    )

    def failing_save_character(*args, **kwargs):
        raise RuntimeError("forced failure")

    character_repository.save_character = failing_save_character

    try:
        try:
            service.create_character(
                campaign_id="campaign-1",
                data=data,
                activate=True,
            )
        except RuntimeError:
            pass

        # Comprobar que no quedó Entity huérfana.
        entities = entity_repository.get_entities(
            entity_type="character"
        )

        assert not any(
            entity.name == "Arannis"
            for entity in entities
        )

    finally:
        character_repository.save_character = (
            original_save_character
        )