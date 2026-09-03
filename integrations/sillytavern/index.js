import {
    extension_settings,
    getContext,
} from '../../extensions.js';

import {
    chat,
    eventSource,
    event_types,
    getCurrentChatId,
} from '../../../script.js';


const extensionName = 'campaign-manager';

const defaultSettings = {
    enabled: true,
    backendUrl: 'http://127.0.0.1:8765',
    contextQuery: 'Quiero conocer el estado actual de la campaña.',
};

let settings = null;

let lastProcessedTurnKey = null;

// ============================================================
// CAMPAIGN MANAGER CONTEXT FOR GENERATION
// ============================================================

async function getCampaignManagerGenerationContext(query) {
    const currentSettings = getSettings();

    if (!currentSettings.enabled) {
        return "";
    }

    const backendUrl = currentSettings.backendUrl
        .trim()
        .replace(/\/+$/, "");

    if (!backendUrl) {
        warn("Backend URL is empty. Context was not requested.");
        return "";
    }

    const normalizedQuery =
        typeof query === "string"
            ? query.trim()
            : "";

    if (!normalizedQuery) {
        warn("Generation context query is empty.");
        return "";
    }

    try {
        const response = await fetch(
            `${backendUrl}/integration/context`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    query: normalizedQuery,
                }),
            },
        );

        let responseBody = null;

        try {
            responseBody = await response.json();
        } catch {
            responseBody = null;
        }

        if (!response.ok) {
            const detail = responseBody?.detail;

            let errorMessage;

            if (typeof detail === "string") {
                errorMessage = detail;
            } else if (detail !== undefined) {
                errorMessage = JSON.stringify(detail);
            } else {
                errorMessage = "Unknown backend error";
            }

            throw new Error(
                `HTTP ${response.status}: ${errorMessage}`,
            );
        }

        if (!responseBody || typeof responseBody !== "object") {
            throw new Error(
                "Campaign Manager returned an invalid context response",
            );
        }

        /*
         * /integration/context returns:
         *
         * {
         *     campaign: {...},
         *     session: ...,
         *     active_character: ...,
         *     query: "...",
         *     context: {
         *         entities: [...],
         *         items: [...],
         *         ...
         *         context: "..."
         *     }
         * }
         *
         * The actual text that must be injected into
         * SillyTavern is responseBody.context.context.
         */

        if (
            !responseBody.context ||
            typeof responseBody.context !== "object"
        ) {
            throw new Error(
                "Campaign Manager response does not contain a context object",
            );
        }

        if (typeof responseBody.context.context !== "string") {
            throw new Error(
                "Campaign Manager context object does not contain a context string",
            );
        }

        return responseBody.context.context.trim();
    } catch (error) {
        console.warn(
            "[Campaign Manager] Failed to obtain generation context:",
            error,
        );

        return "";
    }
}


// ============================================================
// SILLYTAVERN GENERATION INTERCEPTOR
// ============================================================

