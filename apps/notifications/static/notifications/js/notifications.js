document.addEventListener('alpine:init', () => {
    Alpine.data('notifications', () => ({
        count: 0,
        notifications: [],
        open: false,
        loading: false,

        init() {
            this.fetchNotifications();
            // Poll every 60 seconds
            setInterval(() => {
                this.fetchNotifications();
            }, 60000);
        },

        async fetchNotifications() {
            try {
                const response = await fetch('/notifications/api/list/');
                if (response.ok) {
                    const data = await response.json();
                    this.count = data.unread_count;
                    this.notifications = data.notifications;
                }
            } catch (error) {
                console.error('Error fetching notifications:', error);
            }
        },

        async markAsRead(id) {
            try {
                // Optimistic update
                const index = this.notifications.findIndex(n => n.id === id);
                if (index > -1) {
                    this.notifications[index].is_read = true;
                    this.count = Math.max(0, this.count - 1);
                }

                const response = await fetch(`/notifications/api/${id}/mark-read/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCookie('csrftoken')
                    },
                    keepalive: true
                });

                if (!response.ok) {
                    // Revert if failed (optional, but good UX)
                    console.error('Failed to mark as read');
                }
            } catch (error) {
                console.error('Error marking as read:', error);
            }
        },

        async markAllRead() {
            try {
                this.count = 0;
                this.notifications.forEach(n => n.is_read = true);

                const response = await fetch('/notifications/api/mark-all-read/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCookie('csrftoken')
                    }
                });
            } catch (error) {
                console.error('Error marking all read:', error);
            }
        },

        getCookie(name) {
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
    }));
});
