from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterOperation:
    """
    Operación de dominio aplicada sobre CharacterState.

    Las operaciones de personaje no modifican WorldState.
    """
    pass


@dataclass(frozen=True)
class ChangeCharacterHpOperation(
    CharacterOperation
):
    """
    Modifica los puntos de golpe actuales de un personaje.

    amount:
        Positivo -> curación.
        Negativo -> daño.

    El valor final nunca debe superar max_hp
    ni ser inferior a 0.
    """

    entity_id: int
    amount: int