
// static/js/home.js

document.addEventListener('DOMContentLoaded', function() {
    // --- FAQ Hover Logic ---
    // This script handles the hover-to-expand functionality for the FAQ section.
    const accordionItems = document.querySelectorAll('.accordion-item');

    accordionItems.forEach(item => {
        const button = item.querySelector('.accordion-button');
        const collapse = item.querySelector('.accordion-collapse');

        // On mouse enter, expand the accordion item
        item.addEventListener('mouseenter', () => {
            if (collapse) {
                // To get the smooth animation, we set the max-height to the element's scrollHeight
                collapse.style.maxHeight = collapse.scrollHeight + 'px';
                collapse.style.opacity = '1';
            }
            if (button) {
                // This will trigger the arrow animation if you have one
                button.classList.remove('collapsed');
            }
        });

        // On mouse leave, collapse the accordion item
        item.addEventListener('mouseleave', () => {
            if (collapse) {
                collapse.style.maxHeight = '0';
                collapse.style.opacity = '0';
            }
            if (button) {
                 button.classList.add('collapsed');
            }
        });
    });
});