globalThis.campaignManagerGenerateInterceptor =
    async function (
        chatMessages,
        contextSize,
        abort,
        type,
    ) {
        const currentSettings =
            getSettings();

        /*
         * SillyTavern uses quiet generations for internal
         * operations such as chat summarization.
         *
         * Campaign Manager world state is generation context
         * for the actual narrative response, not for internal
         * SillyTavern processing.
         *
         * Do not inject Campaign Manager context into quiet
         * generations, and explicitly clear any previous
         * extension prompt so it cannot leak into the quiet
         * generation.
         */
        if (type === 'quiet') {
            await clearCampaignManagerContext();

            log(
                'Skipping Campaign Manager context for quiet generation.',
            );

            return;
        }

        if (!currentSettings.enabled) {
            await clearCampaignManagerContext();
            return;
        }

        if (!Array.isArray(chatMessages)) {
            warn(
                'Generation interceptor received invalid chat.',
            );

            await clearCampaignManagerContext();
            return;
        }

        if (chatMessages.length === 0) {
            await clearCampaignManagerContext();
            return;
        }

        /*
         * Find the most recent user message.
         *
         * Do not assume that the user message is the
         * last element of the array because other
         * extensions may modify the generation context.
         */
        let playerInput = '';

        for (
            let index = chatMessages.length - 1;
            index >= 0;
            index -= 1
        ) {
            const message =
                chatMessages[index];

            if (
                message &&
                message.is_user === true &&
                typeof message.mes === 'string'
            ) {
                playerInput =
                    message.mes.trim();

                break;
            }
        }

        if (!playerInput) {
            warn(
                'Could not find a user message for generation context.',
            );

            await clearCampaignManagerContext();
            return;
        }

        const context =
            await getCampaignManagerGenerationContext(
                playerInput,
            );

        if (!context) {
            await clearCampaignManagerContext();
            return;
        }

        await injectCampaignManagerContext(
            context,
        );

        log(
            'Campaign Manager context injected.',
            {
                generationType: type,
                contextSize,
                queryLength:
                    playerInput.length,
                contextLength:
                    context.length,
            },
        );
    };


// ============================================================
// CAMPAIGN MANAGER PROMPT INJECTION
// ============================================================

const campaignManagerPromptId =
    'campaign-manager-world-state';

async function injectCampaignManagerContext(context) {
    if (!context) {
        await clearCampaignManagerContext();
        return;
    }

    const tavernContext = getContext();

    if (
        !tavernContext ||
        typeof tavernContext.setExtensionPrompt !== 'function'
    ) {
        warn(
            'SillyTavern setExtensionPrompt API is unavailable.',
        );

        return;
    }

    const prompt =
        [
            '[CAMPAIGN MANAGER - CURRENT WORLD STATE]',
            context.trim(),
            '[END CAMPAIGN MANAGER CONTEXT]',
        ].join('\n');

    /*
     * position = 0:
     *   After Main Prompt / Story String
     *
     * depth = 0:
     *   Current generation depth.
     *
     * scan = false:
     *   Campaign Manager context must not participate
     *   in World Info keyword scanning.
     *
     * role = 0:
     *   System message.
     */
    await tavernContext.setExtensionPrompt(
        campaignManagerPromptId,
        prompt,
        0,
        0,
        false,
        0,
    );
}

async function clearCampaignManagerContext() {
    const tavernContext = getContext();

    if (
        !tavernContext ||
        typeof tavernContext.setExtensionPrompt !== 'function'
    ) {
        return;
    }

    await tavernContext.setExtensionPrompt(
        campaignManagerPromptId,
        '',
        -1,
        0,
        false,
        0,
    );
}


function log(...args) {
    console.log(
        '[Campaign Manager]',
        ...args,
    );
}

function warn(...args) {
    console.warn(
        '[Campaign Manager]',
        ...args,
    );
}

function getSettings() {
    if (!extension_settings[extensionName]) {
        extension_settings[extensionName] = {
            ...defaultSettings,
        };
    }

    const stored =
        extension_settings[extensionName];

    if (
        typeof stored.enabled !== 'boolean'
    ) {
        stored.enabled =
            defaultSettings.enabled;
    }

    if (
        typeof stored.backendUrl !== 'string' ||
        !stored.backendUrl.trim()
    ) {
        stored.backendUrl =
            defaultSettings.backendUrl;
    }

    if (
        typeof stored.contextQuery !== 'string' ||
        !stored.contextQuery.trim()
    ) {
        stored.contextQuery =
            defaultSettings.contextQuery;
    }

    settings = stored;

    return settings;
}

function saveSettings() {
    if (
        typeof saveSettingsDebounced ===
        'function'
    ) {
        saveSettingsDebounced();
    }
}

