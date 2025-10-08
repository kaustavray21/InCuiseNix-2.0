import { formatTimestamp } from './utils.js';

/**
 * Adds a new note to the top of the notes list.
 * @param {string} noteCardHTML - The HTML of the new note card from the server.
 */
export function addNoteToUI(noteCardHTML) {
    const notesListContainer = document.getElementById('notes-list-container');
    const noNotesMessage = document.getElementById('no-notes-message');
    
    if (noNotesMessage) {
        noNotesMessage.style.display = 'none';
    }
    
    notesListContainer.insertAdjacentHTML('afterbegin', noteCardHTML);
}

/**
 * Updates an existing note card in the UI after an edit.
 * @param {object} note - The updated note object from the server.
 */
export function updateNoteInUI(note) {
    // 1. Find the specific note card using its data attribute.
    const noteCard = document.querySelector(`.note-card[data-note-id="${note.id}"]`);

    if (noteCard) {
        // 2. Find the title and content elements within that card.
        //    (Assumes your note card has elements with class "note-title" and "note-content")
        const titleElement = noteCard.querySelector('.note-title');
        const contentElement = noteCard.querySelector('.note-content');

        if (titleElement) {
            titleElement.textContent = note.title;
        }

        if (contentElement) {
            // Create a truncated preview for the content for display on the card
            const contentPreview = note.content.substring(0, 100) + (note.content.length > 100 ? '...' : '');
            contentElement.textContent = contentPreview;
        }

        // 3. CRITICAL: Update the data attributes on the card itself.
        //    This ensures that when you click "edit" or "view" again,
        //    the modals are populated with the latest, correct data.
        noteCard.dataset.noteTitle = note.title;
        noteCard.dataset.noteContent = note.content;
    } else {
        console.error(`Could not find a note card with ID ${note.id} to update in the UI.`);
    }
}


/**
 * Populates the "Edit Note" modal with the correct data.
 * @param {HTMLElement} noteCard - The note card element that was clicked.
 */
export function populateEditModal(noteCard) {
    document.getElementById('edit-note-id').value = noteCard.dataset.noteId;
    document.getElementById('edit-note-title').value = noteCard.dataset.noteTitle;
    document.getElementById('edit-note-content').value = noteCard.dataset.noteContent;
    
    // Show the modal using Bootstrap's API
    const editModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('editNoteModal'));
    editModal.show();
}

/**
 * Displays the note details in a popup.
 * @param {object} note - A clean note object with title, content, and timestamp.
 */
export function showNotePopup(note) {
    const notePopupOverlay = document.getElementById('note-popup-overlay');
    const popupTitle = document.getElementById('popup-note-title');
    const popupContent = document.getElementById('popup-note-content');
    const popupTimestamp = document.getElementById('popup-note-timestamp');

    // Populate the popup with data from the clean 'note' object
    popupTitle.textContent = note.title;
    popupContent.textContent = note.content;
    popupTimestamp.textContent = `Note at ${formatTimestamp(parseInt(note.timestamp, 10))}`;
    
    // Make the popup visible
    notePopupOverlay.style.display = 'flex';
}