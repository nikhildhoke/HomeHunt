document.addEventListener('DOMContentLoaded', function() {
    const bookingDate = document.getElementById('booking_date');
    const slotContainer = document.querySelector('.slot-container');
    const selectedTimeInput = document.getElementById('selected-time');
    const submitBtn = document.querySelector('.submit-btn');
    const bookedData = JSON.parse(document.getElementById('booked-data').textContent);
    let selectedSlot = null;

    slotContainer.addEventListener('click', function(e) {
        const slot = e.target.closest('.time-slot');
        if (!slot || slot.disabled) return;

        // Deselect previous slot
        if (selectedSlot) {
            selectedSlot.classList.remove('selected');
        }

        // Select new slot
        slot.classList.add('selected');
        selectedSlot = slot;
        selectedTimeInput.value = slot.dataset.time;
        submitBtn.disabled = false;
    });

    function updateTimeSlots() {
        const selectedDate = bookingDate.value;
        const bookedTimes = bookedData[selectedDate] || [];

        document.querySelectorAll('.time-slot').forEach(slot => {
            const slotTime = slot.dataset.time;
            const isBooked = bookedTimes.includes(slotTime);

            // Update slot state
            slot.disabled = isBooked;
            slot.classList.toggle('booked', isBooked);
            
            // Clear selection if slot becomes booked
            if (isBooked && slot === selectedSlot) {
                slot.classList.remove('selected');
                selectedSlot = null;
                selectedTimeInput.value = '';
                submitBtn.disabled = true;
            }
        });
    }
    
        // Date change handler
    bookingDate.addEventListener('change', () => {
        // Clear current selection
        if (selectedSlot) {
            selectedSlot.classList.remove('selected');
            selectedSlot = null;
        }
        
        // Reset form values
        selectedTimeInput.value = '';
        submitBtn.disabled = true;
        
        // Update slot availability
        updateTimeSlots();
    });

    // Initial setup
    updateTimeSlots();
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