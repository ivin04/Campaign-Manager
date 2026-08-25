from models.entity import Entity
from models.extraction import ExtractedFact
from models.resource import Resource, ResourceBalance
from services.resolution import WorldResolver


def build_resolver():
    entities = {
        1: Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        ),
        2: Entity(
            id=2,
            name="Elric",
            entity_type="character",
        ),
    }

    resources = {
        1: Resource(
            id=1,
            name="Oro",
            resource_type="currency",
        ),
    }

    return WorldResolver(
        entities=entities,
        items={},
        item_instances={},
        resources=resources,
        resource_balances={},
        relations={},
    )


def test_resolve_resource_gained():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": 50,
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert operation.resource_id == 1
    assert operation.owner_id == 1
    assert operation.amount == 50


def test_resolve_resource_gained_case_insensitive():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "oRo",
            "owner": "fungoso",
            "amount": 50,
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1


def test_resolve_resource_gained_converts_amount_to_float():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": "50",
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1
    assert operations[0].amount == 50.0


def test_resolve_resource_gained_rejects_unknown_resource():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Plata",
            "owner": "Fungoso",
            "amount": 50,
        },
    )

    operations = resolver.resolve([fact])

    assert operations == []


def test_resolve_resource_gained_rejects_unknown_owner():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Morgath",
            "amount": 50,
        },
    )

    operations = resolver.resolve([fact])

    assert operations == []


def test_resolve_resource_gained_rejects_missing_amount():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
        },
    )

    operations = resolver.resolve([fact])

    assert operations == []


def test_resolve_resource_gained_rejects_invalid_amount():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": "abc",
        },
    )

    operations = resolver.resolve([fact])

    assert operations == []


def test_resolve_resource_gained_rejects_zero_amount():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": 0,
        },
    )

    operations = resolver.resolve([fact])

    assert operations == []


def test_resolve_resource_gained_rejects_negative_amount():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": -10,
        },
    )

    operations = resolver.resolve([fact])

    assert operations == []

def test_resolve_resource_spent():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": 50,
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert operation.resource_id == 1
    assert operation.owner_id == 1
    assert operation.amount == 50


def test_resolve_resource_spent_converts_amount_to_float():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": "25",
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1
    assert operations[0].amount == 25.0


def test_resolve_resource_spent_rejects_unknown_resource():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Plata",
            "owner": "Fungoso",
            "amount": 50,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_spent_rejects_unknown_owner():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Oro",
            "owner": "Morgath",
            "amount": 50,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_spent_rejects_missing_balance():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": 50,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_spent_rejects_insufficient_balance():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=40,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": 50,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_spent_rejects_zero_amount():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": 0,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_spent_rejects_negative_amount():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": -10,
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_resource_transferred():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Elric",
            "amount": 40,
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert operation.resource_id == 1
    assert operation.source_id == 1
    assert operation.target_id == 2
    assert operation.amount == 40


def test_resolve_resource_transferred_converts_amount_to_float():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Elric",
            "amount": "40",
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1
    assert operations[0].amount == 40.0


def test_resolve_resource_transferred_rejects_unknown_resource():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Plata",
            "from": "Fungoso",
            "to": "Elric",
            "amount": 40,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_transferred_rejects_unknown_source():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Morgath",
            "to": "Elric",
            "amount": 40,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_transferred_rejects_unknown_target():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Morgath",
            "amount": 40,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_transferred_rejects_missing_source_balance():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Elric",
            "amount": 40,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_transferred_rejects_insufficient_balance():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=30,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Elric",
            "amount": 40,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_transferred_rejects_zero_amount():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Elric",
            "amount": 0,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_transferred_rejects_negative_amount():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Elric",
            "amount": -10,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_resource_transferred_rejects_invalid_amount():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Elric",
            "amount": "abc",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_resource_gained_rejects_nan_amount():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": "nan",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_resource_gained_rejects_infinite_amount():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_GAINED",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": "inf",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_resource_spent_rejects_nan_amount():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": "nan",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_resource_transferred_rejects_infinite_amount():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Elric",
            "amount": "inf",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_resource_transferred_rejects_same_source_and_target():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Fungoso",
            "amount": 40,
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_resource_spent_rejects_duplicate_balances():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    resolver.resource_balances[2] = ResourceBalance(
        id=2,
        resource_id=1,
        owner_id=1,
        amount=200,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_SPENT",
        data={
            "resource": "Oro",
            "owner": "Fungoso",
            "amount": 50,
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_resource_transferred_rejects_duplicate_source_balances():
    resolver = build_resolver()

    resolver.resource_balances[1] = ResourceBalance(
        id=1,
        resource_id=1,
        owner_id=1,
        amount=100,
    )

    resolver.resource_balances[2] = ResourceBalance(
        id=2,
        resource_id=1,
        owner_id=1,
        amount=200,
    )

    fact = ExtractedFact(
        fact_type="RESOURCE_TRANSFERRED",
        data={
            "resource": "Oro",
            "from": "Fungoso",
            "to": "Elric",
            "amount": 40,
        },
    )

    assert resolver.resolve([fact]) == []