from models.entity import Entity
from models.extraction import ExtractedFact
from models.resource import Resource, ResourceBalance
from models.world_state import WorldState
from models.resource import Resource

from operations.world_operations import GainResourceOperation

from services.resolution import WorldResolver
from services.world_applier import WorldApplier


def build_world():
    fungoso = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
    )

    oro = Resource(
        id=20,
        name="Oro",
        resource_type="currency",
        unit="gp",
    )

    balance = ResourceBalance(
        id=200,
        resource_id=20,
        owner_id=1,
        amount=100,
    )

    return WorldState(
        entities={
            1: fungoso,
        },
        resources={
            20: oro,
        },
        resource_balances={
            200: balance,
        },
    )


def test_resolve_resource_gained():
    world = build_world()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": 50,
        },
    )

    resolver = WorldResolver(
        entities=world.entities,
        items=world.items,
        item_instances=world.item_instances,
        resources=world.resources,
        resource_balances=world.resource_balances,
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(operation, GainResourceOperation)
    assert operation.resource_id == 20
    assert operation.owner_id == 1
    assert operation.amount == 50


def test_apply_resource_gained():
    world = build_world()

    operation = GainResourceOperation(
        resource_id=20,
        owner_id=1,
        amount=50,
    )

    applier = WorldApplier()

    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 150

def test_apply_resource_gained_rejects_unknown_resource():
    world = build_world()

    operation = GainResourceOperation(
        resource_id=999,
        owner_id=1,
        amount=50,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100


def test_apply_resource_gained_rejects_unknown_owner():
    world = build_world()

    operation = GainResourceOperation(
        resource_id=20,
        owner_id=999,
        amount=50,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100


def test_apply_resource_gained_rejects_non_positive_amount():
    world = build_world()

    operation = GainResourceOperation(
        resource_id=20,
        owner_id=1,
        amount=-50,
    )

    applier = WorldApplier()
    applier.apply(world, operation)

    assert world.resource_balances[200].amount == 100

def test_gain_resource_creates_missing_balance():
    world = build_world()

    world.resources[1] = Resource(
        id=1,
        name="Gold",
    )

    operation = GainResourceOperation(
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    WorldApplier().apply(world, operation)

    balances = [
        balance
        for balance in world.resource_balances.values()
        if balance.resource_id == 1
        and balance.owner_id == 1
    ]

    assert len(balances) == 1
    assert balances[0].amount == 100