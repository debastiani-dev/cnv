/**
 * TaskController
 * Handles inline status updates for tasks via the API.
 */
const TaskController = {
    /**
     * Toggles the visibility of the status dropdown for a specific task.
     * Closes all other open dropdowns.
     * @param {string} uuid - The UUID of the task
     */
    toggleDropdown: function (uuid) {
        const dropdown = document.getElementById(`dropdown-${uuid}`);
        const allDropdowns = document.querySelectorAll('.status-dropdown-container > div[id^="dropdown-"]');

        // Close all others
        allDropdowns.forEach(d => {
            if (d.id !== `dropdown-${uuid}`) {
                d.classList.add('hidden');
            }
        });

        if (dropdown) {
            dropdown.classList.toggle('hidden');
        }
    },

    /**
     * Updates the task status via API.
     * @param {string} uuid - The UUID of the task
     * @param {string} newStatus - The new status code (PENDING, IN_PROGRESS, DONE, CANCELED)
     */
    updateStatus: function (uuid, newStatus) {
        const url = `/tasks/api/${uuid}/update-status/`;
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const statusText = document.getElementById(`status-text-${uuid}`);
        const badgeButton = statusText.closest('button');
        const dropdown = document.getElementById(`dropdown-${uuid}`);

        // Visual feedback: opacity/disable
        badgeButton.style.opacity = '0.5';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ status: newStatus })
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => { throw new Error(data.error || 'Request failed') });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Update text
                    statusText.textContent = data.new_status_display;

                    // Update classes: remove old bg/text classes, add new ones
                    // Since we don't know exact previous classes cleanly, we replace the class list partial matches
                    // Simplest strategy: Remove all known status classes and add the new one + base classes
                    // Base classes: "badge inline-flex items-center gap-1 cursor-pointer"
                    badgeButton.className = `badge ${data.color_class} inline-flex items-center gap-1 cursor-pointer`;

                    // Close dropdown
                    dropdown.classList.add('hidden');

                    // Handle "DONE" strikethrough logic
                    const row = document.getElementById(`task-row-${uuid}`);
                    if (newStatus === 'DONE') {
                        if (row) row.classList.add('task-done');
                    } else if (row) {
                        row.classList.remove('task-done');
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to update status: ' + error.message);
            })
            .finally(() => {
                badgeButton.style.opacity = '1';
            });
    }
};

// Close dropdowns when clicking outside
document.addEventListener('click', function (event) {
    if (!event.target.closest('.status-dropdown-container')) {
        document.querySelectorAll('.status-dropdown-container > div[id^="dropdown-"]').forEach(d => {
            d.classList.add('hidden');
        });
    }
});
