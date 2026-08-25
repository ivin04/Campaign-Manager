from __future__ import annotations

import json
from typing import Any

from operations.world_operations import (
    CreateEventOperation,
    CreateRelationOperation,
    GainResourceOperation,
    RemoveRelationOperation,
    SpendResourceOperation,
    TransferItemOperation,
    TransferResourceOperation,
    UpdateRelationOperation,
    WorldOperation,
)


class OperationParseError(ValueError):
    """Raised when an LLM response cannot be converted safely to operations."""


class OperationParser:
    """
    Converts the structured output produced by the narrative/LLM layer into
    concrete WorldOperation instances.

    This class does not inspect or mutate WorldState. Semantic validation
    (for example, whether an entity exists) remains the responsibility of
    WorldApplier/WorldService.
    """

    _BUILDERS = {
        "transfer_item": TransferItemOperation,
        "gain_resource": GainResourceOperation,
        "spend_resource": SpendResourceOperation,
        "transfer_resource": TransferResourceOperation,
        "create_relation": CreateRelationOperation,
        "update_relation": UpdateRelationOperation,
        "remove_relation": RemoveRelationOperation,
        "create_event": CreateEventOperation,
    }

    def parse(self, payload: str | dict[str, Any]) -> list[WorldOperation]:
        """Parse an LLM JSON response into validated operation objects."""
        data = self._decode(payload)

        if not isinstance(data, dict):
            raise OperationParseError("Root JSON must be an object.")

        operations = data.get("operations")
        if not isinstance(operations, list):
            raise OperationParseError("'operations' must be a list.")

        result: list[WorldOperation] = []

        for index, raw_operation in enumerate(operations):
            try:
                result.append(self._parse_operation(raw_operation))
            except OperationParseError as exc:
                raise OperationParseError(
                    f"Invalid operation at index {index}: {exc}"
                ) from exc

        return result

    def _decode(self, payload: str | dict[str, Any]) -> Any:
        if isinstance(payload, dict):
            return payload

        if not isinstance(payload, str):
            raise OperationParseError("Payload must be a JSON string or dict.")

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise OperationParseError("Invalid JSON payload.") from exc

    def _parse_operation(self, raw: Any) -> WorldOperation:
        if not isinstance(raw, dict):
            raise OperationParseError("Operation must be an object.")

        operation_type = raw.get("type")
        if not isinstance(operation_type, str) or not operation_type:
            raise OperationParseError("Operation requires a non-empty 'type'.")

        builder = self._BUILDERS.get(operation_type)
        if builder is None:
            raise OperationParseError(
                f"Unknown operation type: {operation_type!r}."
            )

        fields = dict(raw)
        fields.pop("type", None)

        expected = builder.__dataclass_fields__
        unknown = set(fields) - set(expected)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise OperationParseError(
                f"Unknown field(s) for {operation_type}: {names}."
            )

        missing = [
            name
            for name, field in expected.items()
            if field.default is field.default_factory is field.default
            and name not in fields
        ]

        # Dataclasses use MISSING for required fields. The explicit check below
        # is kept separate so optional fields with defaults remain optional.
        from dataclasses import MISSING

        missing = [
            name
            for name, field in expected.items()
            if field.default is MISSING
            and field.default_factory is MISSING
            and name not in fields
        ]

        if missing:
            raise OperationParseError(
                f"Missing required field(s) for {operation_type}: "
                + ", ".join(missing)
                + "."
            )

        self._validate_fields(operation_type, fields)

        try:
            return builder(**fields)
        except (TypeError, ValueError) as exc:
            raise OperationParseError(
                f"Invalid fields for {operation_type}: {exc}"
            ) from exc

    def _validate_fields(self, operation_type: str, fields: dict[str, Any]) -> None:
        integer_fields = {
            "transfer_item": {"instance_id", "new_owner_id"},
            "gain_resource": {"resource_id", "owner_id"},
            "spend_resource": {"resource_id", "owner_id"},
            "transfer_resource": {"resource_id", "source_id", "target_id"},
            "create_relation": {"subject_id", "target_id"},
            "update_relation": {"target_id"},
            "create_event": {"session_id"},
        }.get(operation_type, set())

        for name in integer_fields:
            if name not in fields or fields[name] is None:
                continue
            if not isinstance(fields[name], int) or isinstance(fields[name], bool):
                raise OperationParseError(f"'{name}' must be an integer.")

        amount = fields.get("amount")
        if amount is not None and (
            not isinstance(amount, (int, float)) or isinstance(amount, bool)
        ):
            raise OperationParseError("'amount' must be a number.")

        for name in {"metadata"}:
            if name in fields and fields[name] is not None and not isinstance(fields[name], dict):
                raise OperationParseError(f"'{name}' must be an object or null.")

        if "active" in fields and fields["active"] is not None and not isinstance(fields["active"], bool):
            raise OperationParseError("'active' must be boolean or null.")

        if "secret" in fields and not isinstance(fields["secret"], bool):
            raise OperationParseError("'secret' must be boolean.")

        string_fields = {
            "relation_id",
            "relation_type",
            "event_id",
            "event_type",
            "title",
            "description",
            "consequences",
        }

        for name in string_fields:
            if name in fields and fields[name] is not None and not isinstance(fields[name], str):
                raise OperationParseError(f"'{name}' must be a string or null.")
