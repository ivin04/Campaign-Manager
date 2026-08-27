from __future__ import annotations

import json
from typing import Any, Callable

from models.world_state import WorldState
from operations.world_operations import WorldOperation


class LLMExtractionError(ValueError):
    """Error al interpretar una respuesta del LLM."""


class LLMWorldExtractor:
    """
    Responsabilidades:

    - Enviar texto + estado relevante al proveedor.
    - Parsear JSON.
    - Validar la estructura.
    - Convertir operaciones a WorldOperation.
    - No modificar WorldState.
    - No persistir nada.

    El proveedor se inyecta para poder probar todo sin necesitar
    un modelo real.
    """

    def __init__(
        self,
        provider: Callable[[str], str],
        operation_parser,
    ) -> None:
        if not callable(provider):
            raise TypeError(
                "provider must be callable"
            )

        if operation_parser is None:
            raise TypeError(
                "operation_parser is required"
            )

        self.provider = provider
        self.operation_parser = operation_parser

    def __call__(
        self,
        text: str,
        world: WorldState,
    ) -> list[WorldOperation]:
        return self.extract(
            text,
            world,
        )

    def extract(
        self,
        text: str,
        world: WorldState,
    ) -> list[WorldOperation]:
        if not isinstance(text, str):
            raise TypeError(
                "text must be a string"
            )

        if not isinstance(world, WorldState):
            raise TypeError(
                "world must be a WorldState"
            )

        text = text.strip()

        if not text:
            return []

        prompt = self._build_prompt(
            text,
            world,
        )

        raw_response = self.provider(
            prompt
        )

        payload = self._parse_response(
            raw_response
        )

        return self._parse_operations(
            payload
        )

    # ============================================================
    # PROMPT
    # ============================================================

    @staticmethod
    def _build_prompt(
        text: str,
        world: WorldState,
    ) -> str:
        """
        Construye un prompt determinista.

        El LLM NO debe inventar cambios persistentes
        que no estén respaldados por el texto.
        """

        return (
            "Eres un extractor de estado de un mundo de D&D.\n"
            "\n"
            "Tu tarea es detectar únicamente cambios persistentes "
            "descritos explícitamente en el texto.\n"
            "\n"
            "NO narres.\n"
            "NO expliques.\n"
            "NO inventes información.\n"
            "NO ejecutes operaciones.\n"
            "\n"
            "Devuelve exclusivamente JSON válido con esta forma:\n"
            '{\n'
            '  "operations": []\n'
            '}\n'
            "\n"
            "Texto narrativo:\n"
            f"{text}\n"
        )

    # ============================================================
    # RESPONSE PARSING
    # ============================================================

    @staticmethod
    def _parse_response(
        raw_response: Any,
    ) -> dict[str, Any]:
        if not isinstance(
            raw_response,
            str,
        ):
            raise LLMExtractionError(
                "LLM response must be a string"
            )

        response = raw_response.strip()

        if not response:
            raise LLMExtractionError(
                "LLM returned an empty response"
            )

        try:
            payload = json.loads(
                response
            )
        except json.JSONDecodeError as exc:
            raise LLMExtractionError(
                "LLM response is not valid JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise LLMExtractionError(
                "LLM response must be a JSON object"
            )

        operations = payload.get(
            "operations"
        )

        if operations is None:
            raise LLMExtractionError(
                "Missing 'operations' field"
            )

        if not isinstance(
            operations,
            list,
        ):
            raise LLMExtractionError(
                "'operations' must be a list"
            )

        return payload

    # ============================================================
    # OPERATION PARSING
    # ============================================================

    def _parse_operations(
        self,
        payload: dict[str, Any],
    ) -> list[WorldOperation]:
        try:
            operations = self.operation_parser.parse(
                payload
            )

        except Exception as exc:
            raise LLMExtractionError(
                "Failed to parse operations"
            ) from exc

        if not isinstance(
            operations,
            list,
        ):
            raise LLMExtractionError(
                "Operation parser returned "
                "an invalid result"
            )

        for index, operation in enumerate(
            operations
        ):
            if not isinstance(
                operation,
                WorldOperation,
            ):
                raise LLMExtractionError(
                    "Operation parser returned "
                    f"an invalid WorldOperation at index {index}"
                )

        return operations