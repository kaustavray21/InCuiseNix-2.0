document.addEventListener('DOMContentLoaded', function() {
    // Correctly reference your existing chat elements
    const assistantForm = document.getElementById('assistant-form');
    const assistantInput = document.getElementById('assistant-input');
    const chatBox = document.getElementById('assistant-chat-box');
    const sendButton = document.getElementById('assistant-send-btn');
    const assistantChat = document.getElementById('assistant-chat'); // Get the main assistant container

    // --- NEW: Read the video ID from the data attribute ---
    const videoId = assistantChat ? assistantChat.dataset.videoId : null;

    // Use a more robust method to get the CSRF token
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

    // Initialize the showdown converter for Markdown
    const converter = new showdown.Converter();

    const handleSubmit = async function(event) {
        event.preventDefault();
        const query = assistantInput.value.trim();
        if (!query) return;

        // Display user's message
        appendMessage(query, 'user');
        assistantInput.value = '';

        // Show loading indicator
        showLoadingIndicator();

        // --- NEW: Get the current video's title ---
        const videoTitle = document.getElementById('current-video-title').textContent.trim();

        try {
            // --- UPDATED FETCH CALL ---
            const response = await fetch('/api/assistant/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                // --- NEW: Send the videoId and video_title along with the query ---
                body: JSON.stringify({ 
                    query: query, 
                    video_id: videoId,
                    video_title: videoTitle 
                })
            });

            // Remove loading indicator before appending the response
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
            // Convert the Markdown string from the AI to HTML
            const htmlContent = converter.makeHtml(message);
            messageElement.innerHTML = htmlContent;
        } else {
            // Keep user messages as plain text
            messageElement.textContent = message;
        }

        chatBox.appendChild(messageElement);
        // Scroll to the latest message
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