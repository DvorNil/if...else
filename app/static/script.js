let timeoutId;

const userContainer = document.getElementById('userContainer');
const userMenu = document.getElementById('userMenu');

userContainer.addEventListener('mouseenter', function() {
    clearTimeout(timeoutId);
    userMenu.classList.add('visible');
});

userContainer.addEventListener('mouseleave', function() {
    timeoutId = setTimeout(function() {
        userMenu.classList.remove('visible');
    }, 300);
});

userMenu.addEventListener('mouseenter', function() {
    clearTimeout(timeoutId);
});

userMenu.addEventListener('mouseleave', function() {
    timeoutId = setTimeout(function() {
        userMenu.classList.remove('visible');
    }, 300);
});

function showModal(title, description, location, tags, eventType, address, lat, lng, imageUrl) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-description').textContent = description;
    document.getElementById('modal-location').textContent = location;
    document.getElementById('modal-address').textContent = address;
    document.getElementById('modal-tags').textContent = tags;
    document.getElementById('modal-event-type').textContent = eventType;
    document.getElementById('modal-image').src = imageUrl || 'https://via.placeholder.com/300x300?text=Image+Not+Found';
    document.getElementById('modal').style.display = 'block';

    fetch('/generate_map?lat=' + lat + '&lng=' + lng)
        .then(response => response.text())
        .then(html => {
            document.getElementById('modal-map').innerHTML = html;
        });
}

function hideModal() {
    document.getElementById('modal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('modal');
    if (event.target == modal) {
        hideModal();
    }
}

function filterPosts(filterType, value) {
    const url = new URL(window.location);
    url.searchParams.set(filterType, value);
    window.location = url;
}