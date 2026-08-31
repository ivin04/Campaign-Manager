from __future__ import annotations

import json
from typing import Any, Callable

from models.turn_context import TurnContext
from operations.turn_operations import TurnOperation


class LLMExtractionError(ValueError):
    """Error al interpretar una respuesta del LLM."""


class LLMWorldExtractor:
    """
    Extrae operaciones persistentes a partir de la narrativa generada
    por el DM.

    El extractor:
        - recibe narrativa + TurnContext
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
        context: TurnContext,
    ) -> list[TurnOperation]:
        return self.extract(
            text,
            context,
        )

    def extract(
        self,
        text: str,
        context: TurnContext,
    ) -> list[TurnOperation]:
        if not isinstance(text, str):
            raise TypeError(
                "text must be a string"
            )

        if not isinstance(context, TurnContext):
            raise TypeError(
                "context must be a TurnContext"
            )

        text = text.strip()

        if not text:
            return []

        prompt = self._build_prompt(
            text,
            context,
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
        context: TurnContext,
    ) -> str:
        """
        Construye un prompt determinista para extraer cambios
        persistentes del turno.

        El LLM no debe ejecutar operaciones ni inventar IDs.
        """

        world = context.world

        entity_lines = []

        for entity_id, entity in world.entities.items():
            marker = ""

            if (
                context.active_character is not None
                and entity_id
                == context.active_character.entity_id
            ):
                marker = " [PERSONAJE ACTIVO]"

            entity_lines.append(
                f"- ID {entity_id}: "
                f"{entity.name} "
                f"({entity.entity_type})"
                f"{marker}"
            )

        if entity_lines:
            known_entities = "\n".join(
                entity_lines
            )
        else:
            known_entities = "- Ninguna"

        active_character = (
            context.active_character
        )

        if active_character is None:
            character_block = (
                "No hay personaje activo."
            )
        else:
            character_block = (
                f"ID de entidad: "
                f"{active_character.entity_id}\n"
                f"Nivel: "
                f"{active_character.level}\n"
                f"Clase: "
                f"{active_character.class_name}\n"
                f"HP actual: "
                f"{active_character.current_hp}\n"
                f"HP máximo: "
                f"{active_character.max_hp}\n"
                f"CA: "
                f"{active_character.armor_class}\n"
                f"FUE: "
                f"{active_character.strength}\n"
                f"DES: "
                f"{active_character.dexterity}\n"
                f"CON: "
                f"{active_character.constitution}\n"
                f"INT: "
                f"{active_character.intelligence}\n"
                f"SAB: "
                f"{active_character.wisdom}\n"
                f"CAR: "
                f"{active_character.charisma}\n"
                f"Competencia: "
                f"{active_character.proficiency_bonus}"
            )

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
            "REGLAS DE IDENTIFICADORES:\n"
            "- Usa únicamente IDs que aparezcan en el contexto.\n"
            "- NO inventes IDs.\n"
            "- El personaje activo está marcado explícitamente.\n"
            "- Para cambiar HP del personaje activo usa su "
            "entity_id real.\n"
            "\n"
            "IMPORTANTE:\n"
            "- Solo crea una operación si el cambio está "
            "explícitamente descrito en la narrativa.\n"
            "- No deduzcas daño, curación, objetos, recursos o "
            "relaciones que no estén descritos.\n"
            "- No conviertas intención narrativa en cambio "
            "persistente si el texto no confirma que ocurrió.\n"
            "\n"
            "PERSONAJE ACTIVO:\n"
            f"{character_block}\n"
            "\n"
            "ENTIDADES CONOCIDAS:\n"
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

        # Algunos modelos devuelven el JSON dentro de un
        # bloque Markdown. Aceptamos tanto JSON puro como:
        #
        # ```json
        # {
        #   "operations": []
        # }
        # ```
        #
        # El contenido sigue teniendo que ser JSON válido.

        if response.startswith("```"):
            lines = response.splitlines()

            if (
                len(lines) >= 2
                and lines[-1].strip() == "```"
            ):
                response = "\n".join(
                    lines[1:-1]
                ).strip()

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