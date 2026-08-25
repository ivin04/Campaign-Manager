from models.entity import Entity
from models.resource import Resource, ResourceBalance
from models.world_state import WorldState

from operations.world_operations import SpendResourceOperation
from services.world_applier import WorldApplier


def build_world():
    world = WorldState()

    world.entities[1] = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
    )

    world.resources[20] = Resource(
        id=20,
        name="oro",
        resource_type="currency",
        unit="gp",
    )

    world.resource_balances[200] = ResourceBalance(
        id=200,
        resource_id=20,
        owner_id=1,
        amount=100,
    )

    return world


def test_apply_resource_spent():
    world = build_world()

    operation = SpendResourceOperation(
        resource_id=20,
        owner_id=1,
        amount=30,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 70


def test_apply_resource_spent_rejects_unknown_resource():
    world = build_world()

    operation = SpendResourceOperation(
        resource_id=999,
        owner_id=1,
        amount=30,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100


def test_apply_resource_spent_rejects_unknown_owner():
    world = build_world()

    operation = SpendResourceOperation(
        resource_id=20,
        owner_id=999,
        amount=30,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100


def test_apply_resource_spent_rejects_non_positive_amount():
    world = build_world()

    operation = SpendResourceOperation(
        resource_id=20,
        owner_id=1,
        amount=-30,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100


def test_apply_resource_spent_rejects_insufficient_balance():
    world = build_world()

    operation = SpendResourceOperation(
        resource_id=20,
        owner_id=1,
        amount=150,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100