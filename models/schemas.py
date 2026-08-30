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