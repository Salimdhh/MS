document.addEventListener('DOMContentLoaded', () => {
    // --- Helper for Toast Notifications (mimicking react-hot-toast) ---
    function showToast(message, type = 'default') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            console.error('Toast container not found!');
            return;
        }

        const toastDiv = document.createElement('div');
        toastDiv.classList.add('toast');
        if (type === 'error') {
            toastDiv.classList.add('error');
        } else if (type === 'success') {
            toastDiv.classList.add('success');
        }
        toastDiv.textContent = message;
        toastContainer.appendChild(toastDiv);

        // Show toast
        setTimeout(() => {
            toastDiv.classList.add('show');
        }, 10); // Small delay to allow CSS transition

        // Hide toast after 3 seconds
        setTimeout(() => {
            toastDiv.classList.remove('show');
            toastDiv.addEventListener('transitionend', () => {
                toastDiv.remove();
            }, { once: true }); // Remove event listener after it fires once
        }, 3000);
    }
    // --- End Toast Helper ---

    // يمكنك استخدام showToast() هنا بناءً على منطق Django الذي ترسله إلى الواجهة الأمامية.
    // على سبيل المثال، إذا كان Django يرسل رسائل (messages framework)، يمكنك عرضها كـ toasts.
    // مثال (في قالب Django):
    // {% if messages %}
    //     <script>
    //         {% for message in messages %}
    //             showToast("{{ message|escapejs }}", "{{ message.tags }}");
    //         {% endfor %}
    //     </script>
    // {% endif %}
});