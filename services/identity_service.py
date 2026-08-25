import re
import unicodedata


def normalize_text(value: str) -> str:
    """
    Normaliza texto para realizar comparaciones.

    No modifica el valor original guardado en la base de datos.
    """
    if not value:
        return ""

    value = str(value)

    value = unicodedata.normalize(
        "NFD",
        value
    )

    value = "".join(
        char
        for char in value
        if unicodedata.category(char) != "Mn"
    )

    value = value.lower()

    value = re.sub(
        r"[^\w\s]",
        "",
        value,
        flags=re.UNICODE
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def tokenize(value: str) -> list[str]:
    """
    Convierte un nombre normalizado en tokens.
    """
    normalized = normalize_text(value)

    if not normalized:
        return []

    return normalized.split()


def canonicalize_tokens(
    tokens: list[str],
    synonym_groups: list[list[str]] | None = None,
) -> list[str]:
    """
    Sustituye sinónimos por la forma canónica del grupo.

    Ejemplo:

        anillo
        aro
        sortija

    pueden pertenecer al mismo grupo.
    """

    if not synonym_groups:
        return sorted(tokens)

    canonical_map = {}

    for group in synonym_groups:
        if not group:
            continue

        canonical = normalize_text(group[0])

        for synonym in group:
            normalized = normalize_text(synonym)

            if normalized:
                canonical_map[normalized] = canonical

    result = [
        canonical_map.get(token, token)
        for token in tokens
    ]

    return sorted(result)


def names_match(
    first: str,
    second: str,
    synonym_groups: list[list[str]] | None = None,
) -> bool:
    """
    Determina si dos nombres representan probablemente
    la misma identidad.

    El nombre original nunca se modifica.
    """

    first_normalized = normalize_text(first)
    second_normalized = normalize_text(second)

    if not first_normalized or not second_normalized:
        return False

    if first_normalized == second_normalized:
        return True

    first_tokens = tokenize(first_normalized)
    second_tokens = tokenize(second_normalized)

    first_canonical = canonicalize_tokens(
        first_tokens,
        synonym_groups,
    )

    second_canonical = canonicalize_tokens(
        second_tokens,
        synonym_groups,
    )

    return first_canonical == second_canonical