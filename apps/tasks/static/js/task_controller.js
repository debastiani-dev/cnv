/**
 * TaskController
 * Handles inline status updates for tasks via the API.
 * Uses a "Portal" strategy to render dropdowns in the body only, avoiding table overflow clipping.
 */
const TaskController = {
    activeDropdownUuid: null,

    /**
     * Toggles the visibility of the status dropdown for a specific task.
     * Moves the dropdown content to a fixed portal in document.body.
     * @param {string} uuid - The UUID of the task
     */
    toggleDropdown: function (uuid) {
        // If clicking the same one, just close it
        if (this.activeDropdownUuid === uuid) {
            this.closeAllDropdowns();
            return;
        }

        // Close any existing
        this.closeAllDropdowns();

        const container = document.querySelector(`.status-dropdown-container[data-task-id="${uuid}"]`);
        const templateDropdown = document.getElementById(`dropdown-${uuid}`);

        if (container && templateDropdown) {
            this.activeDropdownUuid = uuid;

            // Create Portal
            const portal = document.createElement('div');
            portal.id = 'task-dropdown-portal';
            portal.className = 'fixed z-[9999] bg-white shadow-lg rounded-md border border-gray-200 py-1 w-32';

            // Clone content
            portal.innerHTML = templateDropdown.innerHTML;

            // Position it
            const rect = container.getBoundingClientRect();
            const spaceBelow = window.innerHeight - rect.bottom;

            // Logic: Default down (mt-1), if tight (< 200) go up
            // Since fixed, we use top/left coordinates
            portal.style.left = `${rect.left}px`;

            if (spaceBelow < 200) {
                // Open Up
                // Portal height is unknown until appended, but let's assume ~150px or calculate after append?
                // Better: Append first, then measure, then position?
                // Simple assumption for now or calculate:
                document.body.appendChild(portal);
                const portalHeight = portal.offsetHeight;
                portal.style.top = `${rect.top - portalHeight - 4}px`; // 4px gap
            } else {
                // Open Down
                portal.style.top = `${rect.bottom + 4}px`;
                document.body.appendChild(portal);
            }
        }
    },

    closeAllDropdowns: function () {
        const portal = document.getElementById('task-dropdown-portal');
        if (portal) {
            portal.remove();
        }
        this.activeDropdownUuid = null;
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

        // Find badge button (it's in the table, not the portal)
        // We can find it via the statusText parent
        const badgeButton = statusText ? statusText.closest('button') : null;

        if (!badgeButton) return;

        // Visual feedback
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

                    // Close dropdown (Portal)
                    this.closeAllDropdowns();

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
// We need to detect if click is inside the Portal OR the Container Button
document.addEventListener('click', function (event) {
    const portal = document.getElementById('task-dropdown-portal');
    const container = event.target.closest('.status-dropdown-container');

    // If click is inside the portal, do nothing (let button clicks handle it)
    if (event.target.closest('#task-dropdown-portal')) return;

    // If click is inside the activation button, do nothing (toggleDropdown handles it)
    if (container) return;

    // Otherwise, close
    TaskController.closeAllDropdowns();
});

// Update scroll listener to close dropdowns on scroll to avoid detached floating elements
document.addEventListener('scroll', function () {
    TaskController.closeAllDropdowns();
}, true);
