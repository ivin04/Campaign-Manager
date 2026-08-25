from models.item import Item, ItemInstance


class ItemResolver:

    def __init__(
        self,
        items: dict[int, Item],
        instances: dict[int, ItemInstance],
    ):
        self.items = items
        self.instances = instances

    def find_item(
        self,
        name: str,
    ) -> Item | None:

        if not name:
            return None

        normalized = name.strip().casefold()

        for item in self.items.values():

            if item.name.strip().casefold() == normalized:
                return item

        return None

    def find_instances(
        self,
        item_id: int,
    ) -> list[ItemInstance]:

        return [
            instance
            for instance in self.instances.values()
            if instance.item_id == item_id
            and instance.active
        ]

    def find_instances_by_owner(
        self,
        item_id: int,
        owner_id: int,
    ) -> list[ItemInstance]:

        return [
            instance
            for instance in self.instances.values()
            if instance.active
            and instance.item_id == item_id
            and instance.owner_id == owner_id
        ]

    def find_instance_by_owner(
        self,
        item_id: int,
        owner_id: int,
    ) -> ItemInstance | None:

        for instance in self.instances.values():

            if not instance.active:
                continue

            if instance.item_id != item_id:
                continue

            if instance.owner_id != owner_id:
                continue

            return instance

        return None

    