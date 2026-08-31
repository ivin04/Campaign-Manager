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

        El LLM interpreta únicamente hechos explícitos.
        Los IDs solo pueden utilizarse para entidades ya existentes.
        Las entidades nuevas se crean sin ID.
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
            "Eres un extractor de estado persistente "
            "de un mundo de D&D.\n"
            "\n"
            "Tu tarea es convertir únicamente hechos "
            "explícitamente confirmados en la narrativa "
            "en operaciones estructuradas.\n"
            "\n"
            "NO narres.\n"
            "NO expliques.\n"
            "NO añadas texto fuera del JSON.\n"
            "NO inventes hechos.\n"
            "NO ejecutes operaciones.\n"
            "\n"
            "Solo registra información que haya ocurrido "
            "o haya sido revelada explícitamente en la "
            "narrativa.\n"
            "\n"
            "CUÁNDO CREAR UNA ENTIDAD NUEVA:\n"
            "- Si aparece por primera vez una persona, NPC, "
            "criatura, lugar u otra entidad identificable "
            "por un nombre explícito y la narrativa revela "
            "información útil para el estado del mundo, "
            "puedes usar create_entity.\n"
            "- create_entity NO recibe entity_id.\n"
            "- El ID de una entidad nueva lo genera el backend.\n"
            "- No uses create_entity para una entidad que "
            "ya aparezca en ENTIDADES CONOCIDAS.\n"
            "\n"
            "REGLAS DE IDENTIFICADORES:\n"
            "- Para modificar una entidad existente usa "
            "únicamente su ID mostrado en ENTIDADES CONOCIDAS.\n"
            "- NO inventes IDs.\n"
            "- El personaje activo está marcado explícitamente.\n"
            "- Para change_character_hp usa el entity_id real "
            "del personaje correspondiente.\n"
            "\n"
            "IMPORTANTE:\n"
            "- Solo crea una operación si el hecho está "
            "explícitamente descrito en la narrativa.\n"
            "- No deduzcas daño, curación, objetos, recursos "
            "o relaciones que no estén confirmados.\n"
            "- No conviertas una intención en un cambio "
            "persistente si la narrativa no confirma "
            "que ocurrió.\n"
            "- Si no existe ningún cambio persistente, "
            "devuelve una lista de operaciones vacía.\n"
            "\n"
            "OPERACIONES DISPONIBLES:\n"
            "\n"
            "Crear entidad nueva:\n"
            "{\n"
            '  "type": "create_entity",\n'
            '  "name": "Aldren",\n'
            '  "entity_type": "npc",\n'
            '  "description": "Propietario de la taberna."\n'
            "}\n"
            "\n"
            "Modificar entidad existente:\n"
            "{\n"
            '  "type": "update_entity",\n'
            '  "entity_id": 2,\n'
            '  "description": "Nueva información '
            'explícitamente revelada."\n'
            "}\n"
            "\n"
            "Cambiar HP de un personaje:\n"
            "{\n"
            '  "type": "change_character_hp",\n'
            '  "entity_id": 1,\n'
            '  "amount": -5\n'
            "}\n"
            "\n"
            "FORMATO DE RESPUESTA:\n"
            "Devuelve exclusivamente un objeto JSON válido "
            "con esta estructura:\n"
            "{\n"
            '  "operations": [\n'
            "    {\n"
            '      "type": "create_entity",\n'
            '      "name": "Aldren",\n'
            '      "entity_type": "npc",\n'
            '      "description": "Propietario de la taberna."\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "\n"
            "Si no hay ningún cambio persistente:\n"
            "{\n"
            '  "operations": []\n'
            "}\n"
            "\n"
            "PERSONAJE ACTIVO:\n"
            f"{character_block}\n"
            "\n"
            "ENTIDADES CONOCIDAS:\n"
            f"{known_entities}\n"
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