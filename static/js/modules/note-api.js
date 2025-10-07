const playerContainer = document.getElementById('player-data-container');
const csrfToken = playerContainer ? playerContainer.dataset.csrfToken : '';

async function fetchAPI(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Something went wrong');
    }
    return response.json();
}

export function addNote(videoId, formData) {
    return fetchAPI(`/note/add/${videoId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData,
    });
}

// static/js/modules/note-api.js

export function editNote(noteId, newTitle, newContent) { // <-- FIX: Accepts both title and content
    return fetchAPI(`/note/edit/${noteId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        // FIX: Sends both title and content in the request body
        body: JSON.stringify({ title: newTitle, content: newContent }),
    });
}

export function deleteNote(noteId) {
    return fetchAPI(`/note/delete/${noteId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
    });
}