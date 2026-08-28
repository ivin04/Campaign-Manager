from __future__ import annotations

import json
from typing import Any, Callable

from models.world_state import WorldState
from operations.turn_operations import TurnOperation


class LLMExtractionError(ValueError):
    """Error al interpretar una respuesta del LLM."""


class LLMWorldExtractor:
    """
    Extrae operaciones persistentes a partir de la narrativa generada
    por el DM.

    El extractor:
        - recibe narrativa + WorldState
        - construye el prompt
        - consulta al proveedor LLM
        - parsea el JSON
        - delega la conversión de operaciones al OperationParser
        - valida el resultado

    El extractor NO:
        - modifica el mundo
        - persiste datos
        - aplica operaciones
        - implementa reglas de dominio
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
    ) -> list[TurnOperation]:
        return self.extract(
            text,
            world,
        )

    def extract(
        self,
        text: str,
        world: WorldState,
    ) -> list[TurnOperation]:
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
        Construye un prompt determinista para extraer cambios
        persistentes del turno.

        El LLM no debe ejecutar operaciones ni inventar IDs.
        """

        entity_lines = []

        for entity_id, entity in world.entities.items():
            entity_lines.append(
                f"- ID {entity_id}: "
                f"{entity.name} "
                f"({entity.entity_type})"
            )

        if entity_lines:
            known_entities = "\n".join(
                entity_lines
            )
        else:
            known_entities = "- Ninguna"

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
            "Puedes devolver operaciones de mundo o de personaje.\n"
            "\n"
            "Cuando una operación necesite un entity_id, "
            "usa únicamente los IDs de las entidades conocidas "
            "que aparecen abajo.\n"
            "\n"
            "NO inventes IDs.\n"
            "\n"
            "Entidades conocidas:\n"
            f"{known_entities}\n"
            "\n"
            "Devuelve exclusivamente JSON válido con esta forma:\n"
            "{\n"
            '  "operations": []\n'
            "}\n"
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
    ) -> list[TurnOperation]:
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
                TurnOperation,
            ):
                raise LLMExtractionError(
                    "Operation parser returned "
                    f"an invalid TurnOperation at index {index}"
                )

        return operations