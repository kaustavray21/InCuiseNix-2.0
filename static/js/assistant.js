document.addEventListener('DOMContentLoaded', function() {
    // Correctly reference your existing chat elements
    const assistantForm = document.getElementById('assistant-form');
    const assistantInput = document.getElementById('assistant-input');
    const chatBox = document.getElementById('assistant-chat-box');
    const sendButton = document.getElementById('assistant-send-btn');
    const assistantChat = document.getElementById('assistant-chat'); // Get the main assistant container

    const videoId = assistantChat ? assistantChat.dataset.videoId : null;

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrfToken = getCookie('csrftoken');

    const converter = new showdown.Converter();

    const handleSubmit = async function(event) {
        event.preventDefault();
        const query = assistantInput.value.trim();
        if (!query) return;

        appendMessage(query, 'user');
        assistantInput.value = '';

        showLoadingIndicator();

        // --- UPDATED LOGIC ---
        const videoTitle = document.getElementById('current-video-title').textContent.trim();
        // Get timestamp if the player exists, otherwise default to 0
        const timestamp = window.videoPlayer ? window.videoPlayer.currentTime : 0;

        try {
            const response = await fetch('/api/assistant/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                // --- UPDATED: Send all context: query, id, title, and timestamp ---
                body: JSON.stringify({ 
                    query: query, 
                    video_id: videoId,
                    video_title: videoTitle,
                    timestamp: timestamp // Add the current timestamp
                })
            });

            removeLoadingIndicator();
            
            if (!response.ok) {
                const errorData = await response.json();
                const errorMessage = errorData.error || `An unexpected error occurred. Status: ${response.status}`;
                throw new Error(errorMessage);
            }

            const data = await response.json();

            if (data.answer) {
                appendMessage(data.answer, 'assistant');
            } else {
                appendMessage('Sorry, an error occurred. The assistant did not provide a valid answer.', 'assistant');
            }

        } catch (error) {
            console.error('Error:', error);
            removeLoadingIndicator();
            appendMessage(`Sorry, an error occurred: ${error.message}`, 'assistant');
        }
    };

    if (assistantForm) {
        assistantForm.addEventListener('submit', handleSubmit);
    }

    function appendMessage(message, sender) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', sender);

        if (sender === 'assistant') {
            const htmlContent = converter.makeHtml(message);
            messageElement.innerHTML = htmlContent;
        } else {
            messageElement.textContent = message;
        }

        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function showLoadingIndicator() {
        if (sendButton) sendButton.disabled = true;
        const loadingElement = document.createElement('div');
        loadingElement.classList.add('chat-message', 'loading');
        loadingElement.id = 'loading-indicator';
        loadingElement.innerHTML = `
            <div class="d-flex align-items-center">
                <strong class="me-2">Assistant is thinking...</strong>
                <div class="spinner-border spinner-border-sm" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
        chatBox.appendChild(loadingElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function removeLoadingIndicator() {
        if (sendButton) sendButton.disabled = false;
        const loadingElement = document.getElementById('loading-indicator');
        if (loadingElement) {
            loadingElement.remove();
        }
    }
});