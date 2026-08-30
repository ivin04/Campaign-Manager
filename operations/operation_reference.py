from dataclasses import dataclass


@dataclass(frozen=True)
class OperationReference:
    """
    Referencia al resultado de una operación anterior.

    Ejemplo de entrada del LLM:

        "$sword"

    que se representa internamente como:

        OperationReference("sword")
    """

    name: str