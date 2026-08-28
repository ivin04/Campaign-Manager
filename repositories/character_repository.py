import json

from database import execute, one, rows
from models.character_state import CharacterState


class CharacterRepository:

    def get_character(
        self,
        entity_id: int,
        *,
        conn=None,
    ) -> CharacterState | None:

        if conn is None:
            row = one(
                """
                SELECT
                    entity_id,
                    level,
                    class_name,
                    current_hp,
                    max_hp,
                    armor_class,
                    strength,
                    dexterity,
                    constitution,
                    intelligence,
                    wisdom,
                    charisma,
                    proficiency_bonus,
                    metadata
                FROM character_states
                WHERE entity_id=?
                """,
                (entity_id,),
            )

        else:
            row = conn.execute(
                """
                SELECT
                    entity_id,
                    level,
                    class_name,
                    current_hp,
                    max_hp,
                    armor_class,
                    strength,
                    dexterity,
                    constitution,
                    intelligence,
                    wisdom,
                    charisma,
                    proficiency_bonus,
                    metadata
                FROM character_states
                WHERE entity_id=?
                """,
                (entity_id,),
            ).fetchone()

            row = dict(row) if row else None

        if row is None:
            return None

        return self._row_to_model(row)

    def save_character(
        self,
        character: CharacterState,
        *,
        conn=None,
    ) -> CharacterState:

        query = """
            INSERT INTO character_states (
                entity_id,
                level,
                class_name,
                current_hp,
                max_hp,
                armor_class,
                strength,
                dexterity,
                constitution,
                intelligence,
                wisdom,
                charisma,
                proficiency_bonus,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id)
            DO UPDATE SET
                level=excluded.level,
                class_name=excluded.class_name,
                current_hp=excluded.current_hp,
                max_hp=excluded.max_hp,
                armor_class=excluded.armor_class,
                strength=excluded.strength,
                dexterity=excluded.dexterity,
                constitution=excluded.constitution,
                intelligence=excluded.intelligence,
                wisdom=excluded.wisdom,
                charisma=excluded.charisma,
                proficiency_bonus=excluded.proficiency_bonus,
                metadata=excluded.metadata
        """

        params = (
            character.entity_id,
            character.level,
            character.class_name,
            character.current_hp,
            character.max_hp,
            character.armor_class,
            character.strength,
            character.dexterity,
            character.constitution,
            character.intelligence,
            character.wisdom,
            character.charisma,
            character.proficiency_bonus,
            json.dumps(character.metadata),
        )

        if conn is None:
            execute(
                query,
                params,
            )
        else:
            conn.execute(
                query,
                params,
            )

        loaded = self.get_character(
            character.entity_id,
            conn=conn,
        )

        if loaded is None:
            raise RuntimeError(
                f"Character {character.entity_id} "
                "could not be loaded after save"
            )

        return loaded

    def delete_character(
        self,
        entity_id: int,
    ) -> None:

        execute(
            """
            DELETE FROM character_states
            WHERE entity_id=?
            """,
            (entity_id,),
        )

    def list_characters(self) -> list[CharacterState]:

        rows_data = rows(
            """
            SELECT
                entity_id,
                level,
                class_name,
                current_hp,
                max_hp,
                armor_class,
                strength,
                dexterity,
                constitution,
                intelligence,
                wisdom,
                charisma,
                proficiency_bonus,
                metadata
            FROM character_states
            ORDER BY entity_id
            """
        )

        return [
            self._row_to_model(row)
            for row in rows_data
        ]

    @staticmethod
    def _row_to_model(row) -> CharacterState:

        metadata = row["metadata"]

        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return CharacterState(
            entity_id=row["entity_id"],
            level=row["level"],
            class_name=row["class_name"],
            current_hp=row["current_hp"],
            max_hp=row["max_hp"],
            armor_class=row["armor_class"],
            strength=row["strength"],
            dexterity=row["dexterity"],
            constitution=row["constitution"],
            intelligence=row["intelligence"],
            wisdom=row["wisdom"],
            charisma=row["charisma"],
            proficiency_bonus=row["proficiency_bonus"],
            metadata=metadata,
        )