from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from models.turn_context import TurnContext
from operations.character_operations import CharacterOperation
from operations.turn_operations import TurnOperation
from operations.world_operations import WorldOperation


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
        Construye el prompt para extraer cambios persistentes
        del turno a partir de hechos explícitos de la narrativa.
        """

        world = context.world

        # ------------------------------------------------------------
        # ENTIDADES CONOCIDAS
        # ------------------------------------------------------------

        entity_lines = []

        for entity_id, entity in world.entities.items():
            marker = ""

            if (
                context.active_character is not None
                and entity_id == context.active_character.entity_id
            ):
                marker = " [PERSONAJE ACTIVO]"

            entity_lines.append(
                f"- ID {entity_id}: "
                f"{entity.name} "
                f"({entity.entity_type})"
                f"{marker}"
            )

        known_entities = (
            "\n".join(entity_lines)
            if entity_lines
            else "- Ninguna"
        )

        # ------------------------------------------------------------
        # ITEMS CONOCIDOS
        # ------------------------------------------------------------

        item_lines = []

        for item_id, item in world.items.items():
            item_lines.append(
                f"- ID {item_id}: "
                f"{item.name}"
            )

        known_items = (
            "\n".join(item_lines)
            if item_lines
            else "- Ninguno"
        )

        # ------------------------------------------------------------
        # INSTANCIAS FÍSICAS CONOCIDAS
        # ------------------------------------------------------------

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
                f"(item_id={instance.item_id}, "
                f"instance_number={instance.instance_number}, "
                f"owner_id={instance.owner_id}, "
                f"location_id={instance.location_id}, "
                f"condition={instance.condition}, "
                f"active={instance.active})"
            )

        known_item_instances = (
            "\n".join(item_instance_lines)
            if item_instance_lines
            else "- Ninguna"
        )

        # ------------------------------------------------------------
        # RECURSOS CONOCIDOS
        # ------------------------------------------------------------

        resource_lines = []

        for resource_id, resource in world.resources.items():
            resource_lines.append(
                f"- ID {resource_id}: "
                f"{resource.name} "
                f"(tipo={resource.resource_type}, "
                f"unidad={resource.unit})"
            )

        known_resources = (
            "\n".join(resource_lines)
            if resource_lines
            else "- Ninguno"
        )

        # ------------------------------------------------------------
        # RELACIONES CONOCIDAS
        # ------------------------------------------------------------

        relation_lines = []

        for relation_id, relation in world.relations.items():
            subject = world.entities.get(
                relation.subject_id
            )
            target = world.entities.get(
                relation.target_id
            )

            subject_name = (
                subject.name
                if subject is not None
                else f"Entidad {relation.subject_id}"
            )

            target_name = (
                target.name
                if target is not None
                else f"Entidad {relation.target_id}"
            )

            relation_lines.append(
                f"- ID {relation_id}: "
                f"{subject_name} "
                f"(ID {relation.subject_id}) "
                f"--[{relation.relation_type}]--> "
                f"{target_name} "
                f"(ID {relation.target_id}), "
                f"active={relation.active}, "
                f"metadata={relation.metadata}"
            )

        known_relations = (
            "\n".join(relation_lines)
            if relation_lines
            else "- Ninguna"
        )

        # ------------------------------------------------------------
        # EVENTOS CONOCIDOS
        # ------------------------------------------------------------

        event_lines = []

        for event_id, event in world.events.items():
            event_lines.append(
                f"- ID {event_id}: "
                f"type={event.event_type}, "
                f"title={event.title}, "
                f"description={event.description}, "
                f"consequences={event.consequences}, "
                f"session_id={event.session_id}, "
                f"secret={event.secret}, "
                f"metadata={event.metadata}"
            )

        known_events = (
            "\n".join(event_lines)
            if event_lines
            else "- Ninguno"
        )

        # ------------------------------------------------------------
        # PERSONAJE ACTIVO
        # ------------------------------------------------------------

        active_character = context.active_character

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
            "para un mundo de D&D 5e (2014).\n"
            "\n"

            "TU ÚNICA FUNCIÓN:\n"
            "Analizar la narrativa proporcionada y convertir "
            "ÚNICAMENTE hechos explícitamente ocurridos o "
            "información explícitamente revelada en operaciones "
            "estructuradas de persistencia.\n"
            "\n"

            "NO eres el Dungeon Master.\n"
            "NO continúes la historia.\n"
            "NO inventes información.\n"
            "NO interpretes intenciones como hechos.\n"
            "NO hagas tiradas.\n"
            "NO calcules resultados que no aparezcan en la narrativa.\n"
            "NO ejecutes operaciones.\n"
            "NO expliques tus decisiones.\n"
            "NO escribas texto fuera del JSON final.\n"
            "\n"

            "Tu trabajo consiste exclusivamente en responder:\n"
            "\"¿Qué hechos persistentes nuevos o cambios de estado "
            "han quedado confirmados por esta narrativa?\"\n"
            "\n"

            "============================================================\n"
            "REGLAS FUNDAMENTALES\n"
            "============================================================\n"
            "\n"

            "1. SOLO HECHOS CONFIRMADOS\n"
            "- Crea una operación únicamente si la narrativa confirma "
            "que algo ocurrió o que una información quedó establecida.\n"
            "- No conviertas intenciones, deseos, planes, amenazas, "
            "posibilidades, rumores no confirmados o acciones hipotéticas "
            "en cambios persistentes.\n"
            "- \"Va a atacar\" NO significa que haya atacado.\n"
            "- \"Intenta abrir la puerta\" NO significa necesariamente "
            "que la puerta se haya abierto.\n"
            "- \"Quizá sea un espía\" NO crea una relación de espionaje.\n"
            "- \"Podría haber una trampa\" NO crea un evento de trampa.\n"
            "\n"

            "2. CAMBIOS REALES DE ESTADO\n"
            "Si una acción confirmada modifica el estado persistente "
            "del mundo, debes registrarla.\n"
            "\n"
            "Ejemplos:\n"
            "- Un personaje recibe daño -> change_character_hp.\n"
            "- Un personaje es curado -> change_character_hp.\n"
            "- Aparece un NPC nuevo con nombre e información relevante "
            "-> create_entity.\n"
            "- Se descubre información nueva sobre un NPC existente "
            "-> update_entity.\n"
            "- Se recoge un objeto físico existente -> modificar "
            "su instancia si cambia su propietario.\n"
            "- Se entrega un objeto a otra entidad -> transfer_item.\n"
            "- Dos personajes establecen una relación persistente "
            "explícitamente -> create_relation.\n"
            "- Una relación existente cambia explícitamente "
            "-> update_relation.\n"
            "- Una relación deja de existir -> remove_relation.\n"
            "- Ocurre un acontecimiento histórico relevante para "
            "el mundo -> create_event.\n"
            "\n"

            "3. NO DUPLICAR INFORMACIÓN\n"
            "- Antes de crear algo nuevo, comprueba las listas "
            "de elementos conocidos.\n"
            "- Si una entidad ya existe, utiliza su ID.\n"
            "- Si una relación ya existe, actualízala en lugar de crear "
            "otra relación equivalente.\n"
            "- Si un evento ya existe y la narrativa simplemente vuelve "
            "a mencionarlo, NO lo dupliques.\n"
            "- Si una instancia física ya existe, actualiza esa instancia "
            "en lugar de crear otra.\n"
            "\n"

            "4. IDENTIFICADORES\n"
            "- NO inventes IDs numéricos.\n"
            "- NO inventes IDs de entidades.\n"
            "- NO inventes item_id.\n"
            "- NO inventes instance_id.\n"
            "- NO inventes resource_id.\n"
            "- NO inventes relation_id para actualizar o eliminar "
            "una relación existente.\n"
            "- NO inventes event_id para actualizar información existente.\n"
            "- Los IDs de entidades, items, instancias y recursos "
            "deben proceder del contexto.\n"
            "- Las relaciones y eventos nuevos sí necesitan un identificador "
            "estable generado por ti, pero ese identificador debe ser "
            "descriptivo, determinista y único dentro del mundo.\n"
            "\n"

            "Ejemplos válidos de IDs nuevos:\n"
            "- \"aldren_guardia_ciudad\"\n"
            "- \"edrik_debe_dinero_a_aldren\"\n"
            "- \"cripta_puerta_abierta\"\n"
            "- \"explorador_muerto_cripta\"\n"
            "\n"

            "No utilices IDs aleatorios ni IDs numéricos para relaciones "
            "o eventos nuevos.\n"
            "\n"

            "5. PERSONAJE ACTIVO\n"
            "- El personaje marcado como [PERSONAJE ACTIVO] es el personaje "
            "jugador actual.\n"
            "- No asumas un nombre concreto para él.\n"
            "- Nunca utilices nombres ficticios como \"Darian\" salvo que "
            "ese nombre aparezca realmente en el contexto o la narrativa.\n"
            "- Cuando la narrativa diga \"el personaje\", \"el aventurero\", "
            "\"el jugador\" o equivalente y exista un personaje activo, "
            "utiliza su entity_id.\n"
            "- Para change_character_hp utiliza el entity_id real del "
            "personaje activo o del personaje afectado.\n"
            "\n"

            "============================================================\n"
            "ENTIDADES\n"
            "============================================================\n"
            "\n"

            "CREAR ENTIDAD:\n"
            "{\n"
            '  "type": "create_entity",\n'
            '  "name": "Aldren",\n'
            '  "entity_type": "npc",\n'
            '  "description": "Propietario de la taberna.",\n'
            "  \"notes\": \"Vive en Vorder's Hold.\",\n"
            '  "active": true\n'
            "}\n"
            "\n"

            "Usa create_entity cuando aparezca una entidad nueva "
            "identificable y la narrativa aporte información que "
            "merezca formar parte del estado persistente.\n"
            "\n"

            "No crees entidades para referencias genéricas sin identidad "
            "útil, como \"un hombre\", \"una sombra\" o \"unos guardias\", "
            "salvo que la narrativa establezca que esa entidad concreta "
            "tiene relevancia persistente.\n"
            "\n"

            "MODIFICAR ENTIDAD:\n"
            "{\n"
            '  "type": "update_entity",\n'
            '  "entity_id": 2,\n'
            '  "description": "Nueva información revelada.",\n'
            '  "notes": "Ahora sabemos que pertenece a la guardia."\n'
            "}\n"
            "\n"

            "Usa únicamente el entity_id de ENTIDADES CONOCIDAS.\n"
            "Solo proporciona los campos que deban cambiar.\n"
            "\n"

            "============================================================\n"
            "OBJETOS E INSTANCIAS FÍSICAS\n"
            "============================================================\n"
            "\n"

            "Un ITEM es una definición de objeto.\n"
            "Una ITEM INSTANCE es una copia física concreta.\n"
            "\n"

            "CREAR ITEM:\n"
            "{\n"
            '  "type": "create_item",\n'
            '  "name": "Espada de hierro",\n'
            '  "description": "Una espada sencilla de hierro.",\n'
            '  "significance": "Arma común.",\n'
            '  "unique": false,\n'
            '  "notes": ""\n'
            "}\n"
            "\n"

            "CREAR INSTANCIA:\n"
            "{\n"
            '  "type": "create_item_instance",\n'
            '  "item_id": 10,\n'
            '  "instance_number": 1,\n'
            '  "owner_id": null,\n'
            '  "location_id": 3,\n'
            '  "condition": "intacto",\n'
            '  "notes": "Tiene un símbolo grabado.",\n'
            '  "active": true\n'
            "}\n"
            "\n"

            "IMPORTANTE:\n"
            "- create_item crea el tipo/definición del objeto.\n"
            "- create_item_instance crea una copia física concreta.\n"
            "- create_item_instance requiere un item_id existente.\n"
            "- No inventes item_id.\n"
            "\n"

            "CREAR INSTANCIA CUANDO:\n"
            "- La narrativa presenta un objeto físico concreto que debe "
            "poder rastrearse individualmente.\n"
            "- El objeto es relevante para el estado del mundo.\n"
            "- Puede distinguirse razonablemente como una copia concreta.\n"
            "\n"

            "NO CREAR INSTANCIA CUANDO:\n"
            "- Solo se menciona genéricamente un tipo de objeto.\n"
            "- La narrativa no permite determinar que exista una copia "
            "física persistente relevante.\n"
            "\n"

            "TRANSFERIR OBJETO:\n"
            "{\n"
            '  "type": "transfer_item",\n'
            '  "instance_id": 25,\n'
            '  "new_owner_id": 7\n'
            "}\n"
            "\n"

            "Usa transfer_item cuando una instancia física existente "
            "cambia explícitamente de propietario.\n"
            "\n"

            "ACTUALIZAR INSTANCIA:\n"
            "{\n"
            '  "type": "update_item_instance",\n'
            '  "instance_id": 25,\n'
            '  "condition": "dañado",\n'
            '  "notes": "La hoja tiene una grieta."\n'
            "}\n"
            "\n"

            "REGLA FUNDAMENTAL DE TRANSICIÓN DE ESTADO:\n"
            "- Si la narrativa describe una acción sobre un objeto físico "
            "que ya aparece en INSTANCIAS DE OBJETOS CONOCIDAS, debes "
            "modificar esa instancia existente.\n"
            "- No crees una nueva instancia para representar una transición "
            "de estado de una instancia ya conocida.\n"
            "- Recoger un objeto existente cambia su propietario si la "
            "narrativa confirma quién lo recoge.\n"
            "- Entregar un objeto existente cambia su propietario al receptor.\n"
            "- Dejar un objeto existente elimina su propietario si deja de "
            "pertenecer al personaje, pero no inventes una ubicación.\n"
            "- Cambiar el estado físico de un objeto existente actualiza "
            "su instancia correspondiente.\n"
            "- Solo crea una nueva instancia cuando la narrativa establezca "
            "que existe una copia física distinta que todavía no está "
            "representada en el mundo.\n"
            "\n"

            "REGLAS PARA RECOGER OBJETOS:\n"
            "- Cuando la narrativa confirme que el personaje recoge un objeto "
            "físico, busca primero una instancia existente cuyo item_id "
            "corresponda al objeto recogido.\n"
            "- Si existe una instancia física conocida que corresponde al objeto, "
            "NO crees una nueva instancia.\n"
            "- Si la instancia existente no tiene propietario y la narrativa "
            "confirma que el personaje la recoge, asigna el entity_id del "
            "personaje activo como nuevo propietario.\n"
            "- Al recoger un objeto, owner_id debe ser el ID del personaje que "
            "pasa a ser su propietario. Por ejemplo, si el personaje es Darian, "
            "debes utilizar owner_id=ID de Darian.\n"
            "- Si la instancia ya pertenece a otra entidad y la narrativa "
            "confirma que el personaje la recibe, utiliza transfer_item.\n"
            "- Si el objeto recogido no tiene ninguna instancia física conocida "
            "y la narrativa confirma que existe una copia física concreta, "
            "puede ser necesario crear una instancia, pero solo si existe un "
            "item_id conocido o puede crearse primero su definición mediante "
            "create_item.\n"
            "- No crees una segunda instancia simplemente porque el objeto "
            "vuelva a aparecer en una narrativa posterior.\n"
            "- No inventes instance_id, item_id, owner_id ni location_id.\n"
            "\n"

            "REGLAS DE INSTANCIAS:\n"
            "- Si una instancia conocida cambia de propietario, "
            "actualiza el propietario.\n"
            "- Si una instancia conocida cambia de condición, "
            "actualiza la condición.\n"
            "- Si una instancia conocida cambia de ubicación y la nueva "
            "ubicación tiene un ID conocido, actualiza location_id.\n"
            "- Si la nueva ubicación no puede representarse con un ID "
            "conocido, NO inventes un location_id.\n"
            "- Campo omitido = no modificar.\n"
            "- null = borrar explícitamente el valor.\n"
            "- No utilices null simplemente porque desconozcas el valor.\n"

            "Ejemplos:\n"
            "- \"El personaje recoge la espada y se la guarda\" -> "
            "update_item_instance o transfer_item según el estado "
            "actual de la instancia.\n"
            "- \"El personaje entrega la espada a Neria\" -> transfer_item.\n"
            "- \"El personaje deja la espada en el suelo\" -> elimina "
            "owner_id si deja de poseerla; no inventes location_id.\n"
            "- \"La espada se rompe\" -> update_item_instance con "
            "condition si la condición puede representarse.\n"
            "\n"

            "============================================================\n"
            "RECURSOS\n"
            "============================================================\n"
            "\n"

            "CREAR RECURSO:\n"
            "{\n"
            '  "type": "create_resource",\n'
            '  "name": "Oro",\n'
            '  "resource_type": "currency",\n'
            '  "unit": "gp",\n'
            '  "notes": ""\n'
            "}\n"
            "\n"

            "GANAR RECURSO:\n"
            "{\n"
            '  "type": "gain_resource",\n'
            '  "resource_id": 10,\n'
            '  "owner_id": 2,\n'
            '  "amount": 50\n'
            "}\n"
            "\n"

            "GASTAR RECURSO:\n"
            "{\n"
            '  "type": "spend_resource",\n'
            '  "resource_id": 10,\n'
            '  "owner_id": 2,\n'
            '  "amount": 20\n'
            "}\n"
            "\n"

            "TRANSFERIR RECURSO:\n"
            "{\n"
            '  "type": "transfer_resource",\n'
            '  "resource_id": 10,\n'
            '  "subject_id": 2,\n'
            '  "target_id": 7,\n'
            '  "amount": 15\n'
            "}\n"
            "\n"

            "Solo utiliza recursos cuando la narrativa confirme "
            "el cambio cuantitativo.\n"
            "\n"

            "No inventes cantidades.\n"
            "No conviertas una compra hipotética en gasto real.\n"
            "\n"

            "============================================================\n"
            "RELACIONES\n"
            "============================================================\n"
            "\n"

            "Una RELACIÓN representa una conexión persistente entre "
            "dos entidades del mundo.\n"
            "\n"

            "Una conversación, encuentro, saludo, discusión o interacción "
            "momentánea NO constituye automáticamente una relación.\n"
            "\n"

            "CREAR RELACIÓN:\n"
            "{\n"
            '  "type": "create_relation",\n'
            '  "relation_id": "aldren_guardia_ciudad",\n'
            '  "subject_id": 2,\n'
            '  "relation_type": "miembro_de",\n'
            '  "target_id": 7,\n'
            '  "metadata": {}\n'
            "}\n"
            "\n"

            "Crea una relación cuando la narrativa establezca explícitamente "
            "una conexión persistente como:\n"
            "- pertenece a una organización;\n"
            "- es miembro de una facción;\n"
            "- es familiar de otra entidad;\n"
            "- es aliado de otra entidad;\n"
            "- es enemigo de otra entidad;\n"
            "- trabaja para otra entidad;\n"
            "- debe dinero a otra entidad;\n"
            "- está casado con otra entidad;\n"
            "- tiene una relación política, comercial o social persistente.\n"
            "\n"

            "NO crees relaciones para:\n"
            "- hablar con alguien;\n"
            "- conocer a alguien;\n"
            "- estar físicamente junto a alguien;\n"
            "- atacar a alguien una sola vez;\n"
            "- ayudar a alguien una sola vez;\n"
            "- sospechar de alguien;\n"
            "- ser amable o antipático durante una conversación;\n"
            "- cualquier interacción momentánea que no establezca "
            "una relación persistente.\n"
            "\n"

            "MODIFICAR RELACIÓN:\n"
            "{\n"
            '  "type": "update_relation",\n'
            '  "relation_id": "aldren_guardia_ciudad",\n'
            '  "relation_type": "aliado_de",\n'
            '  "target_id": 7,\n'
            '  "metadata": {},\n'
            '  "active": true\n'
            "}\n"
            "\n"

            "Usa update_relation cuando una relación existente cambia "
            "explícitamente.\n"
            "\n"

            "ELIMINAR RELACIÓN:\n"
            "{\n"
            '  "type": "remove_relation",\n'
            '  "relation_id": "aldren_guardia_ciudad"\n'
            "}\n"
            "\n"

            "remove_relation desactiva una relación existente.\n"
            "\n"

            "IMPORTANTE SOBRE RELACIONES:\n"
            "- Para modificar o eliminar una relación existente utiliza "
            "su relation_id real de RELACIONES CONOCIDAS.\n"
            "- No crees una segunda relación equivalente.\n"
            "- Si una relación existente ya expresa el hecho narrado, "
            "no hagas nada salvo que haya un cambio real.\n"
            "- subject_id y target_id deben ser IDs de entidades conocidas.\n"
            "\n"

            "============================================================\n"
            "EVENTOS\n"
            "============================================================\n"
            "\n"

            "Un EVENTO representa un acontecimiento histórico relevante "
            "que ha ocurrido en el mundo.\n"
            "\n"

            "No registres cada acción narrativa como evento.\n"
            "Los eventos deben reservarse para acontecimientos con "
            "relevancia futura, histórica o causal.\n"
            "\n"

            "CREAR EVENTO:\n"
            "{\n"
            '  "type": "create_event",\n'
            '  "event_id": "cripta_puerta_abierta",\n'
            '  "event_type": "world_event",\n'
            '  "title": "La puerta de la cripta se abre",\n'
            '  "description": "La antigua puerta fue abierta.",\n'
            '  "consequences": "La cripta vuelve a ser accesible.",\n'
            '  "session_id": 1,\n'
            '  "secret": false,\n'
            '  "metadata": {}\n'
            "}\n"
            "\n"

            "CREA UN EVENTO cuando ocurra algo como:\n"
            "- apertura o destrucción de una localización importante;\n"
            "- muerte relevante;\n"
            "- descubrimiento importante;\n"
            "- inicio o final de una guerra o conflicto;\n"
            "- traición significativa;\n"
            "- aparición de una amenaza importante;\n"
            "- cambio político relevante;\n"
            "- descubrimiento de un secreto importante;\n"
            "- acontecimiento que razonablemente pueda afectar "
            "a turnos futuros.\n"
            "\n"

            "NO crees eventos para:\n"
            "- caminar unos metros;\n"
            "- hablar con un NPC sin consecuencia relevante;\n"
            "- abrir una puerta normal sin importancia futura;\n"
            "- sacar un arma;\n"
            "- realizar una acción cotidiana;\n"
            "- cualquier detalle puramente narrativo sin relevancia "
            "persistente.\n"
            "\n"

            "Si el mismo acontecimiento ya aparece en EVENTOS CONOCIDOS, "
            "no lo dupliques.\n"
            "\n"

            "Si la narrativa modifica explícitamente un evento existente "
            "pero no existe una operación específica de actualización "
            "de eventos, NO inventes una operación nueva. Conserva el "
            "evento existente y registra únicamente los cambios que "
            "sí puedan representarse mediante las operaciones disponibles.\n"
            "\n"

            "============================================================\n"
            "HP Y ESTADO DEL PERSONAJE\n"
            "============================================================\n"
            "\n"

            "CAMBIAR HP:\n"
            "{\n"
            '  "type": "change_character_hp",\n'
            '  "entity_id": 1,\n'
            '  "amount": -5\n'
            "}\n"
            "\n"

            "Usa change_character_hp cuando la narrativa confirme "
            "que un personaje ha recibido daño o curación.\n"
            "\n"

            "Daño -> amount negativo.\n"
            "Curación -> amount positivo.\n"
            "\n"

            "Ejemplos:\n"
            "- \"Aldren recibe 4 puntos de daño\" -> amount=-4.\n"
            "- \"Aldren pierde 4 HP\" -> amount=-4.\n"
            "- \"Aldren recupera 6 HP\" -> amount=6.\n"
            "- \"La trampa hiere a Aldren\" NO permite inventar cuántos "
            "HP pierde si la narrativa no especifica una cantidad "
            "y no existe otro resultado mecánico explícito que indique "
            "la cantidad.\n"
            "\n"

            "NO calcules HP final manualmente.\n"
            "NO establezcas current_hp directamente.\n"
            "NO inventes daño basándote en el tipo de ataque.\n"
            "El backend aplicará el cambio.\n"
            "\n"

            "============================================================\n"
            "PRIORIZACIÓN\n"
            "============================================================\n"
            "\n"

            "Cuando una narrativa contiene varios hechos persistentes, "
            "genera todas las operaciones necesarias.\n"
            "\n"

            "Ejemplo:\n"
            "\"El personaje derrota al guardia, recoge su espada y "
            "descubre que pertenecía a la Guardia de Hierro.\"\n"
            "\n"

            "Puede implicar:\n"
            "- cambio de estado del guardia si existe una representación "
            "persistente adecuada;\n"
            "- cambio de propietario de la espada si existe una instancia;\n"
            "- nueva información sobre el guardia;\n"
            "- una relación con la Guardia de Hierro si la pertenencia "
            "queda explícitamente establecida.\n"
            "\n"

            "Pero NO debes crear operaciones solo porque algo sea "
            "razonable o probable.\n"
            "\n"

            "============================================================\n"
            "REGLA DE CAMBIO MÍNIMO\n"
            "============================================================\n"
            "\n"

            "Realiza el cambio persistente mínimo necesario para representar "
            "el hecho confirmado.\n"
            "\n"

            "No sobrescribas información existente innecesariamente.\n"
            "No sustituyas una descripción completa si solo se ha revelado "
            "un dato nuevo.\n"
            "No cambies campos que no hayan cambiado.\n"
            "No generes operaciones redundantes.\n"
            "\n"

            "============================================================\n"
            "PROCESO MENTAL INTERNO\n"
            "============================================================\n"
            "\n"

            "Antes de responder, sigue internamente este proceso:\n"
            "1. Identifica hechos explícitos en la narrativa.\n"
            "2. Descarta intenciones, hipótesis y posibilidades.\n"
            "3. Compara cada hecho con el estado conocido.\n"
            "4. Identifica si modifica una entidad, objeto, instancia, "
            "recurso, relación, evento o HP.\n"
            "5. Reutiliza IDs existentes siempre que sea posible.\n"
            "6. Genera únicamente las operaciones necesarias.\n"
            "7. Comprueba que ningún ID inventado aparezca en operaciones "
            "que requieren una entidad existente.\n"
            "8. Comprueba que no hayas duplicado una entidad, instancia, "
            "relación o evento existente.\n"
            "9. Devuelve únicamente JSON válido.\n"
            "\n"

            "============================================================\n"
            "FORMATO DE SALIDA\n"
            "============================================================\n"
            "\n"

            "Debes devolver EXCLUSIVAMENTE un objeto JSON válido.\n"
            "\n"

            "Formato:\n"
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

            "Si no existe ningún cambio persistente:\n"
            "{\n"
            '  "operations": []\n'
            "}\n"
            "\n"

            "NO uses Markdown.\n"
            "NO uses bloques ```json.\n"
            "NO añadas explicaciones antes o después del JSON.\n"
            "\n"

            "============================================================\n"
            "CONTEXTO ACTUAL DEL MUNDO\n"
            "============================================================\n"
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

            "INSTANCIAS DE OBJETOS CONOCIDAS "
            "(INSTANCIAS DE ITEMS CONOCIDAS):\n"
            f"{known_item_instances}\n"
            "\n"

            "RECURSOS CONOCIDOS:\n"
            f"{known_resources}\n"
            "\n"

            "RELACIONES CONOCIDAS:\n"
            f"{known_relations}\n"
            "\n"

            "EVENTOS CONOCIDOS:\n"
            f"{known_events}\n"
            "\n"

            "============================================================\n"
            "NARRATIVA A ANALIZAR\n"
            "============================================================\n"
            "\n"

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
                (WorldOperation, CharacterOperation),
            ):
                raise LLMExtractionError(
                    "Operation parser returned "
                    f"invalid operation at index {index}"
                )

        return operations