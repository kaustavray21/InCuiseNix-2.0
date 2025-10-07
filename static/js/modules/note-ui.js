// static/js/modules/note-ui.js

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
 * @param {object} note - The updated note object.
 */
export function updateNoteInUI(note) {
    const noteCard = document.querySelector(`.note-card[data-note-id='${note.id}']`);
    if (noteCard) {
        // Update the visible preview text
        noteCard.querySelector('.note-title-preview').textContent = note.title;
        
        // Create a truncated preview for the content
        const contentPreview = note.content.split(' ').slice(0, 10).join(' ') + (note.content.split(' ').length > 10 ? '...' : '');
        noteCard.querySelector('.note-content-preview').textContent = contentPreview;
        
        // Update the data attributes for future interactions
        noteCard.dataset.noteTitle = note.title;
        noteCard.dataset.noteContent = note.content;
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