function createSettingsUi() {
    const existingElement =
        document.getElementById(
            'campaign-manager-extension-settings',
        );

    if (existingElement) {
        return;
    }

    const settingsContainer =
        document.createElement('div');

    settingsContainer.id =
        'campaign-manager-extension-settings';

    settingsContainer.className =
        'campaign-manager-settings';

    settingsContainer.innerHTML = `
        <div class="inline-drawer">
            <div class="inline-drawer-toggle inline-drawer-header">
                <b>Campaign Manager</b>
                <div
                    class="inline-drawer-icon fa-solid fa-circle-chevron-down"
                ></div>
            </div>

            <div class="inline-drawer-content">
                <label class="checkbox_label">
                    <input
                        id="campaign-manager-enabled"
                        type="checkbox"
                    >
                    <span>Enabled</span>
                </label>

                <div class="campaign-manager-setting">
                    <label for="campaign-manager-url">
                        Backend URL
                    </label>

                    <input
                        id="campaign-manager-url"
                        type="text"
                        class="text_pole"
                        placeholder="http://127.0.0.1:8765"
                    >
                </div>

                <div class="campaign-manager-setting">
                    <label for="campaign-manager-query">
                        Context query
                    </label>

                    <input
                        id="campaign-manager-query"
                        type="text"
                        class="text_pole"
                        placeholder="Quiero conocer el estado actual de la campaña."
                    >
                </div>

                <div class="campaign-manager-actions">
                    <button
                        id="campaign-manager-test"
                        class="menu_button"
                        type="button"
                    >
                        Test connection
                    </button>
                </div>

                <div
                    id="campaign-manager-status"
                    class="campaign-manager-status"
                >
                    Not tested
                </div>
            </div>
        </div>
    `;

    const extensionsContainer =
        document.querySelector(
            '#extensions_settings',
        );

    if (!extensionsContainer) {
        warn(
            'Could not find #extensions_settings.',
        );

        return;
    }

    extensionsContainer.appendChild(
        settingsContainer,
    );

    bindSettingsUi();
}

function bindSettingsUi() {
    const currentSettings =
        getSettings();

    const enabledElement =
        document.getElementById(
            'campaign-manager-enabled',
        );

    const urlElement =
        document.getElementById(
            'campaign-manager-url',
        );

    const queryElement =
        document.getElementById(
            'campaign-manager-query',
        );

    const testElement =
        document.getElementById(
            'campaign-manager-test',
        );

    if (
        !enabledElement ||
        !urlElement ||
        !queryElement ||
        !testElement
    ) {
        warn(
            'Could not initialize settings UI.',
        );

        return;
    }

    enabledElement.checked =
        Boolean(
            currentSettings.enabled,
        );

    urlElement.value =
        currentSettings.backendUrl;

    queryElement.value =
        currentSettings.contextQuery;

    enabledElement.addEventListener(
        'change',
        () => {
            currentSettings.enabled =
                enabledElement.checked;

            saveSettings();
        },
    );

    urlElement.addEventListener(
        'change',
        () => {
            currentSettings.backendUrl =
                urlElement.value.trim();

            saveSettings();
        },
    );

    queryElement.addEventListener(
        'change',
        () => {
            currentSettings.contextQuery =
                queryElement.value.trim();

            saveSettings();
        },
    );

    testElement.addEventListener(
        'click',
        testConnection,
    );
}

