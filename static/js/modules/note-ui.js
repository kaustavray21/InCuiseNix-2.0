// static/js/modules/note-ui.js

import { formatTimestamp } from './utils.js';

/**
 * Creates the HTML for a single note card.
 * This version displays the full title and content.
 * @param {object} note - The note object.
 * @returns {string} The HTML string for the note card.
 */
function createNoteCardHTML(note) {
    // Sanitize content to prevent issues with quotes in data attributes
    const safeTitle = note.title.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    const safeContent = note.content.replace(/"/g, "&quot;").replace(/'/g, "&#39;");

    return `
        <div class="note-card"
             data-note-id="${note.id}"
             data-note-title="${safeTitle}"
             data-note-content="${safeContent}"
             data-note-timestamp="${note.video_timestamp}">
            
            <div class="note-card-header">
                <strong class="note-title">${note.title}</strong>
                <div class="note-actions">
                    <button class="note-btn note-btn-edit" title="Edit Note">
                        <i class="fas fa-pen-to-square"></i>
                    </button>
                    <button class="note-btn note-btn-delete" title="Delete Note">
                        <i class="fas fa-trash-can"></i>
                    </button>
                </div>
            </div>
            
            <p class="note-full-content">${note.content}</p>
            
            <small class="note-timestamp-display">
                Note at ${formatTimestamp(note.video_timestamp)}
            </small>
        </div>
    `;
}

/**
 * Adds a new note to the top of the notes list.
 * @param {object} note - The new note object to add.
 */
export function addNoteToUI(note) {
    const notesListContainer = document.getElementById('notes-list-container');
    const noNotesMessage = document.getElementById('no-notes-message');
    
    if (noNotesMessage) {
        noNotesMessage.style.display = 'none';
    }
    
    const noteCardHTML = createNoteCardHTML(note);
    notesListContainer.insertAdjacentHTML('afterbegin', noteCardHTML);
}

/**
 * Updates an existing note card in the UI after an edit.
 * @param {object} note - The updated note object.
 */
export function updateNoteInUI(note) {
    const noteCard = document.querySelector(`.note-card[data-note-id='${note.id}']`);
    if (noteCard) {
        // Update the visible text
        noteCard.querySelector('.note-title').textContent = note.title;
        
        // FIX: Target the correct class for the full content
        noteCard.querySelector('.note-full-content').textContent = note.content;
        
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
    popupTimestamp.textContent = `Note at ${formatTimestamp(note.timestamp)}`;
    
    // Make the popup visible
    notePopupOverlay.style.display = 'flex';
}