/**
 * Company Knowledge Assistant - Client App Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('pdf-upload-input');
    const uploadStatus = document.getElementById('upload-status');
    const documentsList = document.getElementById('documents-list');
    const docCountBadge = document.getElementById('doc-count-badge');
    const clearBtn = document.getElementById('clear-btn');
    
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const agentLoading = document.getElementById('agent-loading');
    const loadingText = document.getElementById('loading-text');
    const errorBanner = document.getElementById('error-banner');

    // Initialize document list
    fetchDocuments();

    // ================= UPLOAD HANDLERS =================
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files);
        }
    });

    async function handleFileUpload(files) {
        const formData = new FormData();
        let pdfCount = 0;

        for (let i = 0; i < files.length; i++) {
            if (files[i].name.toLowerCase().endsWith('.pdf')) {
                formData.append('files', files[i]);
                pdfCount++;
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
                fileInput.value = '';
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

    // ================= DOCUMENT LISTING =================
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
            item.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                <div class="doc-info">
                    <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
                    <div class="doc-meta">${doc.total_pages} page(s) • ${doc.chunks_count} chunk(s)</div>
                </div>
            `;
            documentsList.appendChild(item);
        });
    }

    // ================= CHAT HANDLERS =================
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = userInput.value.trim();
        if (!query) return;

        // Render user message
        appendUserMessage(query);
        userInput.value = '';
        hideError();

        // Show Loading Indicator
        showLoading('Agent evaluating query...');

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: query })
            });

            const data = await response.json();

            if (response.ok) {
                appendAssistantMessage(data);
            } else {
                showError(data.detail || 'An error occurred while processing your request.');
            }
        } catch (err) {
            showError('Server connection failed. Please check if the application server is running.');
        } finally {
            hideLoading();
        }
    });

    function appendUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'message-row user';
        row.innerHTML = `
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
        const tagText = data.searched_docs 
            ? `🔍 PDF Search (${escapeHtml(data.search_query || 'document retrieval')})` 
            : '💡 Direct Answer';

        let sourcesHtml = '';
        if (data.sources && data.sources.length > 0) {
            const sourcePills = data.sources.map(src => `
                <div class="source-badge">
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

        chatMessages.appendChild(row);
        scrollToBottom();
    }

    // ================= CLEAR SESSION =================
    clearBtn.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to clear all indexed documents and chat history?')) {
            return;
        }

        try {
            const response = await fetch('/api/clear', { method: 'POST' });
            if (response.ok) {
                chatMessages.innerHTML = `
                    <div class="welcome-card">
                        <div class="welcome-header"><h3>Knowledge Base Reset</h3></div>
                        <p>All documents and conversation history have been cleared. Upload new PDFs to begin!</p>
                    </div>
                `;
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
        let formatted = escapeHtml(text);
        // Bold formatting
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italic formatting
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Newlines
        return formatted;
    }
});
