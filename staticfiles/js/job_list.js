
document.getElementById("useCurrentLocation").addEventListener("click", function () {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
            document.getElementById("lat").value = position.coords.latitude;
            document.getElementById("lng").value = position.coords.longitude;
            document.getElementById("filter-form").submit();
        });
    } else {
        alert("Geolocation is not supported by your browser.");
    }
});

document.getElementById("enterManualLocationBtn").addEventListener("click", function () {
    document.getElementById("manualLocationFields").classList.remove("d-none");
    document.getElementById("manualSaveFooter").classList.remove("d-none");
});

document.getElementById("saveManualLocation").addEventListener("click", function () {
    const city = document.getElementById("manual_municipality").value;
    const barangay = document.getElementById("manual_barangay").value;
    const street = document.getElementById("manual_street").value;
    const number = document.getElementById("manual_number").value;

    const fullAddress = [number, street, barangay, city].filter(Boolean).join(", ");

    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(fullAddress)}`)
        .then(response => response.json())
        .then(data => {
            if (data && data.length > 0) {
                document.getElementById("lat").value = data[0].lat;
                document.getElementById("lng").value = data[0].lon;
                document.getElementById("filter-form").submit();
            } else {
                alert("Address not found. Please refine your input.");
            }
        })
        .catch(error => {
            alert("Error fetching coordinates.");
        });
});

