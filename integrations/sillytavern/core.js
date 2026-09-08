export function buildRetrievalQuery(
    configuredQuery,
    playerInput,
) {
    const normalizedConfiguredQuery =
        typeof configuredQuery === "string"
            ? configuredQuery.trim()
            : "";

    const normalizedPlayerInput =
        typeof playerInput === "string"
            ? playerInput.trim()
            : "";

    if (
        !normalizedConfiguredQuery ||
        !normalizedPlayerInput
    ) {
        return "";
    }

    return [
        normalizedConfiguredQuery,
        "",
        "Acción actual del jugador:",
        normalizedPlayerInput,
    ].join("\n");
}