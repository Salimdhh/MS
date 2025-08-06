// Toast Notification System (Moved to a separate file)
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        console.error('Toast container not found!');
        return;
    }
    const toastElement = document.createElement('div');
    toastElement.classList.add('toast');
    if (type === 'error') {
        toastElement.classList.add('error');
    }
    toastElement.textContent = message;
    toastContainer.appendChild(toastElement);

    setTimeout(() => {
        toastElement.classList.add('show');
    }, 10);
    setTimeout(() => {
        toastElement.classList.remove('show');
        toastElement.addEventListener('transitionend', () => {
            toastElement.remove();
        }, { once: true });
    }, 3000);
}