function showDeleteConfirmation(event) {
    event.preventDefault();  // Prevent default button action
    document.getElementById('confirmationModal').style.display = 'block';
}

function cancelDelete() {
    document.getElementById('confirmationModal').style.display = 'none';
}

// Add event listener to prevent form submission from Enter key
document.getElementById('property-form').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const successMessage = document.getElementById('temp-message');
    const errorMessage = document.getElementById('temp-error-message');
    if (successMessage) {
        setTimeout(function() {
            successMessage.style.display = 'none';
        }, 5000);
    }
    
    if (errorMessage) {
        setTimeout(function() {
            errorMessage.style.display = 'none';
        }, 5000);
    }
});