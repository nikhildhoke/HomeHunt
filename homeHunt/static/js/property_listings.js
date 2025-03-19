document.addEventListener('DOMContentLoaded', () => {
    // Carousel functionality
    document.querySelectorAll('.image-carousel').forEach(carousel => {
        const items = carousel.querySelectorAll('.carousel-item');
        let currentIndex = 0;
        
        const showSlide = (index) => {
            items.forEach(item => item.classList.remove('active'));
            items[index].classList.add('active');
        };
        
        carousel.querySelector('.carousel-next').addEventListener('click', (e) => {
            e.stopPropagation();
            currentIndex = (currentIndex + 1) % items.length;
            showSlide(currentIndex);
        });
        
        carousel.querySelector('.carousel-prev').addEventListener('click', (e) => {
            e.stopPropagation();
            currentIndex = (currentIndex - 1 + items.length) % items.length;
            showSlide(currentIndex);
        });
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const addressFilter = document.getElementById('address-filter');
    const priceFilter = document.getElementById('price-filter');
    const bedroomsFilter = document.getElementById('bedrooms-filter');
    const propertyItems = document.querySelectorAll('.property-grid > div');

    function applyFilters() {
        const addressValue = addressFilter.value.toLowerCase();
        const priceValue = parseFloat(priceFilter.value) || 0;
        const bedroomsValue = parseInt(bedroomsFilter.value) || 0;

        propertyItems.forEach(item => {
            const address = item.querySelector('.property-info h5').textContent.toLowerCase();
            const priceText = item.querySelector('.price').textContent;
            const price = parseFloat(priceText.replace(/[^\d.]/g, ''));
            const bedroomsText = item.querySelector('.details span:nth-child(1)').textContent;
            const bedrooms = parseInt(bedroomsText.match(/\d+/)[0]);

            // Check filters
            const addressMatch = address.includes(addressValue);
            const priceMatch = priceValue === 0 || price <= priceValue;
            const bedroomsMatch = bedroomsValue === 0 || bedrooms >= bedroomsValue;

            // Toggle visibility
            item.style.display = (addressMatch && priceMatch && bedroomsMatch) ? 'block' : 'none';
        });
    }

    // Event listeners for all filters
    addressFilter.addEventListener('input', applyFilters);
    priceFilter.addEventListener('change', applyFilters);
    bedroomsFilter.addEventListener('change', applyFilters);
});