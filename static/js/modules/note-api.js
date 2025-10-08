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
    // UPDATED: Corrected URL path
    return fetchAPI(`/api/notes/add/${videoId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData,
    });
}

export function editNote(noteId, newTitle, newContent) {
    // UPDATED: Corrected URL path
    return fetchAPI(`/api/notes/edit/${noteId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title: newTitle, content: newContent }),
    });
}

export function deleteNote(noteId) {
    // UPDATED: Corrected URL path
    return fetchAPI(`/api/notes/delete/${noteId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
    });
}