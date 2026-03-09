// Chat App — MSAL.js authentication + Foundry agent interaction
// Fetches config from /api/config (no hardcoded IDs)

let msalInstance = null;
let currentAccount = null;
let lastResponseId = null;
let msalConfig = null;
let appInsights = null;
let pendingApprovalIds = null;
const sessionId = crypto.randomUUID();

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

async function initialize() {
    try {
        const resp = await fetch('/api/config');
        if (!resp.ok) {
            addSystemMessage('Failed to load configuration. Is the server configured?');
            return;
        }
        msalConfig = await resp.json();

        msalInstance = new msal.PublicClientApplication({
            auth: {
                clientId: msalConfig.clientId,
                authority: msalConfig.authority,
                redirectUri: window.location.origin,
            },
            cache: {
                cacheLocation: 'sessionStorage',
            },
        });

        await msalInstance.initialize();

        // Initialize Application Insights (if connection string provided)
        if (msalConfig.appInsightsConnectionString && window.Microsoft && window.Microsoft.ApplicationInsights) {
            var snippet = new Microsoft.ApplicationInsights.ApplicationInsights({
                config: {
                    connectionString: msalConfig.appInsightsConnectionString,
                }
            });
            appInsights = snippet.loadAppInsights();
            appInsights.trackPageView({ name: 'Chat' });
            appInsights.context.session.id = sessionId;
        }

        // Check for existing session
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
            currentAccount = accounts[0];
            onSignedIn();
        }
    } catch (err) {
        addSystemMessage('Error initializing: ' + err.message);
    }
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

async function handleAuth() {
    if (currentAccount) {
        msalInstance.logoutPopup({ account: currentAccount });
        currentAccount = null;
        onSignedOut();
    } else {
        try {
            const result = await msalInstance.loginPopup({
                scopes: msalConfig.scopes,
            });
            currentAccount = result.account;
            if (appInsights) appInsights.trackEvent({ name: 'UserSignedIn' });
            onSignedIn();
        } catch (err) {
            if (err.errorCode !== 'user_cancelled') {
                if (appInsights) appInsights.trackException({ exception: err });
                addSystemMessage('Sign-in failed: ' + err.message);
            }
        }
    }
}

async function getAccessToken() {
    try {
        const result = await msalInstance.acquireTokenSilent({
            scopes: msalConfig.scopes,
            account: currentAccount,
        });
        return result.accessToken;
    } catch {
        const result = await msalInstance.acquireTokenPopup({
            scopes: msalConfig.scopes,
            account: currentAccount,
        });
        return result.accessToken;
    }
}

function onSignedIn() {
    document.getElementById('userInfo').textContent = currentAccount.name || currentAccount.username;
    document.getElementById('authBtn').textContent = 'Sign out';
    document.getElementById('messageInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('suggestions').style.display = 'flex';
}

function onSignedOut() {
    document.getElementById('userInfo').textContent = '';
    document.getElementById('authBtn').textContent = 'Sign in';
    document.getElementById('messageInput').disabled = true;
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('welcome').style.display = 'flex';
    document.getElementById('suggestions').style.display = 'none';
    lastResponseId = null;
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

function useSuggestion(text) {
    document.getElementById('messageInput').value = text;
    sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    document.getElementById('welcome').style.display = 'none';
    addMessage('user', message);
    setLoading(true);

    try {
        const token = await getAccessToken();
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                access_token: token,
                previous_response_id: lastResponseId,
                session_id: sessionId,
            }),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            addSystemMessage('Error: ' + (err.detail || resp.statusText));
            setLoading(false);
            return;
        }

        const data = await resp.json();
        lastResponseId = data.response_id;
        if (appInsights) appInsights.trackEvent({
            name: 'ChatResponse',
            properties: { type: data.type, responseId: data.response_id, requestId: data.request_id }
        });
        handleResponse(data);
    } catch (err) {
        if (appInsights) appInsights.trackException({ exception: err });
        addSystemMessage('Error: ' + err.message);
    }

    setLoading(false);
}