async function testConnection() {
    const currentSettings =
        getSettings();

    const statusElement =
        document.getElementById(
            'campaign-manager-status',
        );

    if (!statusElement) {
        return;
    }

    if (!currentSettings.enabled) {
        statusElement.textContent =
            'Extension disabled.';

        return;
    }

    const backendUrl =
        currentSettings.backendUrl
            .trim()
            .replace(/\/+$/, '');

    const query =
        currentSettings.contextQuery
            .trim();

    if (!backendUrl) {
        statusElement.textContent =
            'Backend URL is empty.';

        return;
    }

    if (!query) {
        statusElement.textContent =
            'Context query is empty.';

        return;
    }

    statusElement.textContent =
        'Connecting...';

    try {
        const response =
            await fetch(
                `${backendUrl}/integration/context`,
                {
                    method: 'POST',

                    headers: {
                        'Content-Type':
                            'application/json',

                        'Accept':
                            'application/json',
                    },

                    body: JSON.stringify({
                        query: query,
                    }),
                },
            );

        const responseBody =
            await response.json();

        if (!response.ok) {
            const detail =
                responseBody?.detail;

            let errorMessage;

            if (typeof detail === 'string') {
                errorMessage = detail;
            } else if (detail !== undefined) {
                errorMessage =
                    JSON.stringify(detail);
            } else {
                errorMessage =
                    'Unknown backend error';
            }

            throw new Error(
                `HTTP ${response.status}: ${errorMessage}`,
            );
        }

        if (
            !responseBody?.context ||
            typeof responseBody.context !== 'object'
        ) {
            throw new Error(
                'Campaign Manager response does not contain a context object.',
            );
        }

        if (
            typeof responseBody.context.context !== 'string'
        ) {
            throw new Error(
                'Campaign Manager context object does not contain a context string.',
            );
        }

        const campaignName =
            responseBody?.campaign?.name ??
            'Unknown campaign';

        statusElement.textContent =
            `Connected: ${campaignName}`;

        log(
            'Context received:',
            responseBody,
        );
    } catch (error) {
        console.error(
            '[Campaign Manager] Connection failed:',
            error,
        );

        statusElement.textContent =
            `Connection failed: ${error.message}`;
    }
}

function registerTurnDetection() {
    if (
        !eventSource ||
        !event_types
    ) {
        warn(
            'SillyTavern event system is unavailable.',
        );

        return;
    }

    const messageReceivedEvent =
        event_types.MESSAGE_RECEIVED;

    if (!messageReceivedEvent) {
        warn(
            'MESSAGE_RECEIVED event is unavailable.',
        );

        return;
    }

    eventSource.on(
        messageReceivedEvent,
        onMessageReceived,
    );

    log(
        'Turn detection registered:',
        messageReceivedEvent,
    );
}

async function createStableTurnId(
    playerMessageIndex,
    narrativeMessageIndex,
    playerInput,
    narrativeText,
) {
    let chatId = '';

    try {
        if (typeof getCurrentChatId === 'function') {
            chatId = String(
                getCurrentChatId() ?? '',
            );
        }
    } catch (error) {
        warn(
            'Could not obtain current SillyTavern chat id.',
            error,
        );
    }

    const rawValue = [
        'campaign-manager-v1',
        chatId,
        playerMessageIndex,
        narrativeMessageIndex,
        playerInput,
        narrativeText,
    ].join('\n');

    const encoder =
        new TextEncoder();

    const data =
        encoder.encode(rawValue);

    const hashBuffer =
        await crypto.subtle.digest(
            'SHA-256',
            data,
        );

    const hashArray =
        Array.from(
            new Uint8Array(
                hashBuffer,
            ),
        );

    const hashHex =
        hashArray
            .map(
                byte =>
                    byte
                        .toString(16)
                        .padStart(2, '0'),
            )
            .join('');

    return hashHex;
}

