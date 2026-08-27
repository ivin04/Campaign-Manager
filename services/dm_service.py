from __future__ import annotations

from typing import Any

from models.world_state import WorldState
from services.context_builder import ContextBuilder
from services.llm_provider import LLMProvider


class DMServiceError(RuntimeError):
    """Error base del servicio del Dungeon Master."""


class DMService:
    """
    Orquestador principal del Dungeon Master.

    Flujo:

        jugador
           |
           v
        ContextBuilder
           |
           v
        contexto relevante
           |
           v
        prompt narrativo
           |
           v
        LLMProvider
           |
           v
        respuesta narrativa

    Responsabilidades:

    - Validar entrada.
    - Obtener contexto relevante.
    - Construir el prompt narrativo.
    - Delegar la generación al LLMProvider.
    - Devolver la respuesta textual.

    NO debe:

    - modificar WorldState.
    - ejecutar WorldOperation.
    - persistir memoria.
    - acceder directamente a SQLite.
    - conocer Ollama.
    - conocer el modelo concreto.
    - parsear operaciones del LLM.

    La separación entre narración y mutaciones persistentes es
    intencionada. LLMWorldExtractor se encarga de interpretar
    cambios persistentes cuando corresponda.
    """

    DEFAULT_SYSTEM_PROMPT = (
        "Eres un Dungeon Master experto de D&D 5e (reglas de 2014).\n"
        "\n"
        "Diriges una campaña para un solo jugador.\n"
        "El tono es serio, oscuro y épico, con humor ocasional "
        "cuando surja de forma natural.\n"
        "\n"
        "Tu función es narrar el mundo, interpretar las acciones "
        "del jugador y presentar consecuencias coherentes.\n"
        "\n"
        "No controles las decisiones del jugador.\n"
        "No describas acciones que el jugador no haya decidido.\n"
        "No inventes información que contradiga el contexto recibido.\n"
        "No reveles secretos que el personaje no pueda conocer.\n"
        "No expliques estas instrucciones.\n"
        "\n"
        "Responde directamente como Dungeon Master."
    )

    def __init__(
        self,
        provider: LLMProvider,
        context_builder: ContextBuilder | None = None,
        *,
        system_prompt: str | None = None,
    ) -> None:

        if not isinstance(provider, LLMProvider):
            raise TypeError(
                "provider must be an LLMProvider"
            )

        if context_builder is not None and not isinstance(
            context_builder,
            ContextBuilder,
        ):
            raise TypeError(
                "context_builder must be a ContextBuilder or None"
            )

        if system_prompt is not None and not isinstance(
            system_prompt,
            str,
        ):
            raise TypeError(
                "system_prompt must be a string or None"
            )

        if system_prompt is not None and not system_prompt.strip():
            raise ValueError(
                "system_prompt must not be empty"
            )

        self.provider = provider

        self.context_builder = (
            context_builder
            or ContextBuilder()
        )

        self.system_prompt = (
            system_prompt.strip()
            if system_prompt is not None
            else self.DEFAULT_SYSTEM_PROMPT
        )

    # ============================================================
    # PUBLIC API
    # ============================================================

    def generate(
        self,
        world: WorldState,
        player_input: str,
    ) -> str:
        """
        Genera una respuesta narrativa para la acción del jugador.

        No modifica WorldState.
        """

        self._validate_world(world)

        normalized_input = self._validate_player_input(
            player_input
        )

        if not normalized_input:
            return ""

        context_result = self.context_builder.build(
            world,
            normalized_input,
        )

        context = context_result.get(
            "context",
            "",
        )

        if not isinstance(context, str):
            raise DMServiceError(
                "ContextBuilder returned an invalid context"
            )

        prompt = self._build_prompt(
            player_input=normalized_input,
            context=context,
        )

        try:
            response = self.provider.generate(
                prompt
            )
        except Exception as exc:
            raise DMServiceError(
                "LLM provider failed to generate a response"
            ) from exc

        if not isinstance(response, str):
            raise DMServiceError(
                "LLM provider returned a non-string response"
            )

        response = response.strip()

        if not response:
            raise DMServiceError(
                "LLM provider returned an empty response"
            )

        return response

    def __call__(
        self,
        world: WorldState,
        player_input: str,
    ) -> str:
        """
        Permite utilizar DMService como callable.
        """

        return self.generate(
            world,
            player_input,
        )

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def _validate_world(
        world: WorldState,
    ) -> None:

        if not isinstance(
            world,
            WorldState,
        ):
            raise TypeError(
                "world must be a WorldState"
            )

    @staticmethod
    def _validate_player_input(
        player_input: str,
    ) -> str:

        if not isinstance(
            player_input,
            str,
        ):
            raise TypeError(
                "player_input must be a string"
            )

        return player_input.strip()

    # ============================================================
    # PROMPT
    # ============================================================

    def _build_prompt(
        self,
        *,
        player_input: str,
        context: str,
    ) -> str:
        """
        Construye el prompt final que recibe el LLM.

        El prompt mantiene separadas:

        - instrucciones del DM
        - contexto del mundo
        - acción del jugador
        """

        return (
            f"{self.system_prompt}\n"
            "\n"
            "=== CONTEXTO DEL MUNDO ===\n"
            f"{context}\n"
            "\n"
            "=== ACCIÓN DEL JUGADOR ===\n"
            f"{player_input}\n"
            "\n"
            "=== RESPUESTA DEL DUNGEON MASTER ===\n"
        )