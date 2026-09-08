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

export function buildStableTurnIdentityInput(
    chatId,
    playerMessageIndex,
) {
    if (
        typeof chatId !== 'string' ||
        !chatId.trim()
    ) {
        throw new Error(
            'chatId is required.',
        );
    }

    if (
        !Number.isInteger(playerMessageIndex) ||
        playerMessageIndex < 0
    ) {
        throw new Error(
            'playerMessageIndex must be a non-negative integer.',
        );
    }

    return [
        'campaign-manager-turn-v2',
        chatId.trim(),
        String(playerMessageIndex),
    ].join('|');
}


export class TurnState {
    constructor() {
        this.turnVersions =
            new Map();

        this.turnNarratives =
            new Map();

        this.lastProcessedTurnVersionKey =
            null;
    }

    async getVersion(
        externalTurnId,
        narrativeText,
        getPersistedState,
    ) {
        if (
            typeof externalTurnId !== 'string' ||
            !externalTurnId.trim()
        ) {
            throw new Error(
                'externalTurnId is required.',
            );
        }

        if (
            typeof narrativeText !== 'string' ||
            !narrativeText.trim()
        ) {
            throw new Error(
                'narrativeText is required.',
            );
        }

        if (
            typeof getPersistedState !== 'function'
        ) {
            throw new Error(
                'getPersistedState must be a function.',
            );
        }

        const normalizedExternalTurnId =
            externalTurnId.trim();

        const normalizedNarrative =
            narrativeText.trim();

        /*
         * The backend is authoritative.
         *
         * If this local state does not know the turn yet,
         * restore the currently active backend version before
         * deciding whether this is an existing narrative or
         * a new regeneration.
         */
        if (
            !this.turnVersions.has(
                normalizedExternalTurnId,
            )
        ) {
            const persistedState =
                await getPersistedState(
                    normalizedExternalTurnId,
                );

            if (
                !persistedState ||
                typeof persistedState !== 'object'
            ) {
                throw new Error(
                    'Persisted turn state is invalid.',
                );
            }

            if (
                !Number.isInteger(
                    persistedState.active_version,
                ) ||
                persistedState.active_version < 0
            ) {
                throw new Error(
                    'Persisted active version is invalid.',
                );
            }

            this.turnVersions.set(
                normalizedExternalTurnId,
                persistedState.active_version,
            );

            if (
                persistedState.exists &&
                typeof persistedState.narrative ===
                    'string'
            ) {
                this.turnNarratives.set(
                    normalizedExternalTurnId,
                    persistedState.narrative.trim(),
                );
            } else {
                this.turnNarratives.delete(
                    normalizedExternalTurnId,
                );
            }
        }

        const previousNarrative =
            this.turnNarratives.get(
                normalizedExternalTurnId,
            );

        const previousVersion =
            this.turnVersions.get(
                normalizedExternalTurnId,
            ) ?? 0;

        /*
         * Same narrative:
         * same version.
         *
         * This includes retries after a backend failure.
         */
        if (
            previousNarrative ===
            normalizedNarrative
        ) {
            return previousVersion;
        }

        /*
         * Different narrative:
         * regeneration/swipe.
         */
        const nextVersion =
            previousVersion + 1;

        this.turnVersions.set(
            normalizedExternalTurnId,
            nextVersion,
        );

        this.turnNarratives.set(
            normalizedExternalTurnId,
            normalizedNarrative,
        );

        return nextVersion;
    }

    tryMarkProcessing(
        externalTurnId,
        turnVersion,
    ) {
        const turnVersionKey =
            `${externalTurnId}:${turnVersion}`;

        if (
            this.lastProcessedTurnVersionKey ===
            turnVersionKey
        ) {
            return false;
        }

        this.lastProcessedTurnVersionKey =
            turnVersionKey;

        return true;
    }

    markFailed(
        externalTurnId,
        turnVersion,
    ) {
        const turnVersionKey =
            `${externalTurnId}:${turnVersion}`;

        /*
         * Only unlock the turn if the failed request is
         * still the latest locally processed version.
         */
        if (
            this.lastProcessedTurnVersionKey ===
            turnVersionKey
        ) {
            this.lastProcessedTurnVersionKey =
                null;
        }
    }

    reset() {
        this.lastProcessedTurnVersionKey =
            null;

        this.turnVersions.clear();
        this.turnNarratives.clear();
    }
}