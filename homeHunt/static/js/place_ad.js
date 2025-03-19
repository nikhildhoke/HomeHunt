document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('property-form');
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    // Image preview handling
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const preview = this.parentElement.querySelector('.preview-container');
            const file = e.target.files[0];
            
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    preview.innerHTML = `<img src="${e.target.result}" class="preview-image">`;
                }
                reader.readAsDataURL(file);
            }
        });
    });

    // Form validation
    form.addEventListener('submit', (e) => {
        const images = Array.from(fileInputs).filter(input => input.files.length > 0);
        
        if (images.length < 3) {
            e.preventDefault();
            alert('Please upload at least 3 images');
            return;
        }
    });
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