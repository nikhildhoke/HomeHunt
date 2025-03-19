function initMap() {
    const mapElement = document.getElementById('map');
    const eirCode = mapElement.dataset.eirCode;
    let coordinates = null;

    const map = new google.maps.Map(mapElement, {
        zoom: 14,
        center: {lat: 53.3498, lng: -6.2603} // Default Dublin coordinates
    });

    const geocoder = new google.maps.Geocoder();
    
    geocoder.geocode({
        address: `${eirCode}, Ireland`,
        componentRestrictions: { country: 'IE' }
    }, (results, status) => {
        if (status === 'OK' && results[0]) {
            coordinates = results[0].geometry.location;
            map.setCenter(coordinates);
            new google.maps.Marker({
                map: map,
                position: coordinates,
                title: 'Property Location'
            });
        } else {
            console.error('Geocode failed:', status);
            coordinates = {lat: 53.3498, lng: -6.2603}; // Fallback to Dublin
            new google.maps.Marker({
                map: map,
                position: coordinates,
                title: 'Approximate Location'
            });
        }
    });
}

// Load Google Maps API safely
function loadGoogleMaps() {
    if (!document.querySelector('#google-maps-script')) {
        const script = document.createElement('script');
        script.id = 'google-maps-script';
        script.src = `https://maps.googleapis.com/maps/api/js?key=AIzaSyDYKQ6STXyrLhI4yifnIqTSRM2_rR1DUtA&callback=initMap`;
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
    }
}

// Initialize when page loads
window.addEventListener('load', () => {
    loadGoogleMaps();
});