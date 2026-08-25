from repositories import item_repository

from services.identity_service import names_match


# ---------------------------------------------------------
# Reglas de identidad de Items
# ---------------------------------------------------------

ITEM_SYNONYM_GROUPS = [
    ["anillo", "aro", "sortija"],
]


def get_all_items():
    return item_repository.get_all()


def search_items(query: str):
    return item_repository.search(query)


def get_item(item_id: int):
    return item_repository.get_by_id(item_id)


def get_item_by_name(name: str):
    return item_repository.get_by_name(name)


def create_item(data: dict):
    return item_repository.create(data)


def update_item(item_id: int, data: dict):
    return item_repository.update(
        item_id,
        data
    )


def find_matching_item(name: str):
    """
    Busca un Item existente que probablemente represente
    la misma entidad.

    La comparación se realiza contra la identidad canónica
    almacenada en la base de datos.
    """

    if not name:
        return None

    existing_items = item_repository.get_all()

    for existing in existing_items:

        existing_name = existing.get("name")

        if not existing_name:
            continue

        if names_match(
            name,
            existing_name,
            ITEM_SYNONYM_GROUPS,
        ):
            return existing

    return None

def save_extracted_item(data: dict):
    """
    Guarda o actualiza un Item extraído.

    Nunca crea un nuevo Item si el nombre corresponde
    a una entidad existente.
    """

    name = str(data.get("name") or "").strip()

    if not name:
        raise ValueError("Item name is required")

    existing = find_matching_item(name)

    if existing:

        payload = {
            "name": existing["name"],
            "description": data.get("description") or existing["description"] or "",
            "owner": data.get("owner") or existing["owner"] or "",
            "location": data.get("location") or existing["location"] or "",
            "significance": data.get("significance") or existing["significance"] or "",
            "notes": data.get("notes") or existing["notes"] or "",
        }

        item_repository.update(
            existing["id"],
            payload
        )

        return item_repository.get_by_id(
            existing["id"]
        )

    payload = {
        "name": name,
        "description": data.get("description") or "",
        "owner": data.get("owner") or "",
        "location": data.get("location") or "",
        "significance": data.get("significance") or "",
        "notes": data.get("notes") or "",
    }

    item_id = item_repository.create(payload)

    return item_repository.get_by_id(item_id)