from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

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

        item_lines = []

        for item_id, item in world.items.items():
            item_lines.append(
                f"- ID {item_id}: "
                f"{item.name}"
            )

        if item_lines:
            known_items = "\n".join(item_lines)
        else:
            known_items = "- Ninguno"


        item_instance_lines = []

        for instance_id, instance in world.item_instances.items():
            item = world.items.get(instance.item_id)

            item_name = (
                item.name
                if item is not None
                else f"Item {instance.item_id}"
            )

            item_instance_lines.append(
                f"- ID {instance_id}: "
                f"{item_name} "
                f"(instancia #{instance.instance_number}, "
                f"owner_id={instance.owner_id}, "
                f"location_id={instance.location_id}, "
                f"condition={instance.condition}, "
                f"active={instance.active})"
            )

        if item_instance_lines:
            known_item_instances = "\n".join(
                item_instance_lines
            )
        else:
            known_item_instances = "- Ninguna"

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
            "- Usa únicamente IDs que aparezcan en el contexto "
            "proporcionado por el backend.\n"
            "- NO inventes IDs.\n"
            "- entity_id identifica entidades.\n"
            "- item_id identifica definiciones de objetos.\n"
            "- instance_id identifica instancias físicas de objetos.\n"
            "- resource_id identifica recursos.\n"
            "- relation_id identifica relaciones existentes.\n"
            "- event_id identifica eventos históricos.\n"
            "- El personaje activo está marcado explícitamente.\n"
            "- Para change_character_hp utiliza el entity_id "
            "real del personaje correspondiente.\n"
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
            "1. CREAR ENTIDAD:\n"
            "{\n"
            '  "type": "create_entity",\n'
            '  "name": "Aldren",\n'
            '  "entity_type": "npc",\n'
            '  "description": "Propietario de la taberna.",\n'
            '  "notes": "Vive en Vorder\'s Hold.",\n'
            '  "active": true\n'
            "}\n"
            "\n"
            "Usa create_entity cuando aparezca una entidad "
            "nueva que deba formar parte del estado persistente "
            "del mundo.\n"
            "\n"

            "2. MODIFICAR ENTIDAD:\n"
            "{\n"
            '  "type": "update_entity",\n'
            '  "entity_id": 2,\n'
            '  "description": "Nueva información revelada.",\n'
            '  "notes": "Ahora sabemos que pertenece a la guardia."\n'
            "}\n"
            "\n"
            "Usa únicamente el ID de una entidad incluida en "
            "ENTIDADES CONOCIDAS.\n"
            "\n"

            "3. CREAR TIPO DE OBJETO:\n"
            "{\n"
            '  "type": "create_item",\n'
            '  "name": "Espada de hierro",\n'
            '  "description": "Una espada sencilla de hierro.",\n'
            '  "significance": "Arma común.",\n'
            '  "unique": false,\n'
            '  "notes": ""\n'
            "}\n"
            "\n"
            "create_item crea la definición del objeto, "
            "no una copia física concreta.\n"
            "\n"

            "4. CREAR INSTANCIA FÍSICA DE OBJETO:\n"
            "{\n"
            '  "type": "create_item_instance",\n'
            '  "item_id": 10,\n'
            '  "instance_number": 1,\n'
            '  "owner_id": 2,\n'
            '  "location_id": 3,\n'
            '  "condition": "intacto",\n'
            '  "notes": "Tiene una inscripción en la empuñadura.",\n'
            '  "active": true\n'
            "}\n"
            "\n"
            "create_item_instance crea una copia física concreta "
            "de un Item existente.\n"
            "\n"

            "IMPORTANTE: item_id debe corresponder a un Item "
            "existente. No inventes IDs.\n"
            "\n"

            "5. TRANSFERIR OBJETO:\n"
            "{\n"
            '  "type": "transfer_item",\n'
            '  "instance_id": 25,\n'
            '  "new_owner_id": 7\n'
            "}\n"
            "\n"
            "Usa transfer_item cuando una instancia física "
            "existente cambia de propietario.\n"
            "\n"

            "6. ACTUALIZAR INSTANCIA DE OBJETO:\n"
            "{\n"
            '  "type": "update_item_instance",\n'
            '  "instance_id": 25,\n'
            '  "condition": "dañado",\n'
            '  "notes": "La hoja tiene una grieta.",\n'
            '  "active": true\n'
            "}\n"
            "\n"
            "update_item_instance modifica únicamente los campos "
            "proporcionados de una instancia física existente.\n"
            "Los campos no proporcionados no deben modificarse.\n"
            "\n"
            "IMPORTANTE SOBRE INSTANCIAS FÍSICAS DE OBJETOS:\n"
            "- Las instancias físicas existentes aparecen en INSTANCIAS DE OBJETOS "
            "CONOCIDAS con su instance_id, item_id, owner_id y location_id.\n"
            "- Cuando la narrativa modifica una instancia física existente, "
            "debes generar una operación sobre ESA instancia.\n"
            "- No crees una nueva instancia si la narrativa se refiere a un objeto "
            "que ya aparece como instancia conocida.\n"
            "\n"
            "REGLA FUNDAMENTAL DE TRANSICIÓN DE ESTADO:\n"
            "- Compara el estado conocido de la instancia con lo que la narrativa "
            "confirma que ha ocurrido.\n"
            "- Si existe un cambio persistente confirmado, genera una operación "
            "que represente ese cambio.\n"
            "- No devuelvas una lista vacía simplemente porque la acción ya esté "
            "descrita en pasado en la narrativa.\n"
            "- Una acción como recoger, soltar, entregar, recibir, equipar, "
            "desequipar o mover una instancia debe producir una operación cuando "
            "cambie alguno de sus campos persistentes.\n"
            "\n"
            "REGLAS SOBRE owner_id:\n"
            "- Si una instancia existente no tiene propietario "
            "(owner_id=null) y la narrativa confirma que Darian u otra entidad "
            "pasa a poseerla, establece owner_id con el ID de esa entidad.\n"
            "- Si la narrativa confirma que una instancia deja de pertenecer "
            "a una entidad, usa owner_id=null.\n"
            "- Si la instancia ya pertenece al personaje y la narrativa solamente "
            "confirma que la recoge, no cambies owner_id innecesariamente.\n"
            "- No cambies el propietario solamente porque el personaje manipule "
            "físicamente el objeto.\n"
            "\n"
            "REGLAS SOBRE location_id:\n"
            "- Si la narrativa confirma que una instancia deja de estar en una "
            "ubicación identificable, usa location_id=null cuando no exista otra "
            "ubicación conocida que pueda utilizarse.\n"
            "- Si la narrativa confirma que una instancia pasa a una ubicación "
            "existente con ID conocido, usa ese location_id.\n"
            "- Si una superficie, mesa, suelo u otro lugar físico no tiene una "
            "entidad con ID conocido, NO inventes un location_id.\n"
            "- No cambies location_id simplemente porque el objeto haya sido "
            "mencionado en una localización narrativa que no puede representarse "
            "con un ID conocido.\n"
            "\n"
            "REGLAS PARA RECOGER OBJETOS:\n"
            "- Si la narrativa dice que una entidad recoge una instancia física "
            "existente y pasa a tenerla consigo, comprueba owner_id y genera "
            "update_item_instance si el propietario cambia.\n"
            "- Ejemplo: si la instancia 25 tiene owner_id=null y la narrativa dice "
            "\"Darian recoge la espada y se la guarda\", utiliza:\n"
            "{\n"
            '  \"type\": \"update_item_instance\",\n'
            '  \"instance_id\": 25,\n'
            '  \"owner_id\": ID_DE_DARIAN\n'
            "}\n"
            "- Si la instancia ya pertenece a Darian, no generes una operación "
            "de propietario redundante.\n"
            "- Si además existe un cambio persistente de ubicación representable "
            "con un ID conocido, registra también ese cambio.\n"
            "\n"
            "REGLAS PARA SOLTAR O DEJAR OBJETOS:\n"
            "- Si la narrativa confirma que una entidad deja de llevar consigo "
            "una instancia, elimina owner_id usando null cuando corresponda.\n"
            "- Si además pasa a una ubicación conocida, establece location_id "
            "con el ID correspondiente.\n"
            "- Si la nueva ubicación no puede representarse con una entidad "
            "conocida, no inventes un location_id.\n"
            "\n"
            "IMPORTANTE SOBRE CAMPOS OPCIONALES:\n"
            "- Campo omitido = no modificar ese campo.\n"
            "- Campo con valor null = borrar explícitamente ese valor.\n"
            "- Nunca uses null para representar un campo que simplemente "
            "desconoces.\n"
            "- Nunca inventes IDs.\n"
            "\n"
            "Ejemplos conceptuales:\n"
            "- \"Darian entrega la espada a Neria\" -> transfer_item con "
            "instance_id de la espada y new_owner_id=ID de Neria.\n"
            "- \"Darian recoge la espada del suelo\" -> update_item_instance "
            "con instance_id de la espada y owner_id=ID de Darian si la instancia "
            "no tenía propietario.\n"
            "- \"Darian deja la espada\" -> elimina owner_id con null si deja "
            "de ser de su propiedad.\n"
            "- \"Darian deja la espada sobre la mesa\" -> si la mesa no tiene "
            "ID conocido, no inventes location_id; modifica únicamente los campos "
            "cuyo cambio persistente pueda representarse de forma segura.\n"
            "- \"Darian vuelve a recoger la espada\" -> si la instancia conocida "
            "había quedado sin propietario y ahora Darian vuelve a poseerla, "
            "restaura owner_id=ID de Darian.\n"

            "7. CREAR RECURSO:\n"
            "{\n"
            '  "type": "create_resource",\n'
            '  "name": "Oro",\n'
            '  "resource_type": "currency",\n'
            '  "unit": "gp",\n'
            '  "notes": ""\n'
            "}\n"
            "\n"

            "8. OBTENER RECURSO:\n"
            "{\n"
            '  "type": "gain_resource",\n'
            '  "resource_id": 10,\n'
            '  "owner_id": 2,\n'
            '  "amount": 50\n'
            "}\n"
            "\n"
            "Usa gain_resource cuando una entidad recibe "
            "una cantidad de un recurso.\n"
            "\n"

            "9. GASTAR RECURSO:\n"
            "{\n"
            '  "type": "spend_resource",\n'
            '  "resource_id": 10,\n'
            '  "owner_id": 2,\n'
            '  "amount": 20\n'
            "}\n"
            "\n"
            "Usa spend_resource cuando una entidad pierde "
            "una cantidad de un recurso como consecuencia "
            "de un hecho confirmado.\n"
            "\n"

            "10. TRANSFERIR RECURSO:\n"
            "{\n"
            '  "type": "transfer_resource",\n'
            '  "resource_id": 10,\n'
            '  "subject_id": 2,\n'
            '  "target_id": 7,\n'
            '  "amount": 15\n'
            "}\n"
            "\n"

            "11. CREAR RELACIÓN:\n"
            "{\n"
            '  "type": "create_relation",\n'
            '  "relation_id": "aldren_guardia",\n'
            '  "subject_id": 2,\n'
            '  "relation_type": "miembro_de",\n'
            '  "target_id": 7,\n'
            '  "metadata": {}\n'
            "}\n"
            "\n"

            "12. MODIFICAR RELACIÓN:\n"
            "{\n"
            '  "type": "update_relation",\n'
            '  "relation_id": "aldren_guardia",\n'
            '  "relation_type": "aliado_de",\n'
            '  "target_id": 7,\n'
            '  "metadata": {},\n'
            '  "active": true\n'
            "}\n"
            "\n"

            "13. ELIMINAR RELACIÓN:\n"
            "{\n"
            '  "type": "remove_relation",\n'
            '  "relation_id": "aldren_guardia"\n'
            "}\n"
            "\n"
            "remove_relation no borra físicamente la relación. "
            "La desactiva.\n"
            "\n"

            "14. CREAR EVENTO:\n"
            "{\n"
            '  "type": "create_event",\n'
            '  "event_id": "puerta_cripta_abierta",\n'
            '  "event_type": "world_event",\n'
            '  "title": "La puerta de la cripta se abre",\n'
            '  "description": "La antigua puerta fue abierta.",\n'
            '  "consequences": "La cripta vuelve a ser accesible.",\n'
            '  "session_id": 1,\n'
            '  "secret": false,\n'
            '  "metadata": {}\n'
            "}\n"
            "\n"

            "15. CAMBIAR HP:\n"
            "{\n"
            '  "type": "change_character_hp",\n'
            '  "entity_id": 1,\n'
            '  "amount": -5\n'
            "}\n"
            "\n"
            "Usa change_character_hp únicamente cuando el "
            "daño o la curación hayan ocurrido realmente "
            "en la narrativa.\n"
            "\n"
            "REGLA GENERAL:\n"
            "Cada operación debe representar un hecho que haya "
            "ocurrido realmente o que haya sido revelado "
            "explícitamente en la narrativa.\n"
            "No conviertas intenciones, posibilidades, amenazas "
            "o acciones hipotéticas en cambios persistentes.\n"
            "\n"
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
            "ITEMS CONOCIDOS:\n"
            f"{known_items}\n"
            "\n"
            "INSTANCIAS DE ITEMS CONOCIDAS:\n"
            f"{known_item_instances}\n"
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