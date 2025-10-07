// static/js/notes.js

import * as api from './modules/note-api.js';
import * as ui from './modules/note-ui.js';
import { formatTimestamp } from './modules/utils.js';

document.addEventListener('DOMContentLoaded', function() {
    // --- Get all necessary DOM elements ---
    const addNoteModalEl = document.getElementById('addNoteModal');
    const addNoteModal = new bootstrap.Modal(addNoteModalEl);
    const addNoteForm = document.getElementById('add-note-form');
    
    const editNoteModalEl = document.getElementById('editNoteModal');
    const editNoteModal = new bootstrap.Modal(editNoteModalEl);
    const editNoteForm = document.getElementById('edit-note-form');

    const notesListContainer = document.getElementById('notes-list-container');
    const notePopupOverlay = document.getElementById('note-popup-overlay');
    const popupCloseBtn = document.getElementById('popup-close-btn');

    // --- Event Listener for Adding a Note ---
    if (addNoteForm) {
        addNoteForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const videoId = document.getElementById('player-data-container').dataset.videoId;
            const formData = new FormData(this);

            try {
                const data = await api.addNote(videoId, formData);
                if (data.status === 'success') {
                    // FIX: Pass the rendered HTML from the server to the UI function
                    ui.addNoteToUI(data.note_card_html);
                    addNoteForm.reset();
                    addNoteModal.hide();
                } else {
                    console.error('Failed to add note:', data.errors);
                }
            } catch (error) {
                console.error('Error submitting form:', error);
            }
        });
    }

    // --- Event Listener for Saving Edited Note ---
    if (editNoteForm) {
        editNoteForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const noteId = document.getElementById('edit-note-id').value;
            const newTitle = document.getElementById('edit-note-title').value;
            const newContent = document.getElementById('edit-note-content').value;

            try {
                const data = await api.editNote(noteId, newTitle, newContent);
                if (data.status === 'success') {
                    ui.updateNoteInUI(data.note);
                    editNoteModal.hide();
                } else {
                    console.error('Failed to update note:', data.message);
                }
            } catch (error) {
                console.error('Error updating note:', error);
            }
        });
    }

    // --- Main Event Listener for the Notes List (for viewing, editing, deleting) ---
    if (notesListContainer) {
        notesListContainer.addEventListener('click', async function(event) {
            const target = event.target;
            const noteCard = target.closest('.note-card');

            if (!noteCard) return; // Exit if click was not on a card

            const editButton = target.closest('.note-btn-edit');
            const deleteButton = target.closest('.note-btn-delete');
            const noteId = noteCard.dataset.noteId;

            if (editButton) {
                // Handle Edit: Populates modal with correct title and content
                ui.populateEditModal(noteCard);
            
            } else if (deleteButton) {
                // Handle Delete
                if (confirm('Are you sure you want to delete this note?')) {
                    try {
                        const data = await api.deleteNote(noteId);
                        if (data.status === 'success') {
                            noteCard.remove();
                        } else {
                            console.error('Failed to delete note:', data.message);
                        }
                    } catch (error) {
                        console.error('Error deleting note:', error);
                    }
                }
            } else {
                // Handle View: Read data directly from the card's attributes
                const note = {
                    id: noteCard.dataset.noteId,
                    title: noteCard.dataset.noteTitle,
                    content: noteCard.dataset.noteContent,
                    timestamp: noteCard.dataset.noteTimestamp
                };
                
                // Pass the clean 'note' object to the UI function
                ui.showNotePopup(note);
            }
        });
    }
    
    // --- Listeners to close the note detail popup ---
    if (popupCloseBtn) {
        popupCloseBtn.addEventListener('click', () => {
             notePopupOverlay.style.display = 'none';
        });
    }
    if (notePopupOverlay) {
        notePopupOverlay.addEventListener('click', (event) => {
            if (event.target === notePopupOverlay) {
                 notePopupOverlay.style.display = 'none';
            }
        });
    }

    // --- Set timestamp in "Add Note" modal when it opens ---
    if (addNoteModalEl) {
        addNoteModalEl.addEventListener('show.bs.modal', function () {
            if (window.videoPlayer && typeof window.videoPlayer.currentTime === 'number') {
                const currentTime = Math.round(window.videoPlayer.currentTime);
                document.getElementById('id_video_timestamp').value = currentTime;
            }
        });
    }
});