function handleResponse(data) {
    // Render completed tool calls as collapsible cards
    if (data.tool_calls && data.tool_calls.length > 0) {
        for (const tc of data.tool_calls) {
            addToolCallCard(tc);
        }
    }

    if (data.approval_required) {
        setLoading(false);
        showApprovalUI(data.approval_ids);
    } else if (data.text) {
        addMessage('assistant', data.text);
    } else {
        addSystemMessage('Agent returned no text response.');
    }
}

// ---------------------------------------------------------------------------
// Tool call cards (completed calls)
// ---------------------------------------------------------------------------

function addToolCallCard(tc) {
    const container = document.getElementById('chatContainer');
    const div = document.createElement('div');
    div.className = 'message tool-call';

    const isError = !!tc.error;
    const statusClass = isError ? 'status-error' : 'status-success';
    const statusText = isError ? 'Error' : 'Success';

    // Format arguments
    let argsDisplay = '';
    if (tc.arguments) {
        try {
            const parsed = typeof tc.arguments === 'string' ? JSON.parse(tc.arguments) : tc.arguments;
            argsDisplay = JSON.stringify(parsed, null, 2);
        } catch {
            argsDisplay = String(tc.arguments);
        }
    }

    // Format output (truncate to 2000 chars)
    let outputDisplay = '';
    if (tc.error) {
        outputDisplay = tc.error;
    } else if (tc.output) {
        outputDisplay = typeof tc.output === 'string' ? tc.output : JSON.stringify(tc.output, null, 2);
        if (outputDisplay.length > 2000) {
            outputDisplay = outputDisplay.substring(0, 2000) + '\n... (truncated)';
        }
    }

    div.innerHTML =
        '<div class="message-avatar tool-avatar">T</div>' +
        '<div class="message-content tool-call-content">' +
            '<div class="tool-call-header" onclick="toggleToolDetails(this)">' +
                '<span class="tool-call-expand">&#9654;</span>' +
                '<span class="tool-call-name">' + escapeHtml(tc.name) + '</span>' +
                '<span class="tool-call-status ' + statusClass + '">' + statusText + '</span>' +
            '</div>' +
            '<div class="tool-call-details" style="display: none;">' +
                (argsDisplay ?
                    '<div class="tool-call-section">' +
                        '<div class="tool-call-section-label">Arguments</div>' +
                        '<pre class="tool-call-code">' + escapeHtml(argsDisplay) + '</pre>' +
                    '</div>' : '') +
                (outputDisplay ?
                    '<div class="tool-call-section">' +
                        '<div class="tool-call-section-label">Result</div>' +
                        '<pre class="tool-call-code tool-call-output">' + escapeHtml(outputDisplay) + '</pre>' +
                    '</div>' : '') +
            '</div>' +
        '</div>';

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function toggleToolDetails(header) {
    const details = header.nextElementSibling;
    const arrow = header.querySelector('.tool-call-expand');
    if (details.style.display === 'none') {
        details.style.display = 'block';
        arrow.innerHTML = '&#9660;';
    } else {
        details.style.display = 'none';
        arrow.innerHTML = '&#9654;';
    }
}

// ---------------------------------------------------------------------------
// Interactive approval UI
// ---------------------------------------------------------------------------

function showApprovalUI(approvalIds) {
    pendingApprovalIds = approvalIds;
    const container = document.getElementById('chatContainer');

    const div = document.createElement('div');
    div.className = 'message approval';
    div.id = 'approvalCard';

    let toolsHtml = '';
    for (const a of approvalIds) {
        let argsDisplay = '';
        if (a.arguments) {
            try {
                const parsed = typeof a.arguments === 'string' ? JSON.parse(a.arguments) : a.arguments;
                argsDisplay = JSON.stringify(parsed, null, 2);
            } catch {
                argsDisplay = String(a.arguments);
            }
        }

        toolsHtml +=
            '<div class="approval-tool">' +
                '<div class="approval-tool-name">' + escapeHtml(a.name) + '</div>' +
                (argsDisplay ?
                    '<pre class="tool-call-code">' + escapeHtml(argsDisplay) + '</pre>' : '') +
            '</div>';
    }

    div.innerHTML =
        '<div class="message-avatar approval-avatar">?</div>' +
        '<div class="message-content approval-content">' +
            '<div class="approval-header">' +
                '<span class="approval-badge">Requires approval</span>' +
                '<span class="approval-count">' + approvalIds.length + ' tool' + (approvalIds.length !== 1 ? 's' : '') + '</span>' +
            '</div>' +
            toolsHtml +
            '<div class="approval-actions">' +
                '<button class="approval-btn approve-btn" onclick="handleApprovalClick(true)">Approve</button>' +
                '<button class="approval-btn deny-btn" onclick="handleApprovalClick(false)">Deny</button>' +
            '</div>' +
        '</div>';

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

async function handleApprovalClick(approve) {
    const card = document.getElementById('approvalCard');
    if (!card || !pendingApprovalIds) return;

    // Update card to show decision
    const actions = card.querySelector('.approval-actions');
    const badge = card.querySelector('.approval-badge');
    if (actions) {
        actions.innerHTML = '<span class="approval-decision ' + (approve ? 'approved' : 'denied') + '">' +
            (approve ? 'Approved' : 'Denied') + '</span>';
    }
    if (badge) {
        badge.className = 'approval-badge ' + (approve ? 'badge-approved' : 'badge-denied');
        badge.textContent = approve ? 'Approved' : 'Denied';
    }
    card.removeAttribute('id');

    const ids = pendingApprovalIds.map(a => a.id);
    pendingApprovalIds = null;

    await submitApproval(ids, approve);
}

async function submitApproval(approvalIds, approve) {
    setLoading(true);

    try {
        const token = await getAccessToken();
        const resp = await fetch('/api/chat/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                access_token: token,
                previous_response_id: lastResponseId,
                approval_ids: approvalIds,
                approve: approve,
            }),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            addSystemMessage('Approval error: ' + (err.detail || resp.statusText));
            setLoading(false);
            return;
        }

        const data = await resp.json();
        lastResponseId = data.response_id;
        handleResponse(data);
    } catch (err) {
        addSystemMessage('Approval error: ' + err.message);
    }

    setLoading(false);
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function addMessage(role, text) {
    const container = document.getElementById('chatContainer');
    const avatar = role === 'user' ? 'U' : 'A';

    const div = document.createElement('div');
    div.className = 'message ' + role;
    div.innerHTML =
        '<div class="message-avatar">' + avatar + '</div>' +
        '<div class="message-content">' + escapeHtml(text) + '</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addSystemMessage(text) {
    const container = document.getElementById('chatContainer');
    const div = document.createElement('div');
    div.className = 'message system';
    div.innerHTML =
        '<div class="message-avatar">!</div>' +
        '<div class="message-content">' + escapeHtml(text) + '</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function setLoading(visible) {
    const sendBtn = document.getElementById('sendBtn');
    const input = document.getElementById('messageInput');
    sendBtn.disabled = visible;
    input.disabled = visible;

    // Show/hide loading indicator
    let loader = document.getElementById('loadingIndicator');
    if (visible && !loader) {
        loader = document.createElement('div');
        loader.id = 'loadingIndicator';
        loader.className = 'loading visible';
        loader.innerHTML =
            '<div class="loading-dots"><span></span><span></span><span></span></div>' +
            '<span class="loading-text">Agent is thinking...</span>';
        document.getElementById('chatContainer').appendChild(loader);
        document.getElementById('chatContainer').scrollTop =
            document.getElementById('chatContainer').scrollHeight;
    } else if (!visible && loader) {
        loader.remove();
        if (currentAccount) {
            input.disabled = false;
            sendBtn.disabled = false;
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

initialize();
