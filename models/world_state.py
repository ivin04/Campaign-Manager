from dataclasses import dataclass, field

from .entity import Entity
from .item import Item, ItemInstance
from .resource import Resource, ResourceBalance
from .relation import Relation
from .event import Event


@dataclass
class WorldState:

    entities: dict[int, Entity] = field(default_factory=dict)

    items: dict[int, Item] = field(default_factory=dict)

    item_instances: dict[int, ItemInstance] = field(
        default_factory=dict
    )

    resources: dict[int, Resource] = field(
        default_factory=dict
    )

    resource_balances: dict[int, ResourceBalance] = field(
        default_factory=dict
    )

    relations: dict[str, Relation] = field(
        default_factory=dict
    )

    events: dict[str, Event] = field(
        default_factory=dict
    )