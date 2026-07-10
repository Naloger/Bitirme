/**
 * Salience Agent — Chat UI Logic
 *
 * Handles:
 *   • Sending user messages to POST /api/chat/stream
 *   • Reading the NDJSON stream line-by-line
 *   • Rendering status / node_update / final_summary / error events
 *   • Conversation history (in-memory)
 *   • Auto-resize textarea, keyboard shortcuts
 */

(() => {
    "use strict";

    // ── DOM references ─────────────────────────────────────────
    const $messages     = document.getElementById("chat-messages");
    const $input        = document.getElementById("chat-input");
    const $btnSend      = document.getElementById("btn-send");
    const $btnStop      = document.getElementById("btn-stop");
    const $btnNewChat   = document.getElementById("btn-new-chat");
    const $btnClear     = document.getElementById("btn-clear-chat");
    const $btnSidebar   = document.getElementById("btn-toggle-sidebar");
    const $sidebar      = document.getElementById("sidebar");
    const $welcome      = document.getElementById("welcome-screen");
    const $chatTitle    = document.getElementById("chat-title");
    const $convList     = document.getElementById("conversation-list");
    const $statusDot    = document.querySelector(".status-dot");
    const $statusText   = document.querySelector(".status-text");

    // ── State ──────────────────────────────────────────────────
    let conversations   = [];          // [{id, title, messages:[]}]
    let activeConvId    = null;
    let abortController = null;
    let isStreaming      = false;

    // ── LocalStorage Persistence ────────────────────────────────
    const STORAGE_KEY_CONVS = "salience_conversations";
    const STORAGE_KEY_ACTIVE = "salience_active_conv_id";

    function saveToLocalStorage() {
        try {
            localStorage.setItem(STORAGE_KEY_CONVS, JSON.stringify(conversations));
            localStorage.setItem(STORAGE_KEY_ACTIVE, activeConvId || "");
        } catch (e) {
            console.error("Failed to save to localStorage:", e);
        }
    }

    function loadFromLocalStorage() {
        try {
            const storedConvs = localStorage.getItem(STORAGE_KEY_CONVS);
            const storedActive = localStorage.getItem(STORAGE_KEY_ACTIVE);
            if (storedConvs) {
                conversations = JSON.parse(storedConvs);
            }
            if (storedActive && conversations.some(c => c.id === storedActive)) {
                activeConvId = storedActive;
            } else if (conversations.length > 0) {
                activeConvId = conversations[0].id;
            } else {
                activeConvId = null;
            }
        } catch (e) {
            console.error("Failed to load from localStorage:", e);
            conversations = [];
            activeConvId = null;
        }
    }

    // ── Helpers ────────────────────────────────────────────────
    const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
    const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const esc = (s) => {
        const d = document.createElement("div");
        d.textContent = s;
        return d.innerHTML;
    };

    // ── Conversation Management ────────────────────────────────
    function createConversation(title = "New Conversation") {
        const conv = { id: uid(), title, messages: [] };
        conversations.unshift(conv);
        activeConvId = conv.id;
        renderConvList();
        clearMessages();
        $chatTitle.textContent = conv.title;
        saveToLocalStorage();
        return conv;
    }

    function getActiveConv() {
        return conversations.find(c => c.id === activeConvId);
    }

    function switchConversation(id) {
        activeConvId = id;
        const conv = getActiveConv();
        if (!conv) return;
        $chatTitle.textContent = conv.title;
        clearMessages();
        conv.messages.forEach(m => {
            if (m.role === "user") appendUserBubble(m.text, m.time, false);
            else                  replayAssistantMessage(m);
        });
        renderConvList();
        saveToLocalStorage();
    }

    function renderConvList() {
        $convList.innerHTML = conversations.map(c => `
            <div class="conv-item ${c.id === activeConvId ? "active" : ""}" data-id="${c.id}">
                <div class="conv-item-left">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                    </svg>
                    <span>${esc(c.title)}</span>
                </div>
                <button class="btn-delete-conv" data-id="${c.id}" title="Delete conversation">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `).join("");

        $convList.querySelectorAll(".conv-item").forEach(el => {
            el.addEventListener("click", (e) => {
                if (e.target.closest(".btn-delete-conv")) return;
                switchConversation(el.dataset.id);
            });
        });

        $convList.querySelectorAll(".btn-delete-conv").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                deleteConversation(btn.dataset.id);
            });
        });
    }

    function deleteConversation(id) {
        conversations = conversations.filter(c => c.id !== id);
        if (activeConvId === id) {
            if (conversations.length > 0) {
                activeConvId = conversations[0].id;
                switchConversation(activeConvId);
            } else {
                createConversation();
            }
        } else {
            renderConvList();
        }
        saveToLocalStorage();
    }

    // ── Message Rendering ──────────────────────────────────────
    function hideWelcome() {
        if ($welcome) $welcome.style.display = "none";
    }

    function showWelcome() {
        if ($welcome) $welcome.style.display = "";
    }

    function clearMessages() {
        // Remove everything except #welcome-screen
        Array.from($messages.children).forEach(child => {
            if (child.id !== "welcome-screen") child.remove();
        });
        const conv = getActiveConv();
        if (!conv || conv.messages.length === 0) showWelcome();
        else hideWelcome();
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            $messages.scrollTop = $messages.scrollHeight;
        });
    }

    function appendUserBubble(text, time, scroll = true) {
        hideWelcome();
        const row = document.createElement("div");
        row.className = "message-row user";
        row.innerHTML = `
            <div class="msg-content">
                <div class="msg-bubble">${esc(text)}</div>
                <div class="msg-meta"><span>${time}</span></div>
            </div>
            <div class="msg-avatar">U</div>
        `;
        $messages.appendChild(row);
        if (scroll) scrollToBottom();
    }

    /**
     * Create the assistant message row with a typing indicator.
     * Returns an object { row, eventsContainer, setDone }
     */
    function createAssistantRow() {
        hideWelcome();
        const row = document.createElement("div");
        row.className = "message-row assistant";
        row.innerHTML = `
            <div class="msg-avatar">S</div>
            <div class="msg-content">
                <div class="msg-bubble">
                    <div class="typing-indicator"><span></span><span></span><span></span></div>
                    <div class="stream-events"></div>
                    <div class="result-text hidden"></div>
                </div>
                <div class="msg-meta"><span class="msg-time"></span></div>
            </div>
        `;
        $messages.appendChild(row);
        scrollToBottom();

        const eventsContainer = row.querySelector(".stream-events");
        const resultContainer = row.querySelector(".result-text");
        const typingEl        = row.querySelector(".typing-indicator");
        const timeEl          = row.querySelector(".msg-time");

        return {
            row,
            eventsContainer,
            resultContainer,
            appendEvent(html) {
                eventsContainer.insertAdjacentHTML("beforeend", html);
                scrollToBottom();
            },
            showResult(text) {
                resultContainer.innerHTML = formatMarkdown(text);
                resultContainer.classList.remove("hidden");
                scrollToBottom();
            },
            setDone() {
                typingEl.remove();
                timeEl.textContent = now();
            }
        };
    }

    /** Replay a stored assistant message (no streaming, instant render). */
    function replayAssistantMessage(msg) {
        hideWelcome();
        const row = document.createElement("div");
        row.className = "message-row assistant";
        let eventsHtml = msg.events.map(e => renderEventHTML(e)).join("");
        let resultHtml = msg.result ? `<div class="result-text">${formatMarkdown(msg.result)}</div>` : "";

        row.innerHTML = `
            <div class="msg-avatar">S</div>
            <div class="msg-content">
                <div class="msg-bubble">
                    <div class="stream-events">${eventsHtml}</div>
                    ${resultHtml}
                </div>
                <div class="msg-meta"><span>${msg.time}</span></div>
            </div>
        `;
        $messages.appendChild(row);
    }

    // ── Markdown Parser ────────────────────────────────────────
    function formatMarkdown(text) {
        if (!text) return "";
        let html = esc(text);

        // 1. Parse code blocks: ```lang code ```
        html = html.replace(/```(\w*)([\s\S]*?)```/g, (match, lang, code) => {
            const langClass = lang ? ` class="language-${lang}"` : "";
            return `<pre class="code-block"><code${langClass}>${code.trim()}</code></pre>`;
        });

        // 2. Parse inline code: `code`
        html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

        // 3. Replace **bold** and __bold__ with <strong>bold</strong>
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        html = html.replace(/__(.*?)__/g, "<strong>$1</strong>");

        // 4. Replace *italic* and _italic_ with <em>italic</em>
        html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
        html = html.replace(/_(.*?)_/g, "<em>$1</em>");

        return html;
    }

    // ── Log Line Highlighter ──────────────────────────────────
    function formatLogLine(line) {
        // Parse markdown bold in log lines if any
        let html = formatMarkdown(line);

        // Highlight tags like [SalienceRouter], [Decision], [Explanation], [collector_node], etc.
        html = html.replace(/\[([^\]]+)\]/g, (match, tag) => {
            let cls = "log-tag";
            const lower = tag.toLowerCase();
            if (lower.includes("router") || lower.includes("controlmode") || lower.includes("defaultmode")) {
                cls += " log-tag-router";
            } else if (lower.includes("node") || lower.includes("builder") || lower.includes("reasoner") || lower.includes("executor") || lower.includes("evaluator") || lower.includes("memory") || lower.includes("finalizer")) {
                cls += " log-tag-node";
            } else if (lower.includes("decision") || lower.includes("verdict") || lower.includes("explanation")) {
                cls += " log-tag-decision";
            } else if (lower.includes("warning")) {
                cls += " log-tag-warning";
            } else if (lower.includes("error") || lower.includes("failed")) {
                cls += " log-tag-error";
            } else if (lower.includes("mcp")) {
                cls += " log-tag-mcp";
            }
            return `<span class="${cls}">[${tag}]</span>`;
        });

        // Highlight key transitions like "Route to:", "VERDICT:", "tool=", "reasoning for task:"
        html = html.replace(/(Route to:|VERDICT:|tool=|reasoning for task:|executing action step|executing channel:|Finished\.)/g, '<span class="log-keyword">$1</span>');

        // Highlight values
        html = html.replace(/\b(SUCCESS|DefaultMode|ExecutiveControlMode|RETRY|SUCCESS|FAILURE)\b/g, '<span class="log-value">$1</span>');

        return html;
    }

    // ── Event Rendering ────────────────────────────────────────
    const EVENT_ICONS = {
        status:        `<svg class="event-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>`,
        node_update:   `<svg class="event-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
        final_summary: `<svg class="event-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
        error:         `<svg class="event-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    };

    function renderEventHTML(evt) {
        if (evt.type === "log_line") {
            const formatted = formatLogLine(evt.line);
            return `<div class="stream-event log_line"><div class="event-body"><span class="log-text-line">${formatted}</span></div></div>`;
        }

        const icon = EVENT_ICONS[evt.type] || EVENT_ICONS.status;

        if (evt.type === "status") {
            return `<div class="stream-event status">${icon}<div class="event-body"><span class="event-label">Status</span><span class="event-detail">${esc(evt.message)}</span></div></div>`;
        }

        if (evt.type === "node_update") {
            const rowsHtml = Object.entries(evt.updates || {}).map(([k, v]) => {
                let valHtml = "";
                if (k === "intent_result" && typeof v === "object" && v !== null) {
                    valHtml = `
                        <div class="intent-card">
                            <div class="intent-card-row">
                                <span class="intent-card-label">👤 Sender Identity</span>
                                <span class="intent-card-text">${esc(v.sender_identity || "Undetermined")}</span>
                            </div>
                            <div class="intent-card-row">
                                <span class="intent-card-label">💡 Inferences</span>
                                <span class="intent-card-text">${esc(v.inferences || "None")}</span>
                            </div>
                            <div class="intent-card-row">
                                <span class="intent-card-label">⚙ Recommended Action</span>
                                <span class="intent-card-text font-bold text-accent">${esc(v.recommended_action || "None")}</span>
                            </div>
                        </div>
                    `;
                } else if (Array.isArray(v)) {
                    valHtml = `<div style="display: flex; flex-wrap: wrap; gap: 4px 6px;">` + 
                              v.map(item => `<span class="value-chip">${esc(item)}</span>`).join("") + 
                              `</div>`;
                } else if (typeof v === "object" && v !== null) {
                    valHtml = `<code class="value-code">${esc(JSON.stringify(v))}</code>`;
                } else {
                    // Try parsing stringified arrays
                    let parsed = null;
                    if (typeof v === "string" && v.startsWith("[") && v.endsWith("]")) {
                        try { parsed = JSON.parse(v.replace(/'/g, '"')); } catch {}
                    }
                    if (Array.isArray(parsed)) {
                        valHtml = `<div style="display: flex; flex-wrap: wrap; gap: 4px 6px;">` + 
                                  parsed.map(item => `<span class="value-chip">${esc(item)}</span>`).join("") + 
                                  `</div>`;
                    } else {
                        valHtml = formatMarkdown(String(v));
                    }
                }
                return `
                    <div class="event-detail-row">
                        <span class="event-detail-key">${esc(k)}</span>
                        <span class="event-detail-val">${valHtml}</span>
                    </div>
                `;
            }).join("");

            return `
                <div class="stream-event node_update">
                    ${icon}
                    <div class="event-body">
                        <span class="event-label">⚙ ${esc(evt.node_name)}</span>
                        <div class="event-detail-list">${rowsHtml}</div>
                    </div>
                </div>
            `;
        }

        if (evt.type === "final_summary") {
            return `<div class="stream-event final_summary">${icon}<div class="event-body"><span class="event-label">✓ Routed to: ${esc(evt.target_subgraph || "—")}</span><span class="event-detail">${esc(evt.explanation || "")}</span></div></div>`;
        }

        if (evt.type === "error") {
            return `<div class="stream-event error">${icon}<div class="event-body"><span class="event-label">Error</span><span class="event-detail">${esc(evt.message)}</span></div></div>`;
        }

        // Unknown type fallback
        return `<div class="stream-event status">${icon}<div class="event-body"><span class="event-detail">${esc(JSON.stringify(evt))}</span></div></div>`;
    }

    // ── Streaming Handler ──────────────────────────────────────
    async function sendMessage(text) {
        if (!text.trim() || isStreaming) return;

        let conv = getActiveConv();
        if (!conv) conv = createConversation(text.slice(0, 50));
        else if (conv.messages.length === 0) {
            conv.title = text.slice(0, 50);
            $chatTitle.textContent = conv.title;
            renderConvList();
        }

        // Save user message
        const userTime = now();
        conv.messages.push({ role: "user", text, time: userTime });
        appendUserBubble(text, userTime);

        // UI state → streaming
        isStreaming = true;
        $btnSend.classList.add("hidden");
        $btnStop.classList.remove("hidden");
        setStatus("streaming", "Streaming…");
        $input.value = "";
        autoResize();

        // Prepare assistant row
        const assistant = createAssistantRow();
        const assistantMsg = { role: "assistant", events: [], result: "", time: "" };

        abortController = new AbortController();

        try {
            const resp = await fetch("/api/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_input: text }),
                signal: abortController.signal,
            });

            if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop(); // keep incomplete last line

                for (const line of lines) {
                    if (!line.trim()) continue;
                    let evt;
                    try { evt = JSON.parse(line); } catch { continue; }

                    assistantMsg.events.push(evt);
                    assistant.appendEvent(renderEventHTML(evt));

                    // If final_summary, show the result text prominently
                    if (evt.type === "final_summary" && evt.result) {
                        assistantMsg.result = evt.result;
                        assistant.showResult(evt.result);
                    }
                }
            }

        } catch (err) {
            if (err.name !== "AbortError") {
                const errEvt = { type: "error", message: err.message };
                assistantMsg.events.push(errEvt);
                assistant.appendEvent(renderEventHTML(errEvt));
            }
        } finally {
            assistant.setDone();
            assistantMsg.time = now();
            conv.messages.push(assistantMsg);
            isStreaming = false;
            abortController = null;
            $btnSend.classList.remove("hidden");
            $btnStop.classList.add("hidden");
            setStatus("ready", "Ready");
            $btnSend.disabled = !$input.value.trim();
        }
    }

    function stopStreaming() {
        if (abortController) abortController.abort();
    }

    // ── Status Indicator ───────────────────────────────────────
    function setStatus(state, label) {
        $statusText.textContent = label;
        $statusDot.style.background =
            state === "streaming" ? "var(--warning)" :
            state === "error"     ? "var(--error)"   :
                                    "var(--success)";
        $statusDot.style.boxShadow =
            state === "streaming" ? "0 0 6px var(--warning)" :
            state === "error"     ? "0 0 6px var(--error)"   :
                                    "0 0 6px var(--success)";
    }

    // ── Textarea Auto-Resize ───────────────────────────────────
    function autoResize() {
        $input.style.height = "auto";
        $input.style.height = Math.min($input.scrollHeight, parseInt(getComputedStyle(document.documentElement).getPropertyValue("--input-max-height"))) + "px";
    }

    // ── Event Listeners ────────────────────────────────────────
    $input.addEventListener("input", () => {
        autoResize();
        $btnSend.disabled = !$input.value.trim();
    });

    $input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if ($input.value.trim() && !isStreaming) sendMessage($input.value);
        }
    });

    $btnSend.addEventListener("click", () => {
        if ($input.value.trim() && !isStreaming) sendMessage($input.value);
    });

    $btnStop.addEventListener("click", stopStreaming);

    $btnNewChat.addEventListener("click", () => {
        createConversation();
        $input.focus();
    });

    $btnClear.addEventListener("click", () => {
        const conv = getActiveConv();
        if (conv) conv.messages = [];
        clearMessages();
        saveToLocalStorage();
    });

    $btnSidebar.addEventListener("click", () => {
        $sidebar.classList.toggle("collapsed");
    });

    // Suggestion chips
    document.querySelectorAll(".suggestion-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const prompt = chip.dataset.prompt;
            if (prompt) sendMessage(prompt);
        });
    });

    // ── Init ───────────────────────────────────────────────────
    loadFromLocalStorage();
    if (conversations.length === 0) {
        createConversation();
    } else {
        renderConvList();
        switchConversation(activeConvId);
    }
    $input.focus();
})();
