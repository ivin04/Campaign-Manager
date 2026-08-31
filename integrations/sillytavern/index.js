import {
    extension_settings,
} from '../../extensions.js';

const extensionName = 'campaign-manager';

const defaultSettings = {
    enabled: true,
    backendUrl: 'http://127.0.0.1:8765',
    contextQuery: 'Quiero conocer el estado actual de la campaña.',
};

let settings = null;

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

function initializeExtension() {
    const currentSettings =
        getSettings();

    log(
        'Extension loaded.',
        currentSettings,
    );

    createSettingsUi();
}

initializeExtension();