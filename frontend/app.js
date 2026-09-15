/**
 * Company Knowledge Assistant - Client App Logic
 * Supports 3-column ChatGPT-style interface, multi-session chat history, and document repository.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Current Active Session State
    let activeSessionId = null;
    let activeAttachedFilename = null;

    // DOM Elements - Left Sidebar
    const newChatBtn = document.getElementById('new-chat-btn');
    const sessionList = document.getElementById('session-list');

    // DOM Elements - Center Chat Panel
    const currentSessionTitle = document.getElementById('current-session-title');
    const chatMessages = document.getElementById('chat-messages');
    const welcomeCard = document.getElementById('welcome-card');
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const agentLoading = document.getElementById('agent-loading');
    const loadingText = document.getElementById('loading-text');
    const errorBanner = document.getElementById('error-banner');
    const leftPdfInput = document.getElementById('pdf-upload-input');

    // DOM Elements - Attachment Chip Bar
    const attachmentChipBar = document.getElementById('attachment-chip-bar');
    const attachedFileName = document.getElementById('attached-file-name');
    const removeAttachmentBtn = document.getElementById('remove-attachment-btn');

    // DOM Elements - Right Sidebar
    const dropzone = document.getElementById('dropzone');
    const rightPdfInput = document.getElementById('right-pdf-upload-input');
    const uploadStatus = document.getElementById('upload-status');
    const documentsList = document.getElementById('documents-list');
    const docCountBadge = document.getElementById('doc-count-badge');
    const clearBtn = document.getElementById('clear-btn');


    // Initial Load
    init();

    async function init() {
        await fetchDocuments();
        await fetchSessionsAndLoadActive();
    }

    // ================= SESSION MANAGEMENT =================

    async function fetchSessionsAndLoadActive(preferredSessionId = null) {
        try {
            const response = await fetch('/api/sessions');
            const data = await response.json();
            const sessions = data.sessions || [];

            renderSessionList(sessions);

            if (sessions.length > 0) {
                if (preferredSessionId && sessions.some(s => s.session_id === preferredSessionId)) {
                    activeSessionId = preferredSessionId;
                } else if (!activeSessionId || !sessions.some(s => s.session_id === activeSessionId)) {
                    activeSessionId = sessions[0].session_id;
                }
                await loadSession(activeSessionId);
            } else {
                // No existing sessions, create a default first chat session
                await createNewChatSession();
            }
        } catch (err) {
            console.error('Failed to fetch chat sessions:', err);
        }
    }

    function renderSessionList(sessions) {
        sessionList.innerHTML = '';
        if (sessions.length === 0) {
            sessionList.innerHTML = '<div class="empty-sessions-msg">No recent chats</div>';
            return;
        }

        sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = `session-item ${session.session_id === activeSessionId ? 'active' : ''}`;
            item.setAttribute('data-id', session.session_id);

            item.innerHTML = `
                <svg class="session-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                <span class="session-title" title="${escapeHtml(session.title)}">${escapeHtml(session.title)}</span>
                <button class="delete-session-btn" title="Delete chat session">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
            `;

            // Click session item -> select session
            item.addEventListener('click', (e) => {
                if (e.target.closest('.delete-session-btn')) return;
                if (activeSessionId !== session.session_id) {
                    loadSession(session.session_id);
                }
            });

            // Click delete button -> delete session
            const delBtn = item.querySelector('.delete-session-btn');
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteSession(session.session_id);
            });

            sessionList.appendChild(item);
        });
    }

    newChatBtn.addEventListener('click', () => {
        createNewChatSession();
    });

    async function createNewChatSession() {
        try {
            const response = await fetch('/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: 'New Chat' })
            });

            const newSession = await response.json();
            if (response.ok && newSession.session_id) {
                activeSessionId = newSession.session_id;
                await fetchSessionsAndLoadActive(activeSessionId);
            }
        } catch (err) {
            console.error('Failed to create new chat session:', err);
        }
    }

    async function loadSession(sessionId) {
        try {
            const response = await fetch(`/api/sessions/${sessionId}`);
            if (!response.ok) return;

            const session = await response.json();
            activeSessionId = session.session_id;
            currentSessionTitle.textContent = session.title || 'New Chat';

            // Highlight active in session list
            document.querySelectorAll('.session-item').forEach(el => {
                el.classList.toggle('active', el.getAttribute('data-id') === sessionId);
            });

            // Render message history
            renderMessageHistory(session.messages || []);
        } catch (err) {
            console.error(`Failed to load session ${sessionId}:`, err);
        }
    }

    async function deleteSession(sessionId) {
        try {
            const response = await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
            if (response.ok) {
                if (activeSessionId === sessionId) {
                    activeSessionId = null;
                }
                await fetchSessionsAndLoadActive(activeSessionId);
            }
        } catch (err) {
            console.error(`Failed to delete session ${sessionId}:`, err);
        }
    }

    function renderMessageHistory(messages) {
        chatMessages.innerHTML = '';

        if (!messages || messages.length === 0) {
            // Render Welcome Card
            chatMessages.innerHTML = `
                <div class="welcome-card" id="welcome-card">
                    <div class="welcome-header">
                        <h3>Where should we begin?</h3>
                    </div>
                    <p>Ask questions grounded in your uploaded company documents or start a general query.</p>
                    <div class="features-grid">
                        <div class="feature-item">
                            <strong>📄 Upload PDFs</strong>
                            <span>Drop PDFs in the right panel or use the attachment paperclip below.</span>
                        </div>
                        <div class="feature-item">
                            <strong>🤖 Smart Agent Routing</strong>
                            <span>Decides when to search internal documents vs direct answers.</span>
                        </div>
                        <div class="feature-item">
                            <strong>📌 Exact Source Citations</strong>
                            <span>Shows PDF filename and page number for every document answer.</span>
                        </div>
                    </div>
                </div>
            `;
            return;
        }

        messages.forEach(msg => {
            if (msg.role === 'user') {
                appendUserMessage(msg.content);
            } else if (msg.role === 'assistant') {
                appendAssistantMessage({
                    answer: msg.content,
                    searched_docs: msg.searched_docs,
                    search_query: msg.search_query,
                    sources: msg.sources || []
                });
            }
        });

        scrollToBottom();
    }

    // DOM Elements - PDF Preview Modal
    const pdfModal = document.getElementById('pdf-modal');
    const pdfModalFilename = document.getElementById('pdf-modal-filename');
    const pdfModalIframe = document.getElementById('pdf-modal-iframe');
    const pdfModalOpenTab = document.getElementById('pdf-modal-open-tab');
    const pdfModalClose = document.getElementById('pdf-modal-close');

    // Attachment State Controls
    function setAttachedFile(filename) {
        activeAttachedFilename = filename;
        if (filename) {
            attachedFileName.textContent = filename;
            attachmentChipBar.classList.remove('hidden');
        } else {
            attachmentChipBar.classList.add('hidden');
        }
    }

    if (removeAttachmentBtn) {
        removeAttachmentBtn.addEventListener('click', () => {
            setAttachedFile(null);
            leftPdfInput.value = '';
        });
    }

    // ================= UPLOAD HANDLERS =================

    rightPdfInput.addEventListener('change', () => {
        if (rightPdfInput.files.length > 0) {
            handleFileUpload(rightPdfInput.files);
        }
    });

    leftPdfInput.addEventListener('change', () => {
        if (leftPdfInput.files.length > 0) {
            handleFileUpload(leftPdfInput.files);
        }
    });

    async function handleFileUpload(files) {
        const formData = new FormData();
        let pdfCount = 0;
        let lastPdfName = null;

        for (let i = 0; i < files.length; i++) {
            if (files[i].name.toLowerCase().endsWith('.pdf')) {
                formData.append('files', files[i]);
                pdfCount++;
                lastPdfName = files[i].name;
            }
        }

        if (pdfCount === 0) {
            showUploadStatus('Please select valid .pdf files.', 'error');
            return;
        }

        showUploadStatus(`Processing ${pdfCount} PDF document(s)...`, 'info');

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                showUploadStatus(data.message, 'success');
                fetchDocuments();
                if (lastPdfName) {
                    setAttachedFile(lastPdfName);
                }
                rightPdfInput.value = '';
                leftPdfInput.value = '';
            } else {
                showUploadStatus(data.detail || 'Failed to process PDFs.', 'error');
            }
        } catch (err) {
            showUploadStatus('Error uploading file. Server connection failed.', 'error');
        }
    }

    function showUploadStatus(msg, type) {
        uploadStatus.textContent = msg;
        uploadStatus.className = `status-msg ${type}`;
        uploadStatus.classList.remove('hidden');

        if (type === 'success') {
            setTimeout(() => uploadStatus.classList.add('hidden'), 5000);
        }
    }


    // ================= DOCUMENT LISTING & PREVIEW =================

    async function fetchDocuments() {
        try {
            const response = await fetch('/api/documents');
            const data = await response.json();

            if (data.documents && data.documents.length > 0) {
                renderDocumentList(data.documents);
                docCountBadge.textContent = data.documents.length;
            } else {
                documentsList.innerHTML = '<div class="empty-docs-msg">No PDF documents uploaded yet.</div>';
                docCountBadge.textContent = '0';
            }
        } catch (err) {
            console.error('Failed to fetch documents list:', err);
        }
    }

    function renderDocumentList(docs) {
        documentsList.innerHTML = '';
        docs.forEach(doc => {
            const item = document.createElement('div');
            item.className = 'doc-item';
            item.setAttribute('title', 'Click to review document');
            item.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                <div class="doc-info">
                    <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
                    <div class="doc-meta">${doc.total_pages} page(s) • ${doc.chunks_count} chunk(s)</div>
                </div>
                <button class="delete-doc-btn" title="Delete document from repository">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
            `;

            // Click item -> review document in modal
            item.addEventListener('click', (e) => {
                if (e.target.closest('.delete-doc-btn')) return;
                openPdfModal(doc.filename);
            });

            // Click delete button -> delete document
            const delBtn = item.querySelector('.delete-doc-btn');
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteDocument(doc.filename);
            });

            documentsList.appendChild(item);
        });
    }

    async function deleteDocument(filename) {
        if (!confirm(`Are you sure you want to delete '${filename}' from the repository?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' });
            if (response.ok) {
                showUploadStatus(`Deleted '${filename}' from repository.`, 'success');
                fetchDocuments();
            } else {
                showUploadStatus(`Failed to delete '${filename}'.`, 'error');
            }
        } catch (err) {
            showUploadStatus('Error deleting document.', 'error');
        }
    }

    // ================= PDF MODAL CONTROLS =================

    function openPdfModal(filename, pageNumber = 1) {
        const pdfUrl = `/uploaded_pdfs/${encodeURIComponent(filename)}#page=${pageNumber}`;
        pdfModalFilename.textContent = pageNumber > 1 ? `${filename} (Page ${pageNumber})` : filename;
        pdfModalIframe.src = pdfUrl;
        pdfModalOpenTab.href = pdfUrl;
        pdfModal.classList.remove('hidden');
    }

    function closePdfModal() {
        pdfModal.classList.add('hidden');
        pdfModalIframe.src = '';
    }

    if (pdfModalClose) {
        pdfModalClose.addEventListener('click', closePdfModal);
    }

    if (pdfModal) {
        pdfModal.addEventListener('click', (e) => {
            if (e.target === pdfModal) {
                closePdfModal();
            }
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && pdfModal && !pdfModal.classList.contains('hidden')) {
            closePdfModal();
        }
    });

    // ================= CHAT FORM SUBMIT =================

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = userInput.value.trim();
        if (!query) return;

        const attachedForQuery = activeAttachedFilename;
        setAttachedFile(null);

        // Ensure active session exists
        if (!activeSessionId) {
            await createNewChatSession();
        }

        // Remove Welcome Card if present
        const wc = document.getElementById('welcome-card');
        if (wc) wc.remove();

        // Render user message with attached document pill if present
        appendUserMessage(query, attachedForQuery);
        userInput.value = '';
        hideError();

        // Show Loading Indicator with focused status
        const loadMsg = attachedForQuery
            ? `Agent evaluating query & analyzing '${attachedForQuery}'...`
            : 'Agent evaluating query & searching documents...';
        showLoading(loadMsg);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message: query, 
                    session_id: activeSessionId,
                    attached_filename: attachedForQuery
                })
            });

            const data = await response.json();

            if (response.ok) {
                appendAssistantMessage(data);
                if (data.session_title) {
                    currentSessionTitle.textContent = data.session_title;
                }
                // Refresh left sidebar sessions list to show auto-generated title
                const resSessions = await fetch('/api/sessions');
                const dataSessions = await resSessions.json();
                renderSessionList(dataSessions.sessions || []);
            } else {
                showError(data.detail || 'An error occurred while processing your request.');
            }
        } catch (err) {
            showError('Server connection failed. Please check if the application server is running.');
        } finally {
            hideLoading();
        }
    });

    function appendUserMessage(text, attachedFilename = null) {
        const row = document.createElement('div');
        row.className = 'message-row user';
        const attachedBadgeHtml = attachedFilename 
            ? `<div class="user-attached-file-badge"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg> <span>Attached: ${escapeHtml(attachedFilename)}</span></div>`
            : '';
        row.innerHTML = `
            ${attachedBadgeHtml}
            <div class="message-bubble">${escapeHtml(text)}</div>
        `;
        chatMessages.appendChild(row);
        scrollToBottom();
    }

    function appendAssistantMessage(data) {
        const row = document.createElement('div');
        row.className = 'message-row assistant';

        // Tag for agent routing
        const tagClass = data.searched_docs ? 'searched' : 'direct';
        let tagText = '💡 Direct Answer';
        
        if (data.attached_filename) {
            tagText = `🎯 Focused PDF Analysis (${escapeHtml(data.attached_filename)})`;
        } else if (data.searched_docs) {
            tagText = `🔍 PDF Search (${escapeHtml(data.search_query || 'document retrieval')})`;
        }


        let sourcesHtml = '';
        if (data.sources && data.sources.length > 0) {
            const sourcePills = data.sources.map(src => `
                <div class="source-badge" data-file="${escapeHtml(src.filename)}" data-page="${src.page_number}" title="Click to view page ${src.page_number} in document viewer">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                    <span>Source: ${escapeHtml(src.filename)} — Page ${src.page_number}</span>
                </div>
            `).join('');

            sourcesHtml = `
                <div class="sources-container">
                    <div class="sources-header">DOCUMENT SOURCES</div>
                    <div class="sources-list">${sourcePills}</div>
                </div>
            `;
        }

        row.innerHTML = `
            <div class="agent-tag ${tagClass}">${tagText}</div>
            <div class="message-bubble">${formatMarkdownText(data.answer)}${sourcesHtml}</div>
        `;

        // Click source pill -> open PDF viewer modal at target page!
        row.querySelectorAll('.source-badge').forEach(badge => {
            badge.style.cursor = 'pointer';
            badge.addEventListener('click', (e) => {
                e.stopPropagation();
                const fn = badge.getAttribute('data-file');
                const pg = parseInt(badge.getAttribute('data-page') || '1', 10);
                openPdfModal(fn, pg);
            });
        });

        chatMessages.appendChild(row);
        scrollToBottom();
    }

    // ================= CLEAR KNOWLEDGE BASE =================

    clearBtn.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to clear all indexed documents in the repository?')) {
            return;
        }

        try {
            const response = await fetch('/api/clear', { method: 'POST' });
            if (response.ok) {
                showUploadStatus('Knowledge base cleared successfully.', 'success');
                fetchDocuments();
            }
        } catch (err) {
            showError('Failed to reset knowledge base.');
        }
    });

    // ================= UTILITIES =================

    function showLoading(msg) {
        loadingText.textContent = msg;
        agentLoading.classList.remove('hidden');
        sendBtn.disabled = true;
    }

    function hideLoading() {
        agentLoading.classList.add('hidden');
        sendBtn.disabled = false;
    }

    function showError(msg) {
        errorBanner.textContent = msg;
        errorBanner.classList.remove('hidden');
    }

    function hideError() {
        errorBanner.classList.add('hidden');
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    function formatMarkdownText(text) {
        if (!text) return '';
        let formatted = escapeHtml(text.trim());
        // Collapse 3 or more consecutive newlines into 2
        formatted = formatted.replace(/\n{3,}/g, '\n\n');
        // Bold formatting **text**
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italic formatting *text*
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Bullet lists (* or -)
        formatted = formatted.replace(/^[\*\-]\s+(.*)$/gm, '• $1');
        // Newlines to <br>
        formatted = formatted.replace(/\n/g, '<br>');
        return formatted;
    }
});


