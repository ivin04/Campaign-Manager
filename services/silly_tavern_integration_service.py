from __future__ import annotations

from database import get_conn

from models.turn_context import TurnContext
from models.turn_record import TurnRecord
from models.turn_resolution_result import TurnResolutionResult

from repositories.turn_repository import TurnRepository

from services.campaign_state_service import (
    CampaignStateService,
    CampaignStateServiceError,
)
from services.context_builder import ContextBuilder
from services.llm_world_extractor import (
    LLMWorldExtractor,
    LLMExtractionError,
)
from services.world_service import WorldService


class SillyTavernIntegrationServiceError(RuntimeError):
    """
    Error base de la integración con SillyTavern.
    """


class SillyTavernIntegrationServiceConflictError(
    SillyTavernIntegrationServiceError
):
    """
    Conflicto de idempotencia.

    Ocurre cuando un external_turn_id ya existe pero
    pertenece a un payload diferente.
    """


class SillyTavernIntegrationService:
    """
    Integra SillyTavern con Campaign Manager.

    SillyTavern es responsable de generar la narrativa.

    Campaign Manager es responsable de:

        - proporcionar contexto persistente
        - proporcionar el estado actual de la campaña
        - extraer cambios persistentes de la narrativa
        - aplicar las operaciones al mundo
        - persistir el turno

    Flujo:

        SillyTavern
             |
             | contexto
             v
        ContextBuilder
             |
             | contexto
             v
        SillyTavern
             |
             | player_input + narrative
             v
        LLMWorldExtractor
             |
             v
        WorldService
             |
             v
        TurnRepository

    Este servicio NO:

        - genera narrativa
        - conoce Ollama
        - construye prompts narrativos
        - modifica directamente SQLite
        - implementa reglas de dominio
    """

    def __init__(
        self,
        *,
        campaign_state_service: CampaignStateService,
        context_builder: ContextBuilder,
        extractor: LLMWorldExtractor,
        world_service: WorldService,
        turn_repository: TurnRepository,
    ) -> None:

        if not isinstance(
            campaign_state_service,
            CampaignStateService,
        ):
            raise TypeError(
                "campaign_state_service must be a "
                "CampaignStateService"
            )

        if not isinstance(
            context_builder,
            ContextBuilder,
        ):
            raise TypeError(
                "context_builder must be a ContextBuilder"
            )

        if not isinstance(
            extractor,
            LLMWorldExtractor,
        ):
            raise TypeError(
                "extractor must be a LLMWorldExtractor"
            )

        if not isinstance(
            world_service,
            WorldService,
        ):
            raise TypeError(
                "world_service must be a WorldService"
            )

        if not isinstance(
            turn_repository,
            TurnRepository,
        ):
            raise TypeError(
                "turn_repository must be a TurnRepository"
            )

        self.campaign_state_service = (
            campaign_state_service
        )

        self.context_builder = context_builder

        self.extractor = extractor

        self.world_service = world_service

        self.turn_repository = turn_repository

    # ============================================================
    # CONTEXT
    # ============================================================

    def get_context(
        self,
        query: str,
    ) -> dict:
        """
        Construye el contexto que SillyTavern debe proporcionar
        al modelo antes de generar la narrativa.

        El contexto utiliza exactamente el mismo ContextBuilder
        empleado por el pipeline interno de Campaign Manager.
        """

        normalized_query = self._validate_text(
            query,
            "query",
        )

        try:
            turn_context = (
                self.campaign_state_service
                .get_turn_context()
            )

        except CampaignStateServiceError as exc:
            raise SillyTavernIntegrationServiceError(
                "failed to obtain campaign context"
            ) from exc

        except Exception as exc:
            raise SillyTavernIntegrationServiceError(
                "CampaignStateService failed to obtain "
                "campaign context"
            ) from exc

        if not isinstance(
            turn_context,
            TurnContext,
        ):
            raise SillyTavernIntegrationServiceError(
                "CampaignStateService returned an invalid "
                "TurnContext"
            )

        session_id = None

        if turn_context.current_session is not None:
            session_id = (
                turn_context.current_session.session_id
            )

        try:
            recent_turns = (
                self.turn_repository.list_recent_turns(
                    session_id=session_id,
                    limit=10,
                )
            )

        except Exception as exc:
            raise SillyTavernIntegrationServiceError(
                "failed to load recent turn history"
            ) from exc

        try:
            context = self.context_builder.build(
                turn_context.world,
                normalized_query,
                recent_turns=recent_turns,
            )

        except Exception as exc:
            raise SillyTavernIntegrationServiceError(
                "ContextBuilder failed to build context"
            ) from exc

        return {
            "campaign": {
                "id": turn_context.campaign.campaign_id,
                "name": turn_context.campaign.name,
                "system": turn_context.campaign.system,
                "tone": turn_context.campaign.tone,
                "summary": turn_context.campaign.summary,
            },
            "session": self._serialize_session(
                turn_context
            ),
            "active_character": (
                self._serialize_active_character(
                    turn_context
                )
            ),
            "query": normalized_query,
            "context": context,
        }

    # ============================================================
    # EXTERNAL TURN
    # ============================================================

    def process_turn(
        self,
        player_input: str,
        narrative: str,
        external_turn_id: str | None = None,
    ) -> TurnResolutionResult:
        """
        Procesa un turno cuya narrativa ya ha sido generada
        por SillyTavern.

        La persistencia del mundo y del TurnRecord es atómica.

        Cuando existe external_turn_id:

            - el ID se comprueba dentro de una transacción
              BEGIN IMMEDIATE.

            - mismo ID + mismo payload:
                devuelve el resultado persistido sin volver
                a ejecutar las operaciones.

            - mismo ID + payload diferente:
                produce un conflicto.

            - ID inexistente:
                procesa y persiste normalmente.

        BEGIN IMMEDIATE garantiza que dos peticiones concurrentes
        con el mismo external_turn_id no puedan ejecutar ambas
        las operaciones sobre el mundo.
        """

        normalized_input = self._validate_text(
            player_input,
            "player_input",
        )

        normalized_narrative = self._validate_text(
            narrative,
            "narrative",
        )

        normalized_external_turn_id = None

        if external_turn_id is not None:
            if not isinstance(
                external_turn_id,
                str,
            ):
                raise TypeError(
                    "external_turn_id must be a string or None"
                )

            normalized_external_turn_id = (
                external_turn_id.strip()
            )

            if not normalized_external_turn_id:
                raise ValueError(
                    "external_turn_id must not be empty"
                )

            if len(normalized_external_turn_id) > 500:
                raise ValueError(
                    "external_turn_id must not be longer than 500 characters"
                )

        # --------------------------------------------------------
        # CONTEXTO
        # --------------------------------------------------------

        try:
            turn_context = (
                self.campaign_state_service
                .get_turn_context()
            )

        except CampaignStateServiceError as exc:
            raise SillyTavernIntegrationServiceError(
                "failed to obtain campaign turn context"
            ) from exc

        except Exception as exc:
            raise SillyTavernIntegrationServiceError(
                "CampaignStateService failed to obtain "
                "campaign turn context"
            ) from exc

        if not isinstance(
            turn_context,
            TurnContext,
        ):
            raise SillyTavernIntegrationServiceError(
                "CampaignStateService returned an invalid "
                "TurnContext"
            )

        session_id = None

        if turn_context.current_session is not None:
            session_id = (
                turn_context.current_session.session_id
            )

        # --------------------------------------------------------
        # HISTORIAL
        # --------------------------------------------------------

        try:
            recent_turns = (
                self.turn_repository.list_recent_turns(
                    session_id=session_id,
                    limit=10,
                )
            )

        except Exception as exc:
            raise SillyTavernIntegrationServiceError(
                "failed to load recent turn history"
            ) from exc

        # --------------------------------------------------------
        # EXTRAER OPERACIONES
        # --------------------------------------------------------

        try:
            operations = self.extractor.extract(
                normalized_narrative,
                turn_context,
            )

        except LLMExtractionError as exc:
            raise SillyTavernIntegrationServiceError(
                "failed to extract world operations"
            ) from exc

        except Exception as exc:
            raise SillyTavernIntegrationServiceError(
                "LLMWorldExtractor failed to extract "
                "world operations"
            ) from exc

        if not isinstance(
            operations,
            list,
        ):
            raise SillyTavernIntegrationServiceError(
                "LLMWorldExtractor returned an invalid "
                "operations list"
            )

        # --------------------------------------------------------
        # SEPARAR OPERACIONES
        # --------------------------------------------------------

        from operations.world_operations import (
            WorldOperation,
        )

        from operations.character_operations import (
            CharacterOperation,
        )

        from operations.referenced_operation import (
            ReferencedOperation,
        )

        world_operations = []
        character_operations = []

        for operation in operations:

            if isinstance(
                operation,
                ReferencedOperation,
            ):
                inner_operation = (
                    operation.operation
                )

                if isinstance(
                    inner_operation,
                    WorldOperation,
                ):
                    world_operations.append(
                        operation
                    )

                elif isinstance(
                    inner_operation,
                    CharacterOperation,
                ):
                    character_operations.append(
                        operation
                    )

                else:
                    raise SillyTavernIntegrationServiceError(
                        "LLMWorldExtractor returned an invalid "
                        "referenced operation"
                    )

            elif isinstance(
                operation,
                WorldOperation,
            ):
                world_operations.append(
                    operation
                )

            elif isinstance(
                operation,
                CharacterOperation,
            ):
                character_operations.append(
                    operation
                )

            else:
                raise SillyTavernIntegrationServiceError(
                    "LLMWorldExtractor returned an invalid "
                    "operation"
                )

        normalized_operations = tuple(
            operations
        )

        # --------------------------------------------------------
        # APLICAR + PERSISTIR ATÓMICAMENTE
        # --------------------------------------------------------
        #
        # IMPORTANTE:
        #
        # El BEGIN IMMEDIATE ocurre DESPUÉS de la extracción
        # LLM para no mantener bloqueada la base de datos mientras
        # esperamos al modelo.
        #
        # La comprobación del external_turn_id se hace dentro
        # de esta transacción y por tanto es la comprobación
        # autoritativa.
        # --------------------------------------------------------

        try:
            with get_conn() as conn:

                # ------------------------------------------------
                # ADQUIRIR LOCK DE ESCRITURA
                # ------------------------------------------------

                conn.execute(
                    "BEGIN IMMEDIATE"
                )

                # ------------------------------------------------
                # IDEMPOTENCIA
                # ------------------------------------------------

                if normalized_external_turn_id is not None:

                    existing_turn = (
                        self.turn_repository
                        .get_by_external_turn_id(
                            normalized_external_turn_id,
                            conn=conn,
                        )
                    )

                    if existing_turn is not None:

                        same_input = (
                            existing_turn.player_input
                            == normalized_input
                        )

                        same_narrative = (
                            existing_turn.narrative
                            == normalized_narrative
                        )

                        if not (
                            same_input
                            and same_narrative
                        ):
                            raise (
                                SillyTavernIntegrationServiceConflictError(
                                    "external_turn_id already exists "
                                    "with different turn content: "
                                    f"{normalized_external_turn_id}"
                                )
                            )

                        # ------------------------------------------------
                        # REPETICIÓN EXACTA
                        # ------------------------------------------------
                        #
                        # El turno ya fue procesado correctamente.
                        #
                        # NO volvemos a aplicar operaciones.
                        # NO modificamos WorldState.
                        # NO insertamos otro TurnRecord.
                        #
                        # El contexto manager hará COMMIT, pero no
                        # existe ninguna modificación relevante.
                        # ------------------------------------------------

                        return (
                            TurnResolutionResult
                            .from_persisted_turn(
                                existing_turn
                            )
                        )

                # ------------------------------------------------
                # APLICAR OPERACIONES
                # ------------------------------------------------

                operation_results = (
                    self.world_service.apply_turn_operations(
                        world_operations,
                        character_operations,
                        conn=conn,
                        ordered_operations=normalized_operations,
                    )
                )

                # ------------------------------------------------
                # CREAR RESULTADO
                # ------------------------------------------------

                result = TurnResolutionResult(
                    player_input=normalized_input,
                    narrative=normalized_narrative,
                    operations=tuple(
                        world_operations
                    ),
                    character_operations=tuple(
                        character_operations
                    ),
                    operation_results=tuple(
                        operation_results
                    ),
                )

                # ------------------------------------------------
                # PERSISTIR TURNO
                # ------------------------------------------------

                self.turn_repository.save_turn(
                    TurnRecord(
                        session_id=session_id,
                        player_input=result.player_input,
                        narrative=result.narrative,
                        operation_count=(
                            result.operation_count
                        ),
                        successful_operation_count=(
                            result.successful_operation_count
                        ),
                        failed_operation_count=(
                            result.failed_operation_count
                        ),
                        all_operations_succeeded=(
                            result.all_operations_succeeded
                        ),
                        world_changed=(
                            result.world_changed
                        ),
                        external_turn_id=(
                            normalized_external_turn_id
                        ),
                    ),
                    conn=conn,
                )

        except SillyTavernIntegrationServiceConflictError:
            raise

        except Exception as exc:
            raise SillyTavernIntegrationServiceError(
                "failed to process and persist SillyTavern turn"
            ) from exc

        return result

    # ============================================================
    # SERIALIZATION
    # ============================================================

    @staticmethod
    def _serialize_session(
        context: TurnContext,
    ) -> dict | None:

        session = context.current_session

        if session is None:
            return None

        return {
            "id": session.session_id,
            "number": session.number,
            "title": session.title,
            "summary": session.summary,
            "start_location": session.start_location,
            "end_location": session.end_location,
            "notes": session.notes,
        }

    @staticmethod
    def _serialize_active_character(
        context: TurnContext,
    ) -> dict | None:

        character = context.active_character

        if character is None:
            return None

        return {
            "entity_id": character.entity_id,
            "level": character.level,
            "class_name": character.class_name,
            "current_hp": character.current_hp,
            "max_hp": character.max_hp,
            "armor_class": character.armor_class,
            "strength": character.strength,
            "dexterity": character.dexterity,
            "constitution": character.constitution,
            "intelligence": character.intelligence,
            "wisdom": character.wisdom,
            "charisma": character.charisma,
            "proficiency_bonus": (
                character.proficiency_bonus
            ),
        }

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def _validate_text(
        value: str,
        field_name: str,
    ) -> str:

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string"
            )

        value = value.strip()

        if not value:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return value