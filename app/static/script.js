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


function showModal(eventId, title, description, location, tags, eventType, address, lat, lng, imageUrl) {
    document.getElementById('event-id').value = eventId;
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-description').textContent = description;
    document.getElementById('modal-location').textContent = location;
    document.getElementById('modal-address').textContent = address;
    document.getElementById('modal-tags').textContent = tags;
    document.getElementById('modal-event-type').textContent = eventType;
    document.getElementById('modal-image').src = imageUrl || 'https://via.placeholder.com/300x300?text=Image+Not+Found';
    
    const modalImg = document.getElementById('modal-image');
    if (imageUrl) {
        modalImg.src = imageUrl.startsWith('http') ? imageUrl : `/static/${imageUrl}`;
    } else {
        modalImg.src = '/static/images/no-image.jpg';
    }

    document.getElementById('modal').style.display = 'block';

    fetch(`/get_status?event_id=${eventId}`)
    .then(response => response.json())
    .then(data => {
        const activeBtn = data.status 
            ? document.querySelector(`.status-btn[data-status="${data.status}"]`)
            : null;
            
        if(activeBtn) activeBtn.classList.add('active');
    });

    fetch('/generate_map?lat=' + lat + '&lng=' + lng)
        .then(response => response.text())
        .then(html => {
            document.getElementById('modal-map').innerHTML = html;
        });

        checkCurrentStatus(eventData.id);
}

async function checkCurrentStatus(eventId) {
    try {
        const response = await fetch(`/event/${eventId}/status`);
        const { status } = await response.json();
        
        document.querySelectorAll('.status-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.id === `mark-${status}`) {
                btn.classList.add('active');
            }
        });
    } catch (error) {
        console.error('Ошибка проверки статуса:', error);
    }
}

async function updateEventStatus(newStatus) {
    try {
        const eventId = // ... получить ID текущего мероприятия ...;
        response = await fetch(`/event/${eventId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (response.ok) {
            checkCurrentStatus(eventId);
        }
    } catch (error) {
        console.error('Ошибка обновления статуса:', error);
    }
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

function filterPosts(type, value) {
    const searchInput = document.querySelector('input[name="search"]');
    const form = document.querySelector('form');
    
    if (type === 'tag') {
        const hiddenInput = document.querySelector('input[name="tag"]');
        hiddenInput.value = value;
    }
    
    form.submit();
}