from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        max_length=200,
    )
    system: Optional[str] = Field(
        default=None,
        max_length=100,
    )
    tone: Optional[str] = Field(
        default=None,
        max_length=100,
    )
    summary: Optional[str] = Field(
        default=None,
        max_length=5000,
    )


class CampaignSessionUpdate(BaseModel):
    session_id: int | None = None


class SessionIn(BaseModel):
    number: int = Field(
        ...,
        ge=1,
    )
    title: str = Field(
        default="",
        max_length=200,
    )
    summary: str = Field(
        default="",
        max_length=5000,
    )
    start_location: str = Field(
        default="",
        max_length=200,
    )
    end_location: str = Field(
        default="",
        max_length=200,
    )
    notes: str = Field(
        default="",
        max_length=5000,
    )


class TurnIn(BaseModel):
    player_input: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    @field_validator("player_input")
    @classmethod
    def validate_player_input(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "player_input must not be empty"
            )

        return value


class ActiveCharacterUpdate(BaseModel):
    character_id: int | None = Field(
        default=None,
        ge=1,
    )

class SillyTavernContextIn(BaseModel):
    """
    Petición de contexto procedente de SillyTavern.

    query representa la acción o situación actual que el
    modelo va a utilizar para determinar qué recuerdos del
    mundo son relevantes.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    @field_validator("query")
    @classmethod
    def validate_query(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "query must not be empty"
            )

        return value


class SillyTavernTurnIn(BaseModel):
    """
    Turno ya generado por SillyTavern.

    Campaign Manager NO genera la narrativa en este endpoint.
    Recibe la acción del jugador y la narrativa resultante,
    extrae los cambios persistentes y los aplica al mundo.
    """

    player_input: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    narrative: str = Field(
        ...,
        min_length=1,
        max_length=30000,
    )

    @field_validator(
        "player_input",
        "narrative",
    )
    @classmethod
    def validate_text(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "text must not be empty"
            )

        return value