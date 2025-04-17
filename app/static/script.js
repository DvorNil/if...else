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

document.addEventListener('DOMContentLoaded', () => {
    loadPostStatusIcons();
});

// Глобальная переменная для хранения данных о текущем мероприятии
let currentEventData = null;

function handlePostClick(element) {
    const eventData = {
        eventId: element.dataset.eventId,
        title: element.dataset.title,
        description: element.dataset.description,
        locationName: element.dataset.locationName,
        tags: element.dataset.tags,
        eventType: element.dataset.eventType,
        locationAddress: element.dataset.locationAddress,
        lat: parseFloat(element.dataset.lat) || 0,
        lng: parseFloat(element.dataset.lng) || 0,
        imageUrl: element.dataset.imageUrl,
        isPrivate: element.dataset.isPrivate === 'true',
        format: element.dataset.format,
        onlineInfo: element.dataset.onlineInfo
    };

    showModal(eventData);
}

function showModal(eventData) {
    currentEventData = eventData;
    
    if (eventData.isPrivate && !checkAccess(eventData.eventId)) {
        showPasswordPrompt();
    } else {
        showEventContent();
    }
    
    document.getElementById('modal').style.display = 'block';
}

function showPasswordPrompt() {
    document.getElementById('password-prompt').style.display = 'block';
    document.getElementById('event-content').style.display = 'none';
    
    // Устанавливаем только заголовок и изображение
    document.getElementById('modal-title').textContent = currentEventData.title;
    
    const img = document.getElementById('modal-image');
    img.src = currentEventData.imageUrl 
        ? `/static/${currentEventData.imageUrl}`
        : '/static/images/no-image.jpg';
    img.onerror = function() {
        this.src = '/static/images/no-image.jpg';
    };
}

function checkEventPassword() {
    const password = document.getElementById('event-password').value;
    const eventId = currentEventData.eventId;
    
    fetch(`/check_event_password/${eventId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password: password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Сохраняем доступ
            localStorage.setItem(`event_${eventId}_access`, 'granted');
            // Показываем полное содержимое
            showEventContent();
        } else {
            alert('Неверный пароль');
        }
    });
}

function showEventContent() {
    const e = currentEventData;
    if (!e) return;

    // Заполняем данные
    document.getElementById('modal-title').textContent = e.title;
    document.getElementById('modal-description').textContent = e.description;
    document.getElementById('modal-tags').textContent = e.tags;
    document.getElementById('modal-event-type').textContent = e.eventType;
    document.getElementById('event-id').value = e.eventId;

    // Изображение
    const img = document.getElementById('modal-image');
    img.src = e.imageUrl ? `/static/${e.imageUrl}` : '/static/images/no-image.jpg';
    img.onerror = function() {
        this.src = '/static/images/no-image.jpg';
    };

    // Формат мероприятия
    if (e.format === 'online') {
        document.getElementById('location-info').style.display = 'none';
        document.getElementById('online-info').style.display = 'block';
        document.getElementById('modal-online-info').textContent = e.onlineInfo;
    } else {
        document.getElementById('location-info').style.display = 'block';
        document.getElementById('online-info').style.display = 'none';
        document.getElementById('modal-location-name').textContent = e.locationName || "Не указано";
        document.getElementById('modal-location-address').textContent = e.locationAddress || "Не указан";
        
        // Карта
        if (e.lat && e.lng) {
            fetch(`/generate_map?lat=${e.lat}&lng=${e.lng}`)
                .then(response => response.text())
                .then(html => {
                    document.getElementById('modal-map').innerHTML = html;
                })
                .catch(err => {
                    console.error("Ошибка загрузки карты:", err);
                    document.getElementById('modal-map').innerHTML = "<p>Карта недоступна</p>";
                });
        } else {
            document.getElementById('modal-map').innerHTML = "";
        }
    }

    // Скрываем форму пароля
    document.getElementById('password-prompt').style.display = 'none';
    document.getElementById('event-content').style.display = 'block';
}

function loadEventStatus(eventId) {
    fetch(`/get_event_status?event_id=${eventId}`)
        .then(response => response.json())
        .then(data => {
            const statusIcon = document.getElementById('status-icon');
            if (data.status === 'planned') {
                statusIcon.src = '/static/images/plannedMini.png';
                statusIcon.style.display = 'block';
            } else if (data.status === 'attended') {
                statusIcon.src = '/static/images/attendedMini.png';
                statusIcon.style.display = 'block';
            } else {
                statusIcon.style.display = 'none';
            }
        });
}

function checkAccess(eventId) {
    return localStorage.getItem(`event_${eventId}_access`) === 'granted';
}

function hideModal() {
    document.getElementById('modal').style.display = 'none';
    currentEventData = null;
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

function loadPostStatusIcons() {
    fetch('/get_all_events_status')
        .then(response => response.json())
        .then(statuses => {
            document.querySelectorAll('.post').forEach(post => {
                const onclickText = post.getAttribute('onclick');
                const eventIdMatch = onclickText.match(/showModal\((\d+),/);
                if (!eventIdMatch) return;
                
                const eventId = eventIdMatch[1];
                const icon = post.querySelector('.post-status-icon');
                
                if (statuses[eventId]) {
                    icon.style.display = 'block';
                    icon.src = `/static/images/${statuses[eventId]}Mini.png`;
                }
            });
        });
}

function getEventIdFromPost(post) {
    if (!post) return null;
    const onclickText = post.getAttribute('onclick');
    if (!onclickText) return null;
    
    const match = onclickText.match(/showModal\((\d+),/);
    return match ? parseInt(match[1]) : null;
}