async function sendTurnToBackend(
    externalTurnId,
    playerInput,
    narrativeText,
) {
    const currentSettings =
        getSettings();

    const backendUrl =
        currentSettings.backendUrl
            .trim()
            .replace(/\/+$/, '');

    if (!backendUrl) {
        warn(
            'Backend URL is empty. Turn was not sent.',
        );

        return null;
    }

    if (
        typeof externalTurnId !== 'string' ||
        !externalTurnId.trim()
    ) {
        throw new Error(
            'externalTurnId is required.',
        );
    }

    const payload = {
        external_turn_id:
            externalTurnId,

        player_input:
            playerInput,

        narrative:
            narrativeText,
    };

    log(
        'Sending turn to Campaign Manager:',
        payload,
    );

    const response =
        await fetch(
            `${backendUrl}/integration/turn`,
            {
                method: 'POST',

                headers: {
                    'Content-Type':
                        'application/json',

                    'Accept':
                        'application/json',
                },

                body: JSON.stringify(
                    payload,
                ),
            },
        );

    let responseBody = null;

    try {
        responseBody =
            await response.json();
    } catch {
        responseBody = null;
    }

    if (!response.ok) {
        const detail =
            responseBody?.detail;

        let errorMessage;

        if (typeof detail === 'string') {
            errorMessage = detail;
        } else if (
            detail !== undefined
        ) {
            errorMessage =
                JSON.stringify(detail);
        } else {
            errorMessage =
                'Unknown backend error';
        }

        throw new Error(
            `HTTP ${response.status}: ${errorMessage}`,
        );
    }

    log(
        'Turn processed successfully:',
        responseBody,
    );

    return responseBody;
}


async function onMessageReceived() {
    const currentSettings =
        getSettings();

    if (!currentSettings.enabled) {
        return;
    }

    if (!Array.isArray(chat)) {
        warn(
            'SillyTavern chat is unavailable.',
        );

        return;
    }

    if (chat.length < 2) {
        warn(
            'Not enough messages to process a turn.',
        );

        return;
    }

    const narrativeIndex =
        chat.length - 1;

    const narrative =
        chat[narrativeIndex];

    if (!narrative) {
        return;
    }

    if (narrative.is_user) {
        warn(
            'Last message is not an assistant message. Skipping.',
        );

        return;
    }

    const playerMessageIndex =
        chat.length - 2;

    const playerMessage =
        chat[playerMessageIndex];

    if (!playerMessage) {
        warn(
            'Player message not found.',
        );

        return;
    }

    if (!playerMessage.is_user) {
        warn(
            'Previous message is not a user message. Skipping.',
        );

        return;
    }

    const playerInput =
        typeof playerMessage.mes === 'string'
            ? playerMessage.mes.trim()
            : '';

    const narrativeText =
        typeof narrative.mes === 'string'
            ? narrative.mes.trim()
            : '';

    if (!playerInput) {
        warn(
            'Player input is empty. Skipping.',
        );

        return;
    }

    if (!narrativeText) {
        warn(
            'Narrative is empty. Skipping.',
        );

        return;
    }

    let externalTurnId;

    try {
        externalTurnId =
            await createStableTurnId(
                playerMessageIndex,
                narrativeIndex,
                playerInput,
                narrativeText,
            );

    } catch (error) {
        console.error(
            '[Campaign Manager] Failed to create stable turn id:',
            error,
        );

        return;
    }

    if (
        lastProcessedTurnKey ===
        externalTurnId
    ) {
        log(
            'Turn already processed locally. Skipping duplicate.',
        );

        return;
    }

    lastProcessedTurnKey =
        externalTurnId;

    log(
        'Turn detected:',
        {
            external_turn_id:
                externalTurnId,

            player_input:
                playerInput,

            narrative:
                narrativeText,
        },
    );

    /*
     * Do not await the backend request from
     * the MESSAGE_RECEIVED event handler.
     *
     * SillyTavern must be allowed to finish
     * its own message lifecycle without our
     * HTTP request remaining attached to it.
     */
    void sendTurnToBackend(
        externalTurnId,
        playerInput,
        narrativeText,
    ).catch((error) => {
        /*
         * Allow retry if the backend failed.
         */
        if (
            lastProcessedTurnKey ===
            externalTurnId
        ) {
            lastProcessedTurnKey =
                null;
        }

        console.error(
            '[Campaign Manager] Failed to process turn:',
            error,
        );
    });
}


function initializeExtension() {
    const currentSettings =
        getSettings();

    log(
        'Extension loaded.',
        currentSettings,
    );

    createSettingsUi();

    registerTurnDetection();
}

initializeExtension();