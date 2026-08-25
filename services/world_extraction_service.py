from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from models.world_state import WorldState

from operations.world_operations import (
    WorldOperation,
)


@dataclass(frozen=True)
class ExtractionResult:
    """
    Resultado de analizar un texto narrativo.

    operations:
        Operaciones que representan cambios reales en el mundo.

    ignored:
        Indica que el texto no contiene ningún cambio persistente.
    """

    operations: list[WorldOperation]
    ignored: bool = False


class WorldExtractionService:
    """
    Convierte texto narrativo en operaciones de mundo.

    IMPORTANTE:

    Esta clase NO modifica WorldState.

    Su única responsabilidad es interpretar texto y producir
    WorldOperation.

    El resultado debe pasar posteriormente por WorldService.
    """

    def __init__(
        self,
        extractor: Callable[
            [str, WorldState],
            list[WorldOperation],
        ] | None = None,
    ):
        """
        extractor permite inyectar posteriormente un LLM.

        Por ejemplo:

            WorldExtractionService(
                extractor=my_llm_extractor
            )

        El extractor debe recibir:

            text
            world

        y devolver:

            list[WorldOperation]
        """

        self.extractor = extractor

    def extract(
        self,
        text: str,
        world: WorldState,
    ) -> ExtractionResult:
        """
        Analiza un texto y devuelve las operaciones detectadas.
        """

        if not isinstance(text, str):
            return ExtractionResult(
                operations=[],
                ignored=True,
            )

        text = text.strip()

        if not text:
            return ExtractionResult(
                operations=[],
                ignored=True,
            )

        if self.extractor is None:
            return ExtractionResult(
                operations=[],
                ignored=True,
            )

        operations = self.extractor(text, world)

        if operations is None:
            operations = []

        return ExtractionResult(
            operations=list(operations),
            ignored=len(operations) == 0,
        )

    def extract_and_apply(
        self,
        text: str,
        world_service,
    ) -> ExtractionResult:
        """
        Analiza el texto y aplica las operaciones mediante WorldService.

        Esta función NO habla directamente con el repositorio.

        Flujo:

            texto
              ↓
            extractor
              ↓
            operaciones
              ↓
            WorldService
              ↓
            WorldApplier
        """

        result = self.extract(
            text,
            world_service.get_world(),
        )

        for operation in result.operations:
            world_service.apply(operation)

        return result

    def extract_and_apply_and_save(
        self,
        text: str,
        world_service,
    ) -> ExtractionResult:
        """
        Analiza, aplica y persiste las operaciones.

        Si no se detectan operaciones no se realiza ningún guardado.
        """

        result = self.extract(
            text,
            world_service.get_world(),
        )

        if not result.operations:
            return result

        for operation in result.operations:
            world_service.apply(operation)

        world_service.save()

        return result