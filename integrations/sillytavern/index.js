import {
    eventSource,
    event_types,
    extension_settings,
    saveSettingsDebounced,
    getRequestHeaders,
} from '../../../../script.js';

const extensionName = 'campaign-manager';

const defaultSettings = {
    enabled: true,
    backendUrl: 'http://127.0.0.1:8765',
    contextQuery: 'Current campaign state',
};

let settings = {};

function loadSettings() {
    settings = extension_settings[extensionName];

    if (!settings) {
        settings = {};
        extension_settings[extensionName] = settings;
    }

    for (const [key, value] of Object.entries(defaultSettings)) {
        if (settings[key] === undefined) {
            settings[key] = value;
        }
    }

    saveSettingsDebounced();
}

function getBackendUrl() {
    return settings.backendUrl
        .trim()
        .replace(/\/+$/, '');
}

function setStatus(message, type = '') {
    const element = document.getElementById(
        'campaign-manager-status',
    );

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className =
        `campaign-manager-status ${type}`.trim();
}

async function getCampaignContext() {
    const backendUrl = getBackendUrl();

    if (!backendUrl) {
        throw new Error(
            'Campaign Manager backend URL is empty',
        );
    }

    const response = await fetch(
        `${backendUrl}/integration/context`,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify({
                query: settings.contextQuery,
            }),
        },
    );

    if (!response.ok) {
        let detail = '';

        try {
            const errorBody = await response.json();
            detail = errorBody.detail ?? '';
        } catch {
            // Ignore invalid error bodies.
        }

        throw new Error(
            `Campaign Manager returned ${response.status}` +
            (detail ? `: ${detail}` : ''),
        );
    }

    return await response.json();
}

async function testConnection() {
    setStatus('Connecting...');

    try {
        const result = await getCampaignContext();

        const campaignName =
            result?.campaign?.name ?? 'Unknown campaign';

        setStatus(
            `Connected: ${campaignName}`,
            'success',
        );

        console.info(
            '[Campaign Manager] Context received:',
            result,
        );

        return result;
    } catch (error) {
        console.error(
            '[Campaign Manager] Connection failed:',
            error,
        );

        setStatus(
            `Connection failed: ${error.message}`,
            'error',
        );

        throw error;
    }
}

function bindSettings() {
    const enabledElement = document.getElementById(
        'campaign-manager-enabled',
    );

    const urlElement = document.getElementById(
        'campaign-manager-url',
    );

    const queryElement = document.getElementById(
        'campaign-manager-query',
    );

    const testElement = document.getElementById(
        'campaign-manager-test',
    );

    if (
        !enabledElement ||
        !urlElement ||
        !queryElement ||
        !testElement
    ) {
        console.error(
            '[Campaign Manager] Settings elements not found',
        );

        return;
    }

    enabledElement.checked = Boolean(
        settings.enabled,
    );

    urlElement.value = settings.backendUrl;

    queryElement.value = settings.contextQuery;

    enabledElement.addEventListener(
        'change',
        () => {
            settings.enabled =
                enabledElement.checked;

            saveSettingsDebounced();
        },
    );

    urlElement.addEventListener(
        'change',
        () => {
            settings.backendUrl =
                urlElement.value.trim();

            saveSettingsDebounced();
        },
    );

    queryElement.addEventListener(
        'change',
        () => {
            settings.contextQuery =
                queryElement.value.trim();

            saveSettingsDebounced();
        },
    );

    testElement.addEventListener(
        'click',
        async () => {
            try {
                await testConnection();
            } catch {
                // Error already displayed.
            }
        },
    );
}

async function initializeExtension() {
    loadSettings();

    bindSettings();

    console.info(
        '[Campaign Manager] Extension initialized',
    );
}

eventSource.on(
    event_types.APP_READY,
    initializeExtension,
);