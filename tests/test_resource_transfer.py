from models.entity import Entity
from models.resource import Resource, ResourceBalance
from models.world_state import WorldState

from operations.world_operations import TransferResourceOperation
from services.world_applier import WorldApplier


def build_world():
    world = WorldState()

    world.entities[1] = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
    )

    world.entities[2] = Entity(
        id=2,
        name="Neria",
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

    world.resource_balances[201] = ResourceBalance(
        id=201,
        resource_id=20,
        owner_id=2,
        amount=25,
    )

    return world


def test_transfer_resource():
    world = build_world()

    operation = TransferResourceOperation(
        resource_id=20,
        source_id=1,
        target_id=2,
        amount=30,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 70
    assert world.resource_balances[201].amount == 55


def test_transfer_resource_rejects_unknown_resource():
    world = build_world()

    operation = TransferResourceOperation(
        resource_id=999,
        source_id=1,
        target_id=2,
        amount=30,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100
    assert world.resource_balances[201].amount == 25


def test_transfer_resource_rejects_unknown_source():
    world = build_world()

    operation = TransferResourceOperation(
        resource_id=20,
        source_id=999,
        target_id=2,
        amount=30,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100
    assert world.resource_balances[201].amount == 25


def test_transfer_resource_rejects_unknown_target():
    world = build_world()

    operation = TransferResourceOperation(
        resource_id=20,
        source_id=1,
        target_id=999,
        amount=30,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100
    assert world.resource_balances[201].amount == 25


def test_transfer_resource_rejects_non_positive_amount():
    world = build_world()

    operation = TransferResourceOperation(
        resource_id=20,
        source_id=1,
        target_id=2,
        amount=-30,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100
    assert world.resource_balances[201].amount == 25


def test_transfer_resource_rejects_insufficient_balance():
    world = build_world()

    operation = TransferResourceOperation(
        resource_id=20,
        source_id=1,
        target_id=2,
        amount=150,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100
    assert world.resource_balances[201].amount == 25