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

function showModal(eventId, title, description, locationName, tags, eventType, 
                  locationAddress, lat, lng, imageUrl, isPrivate, format, onlineInfo) {
    
    // Сохраняем все данные мероприятия в объект
    currentEventData = {
        eventId, title, description, locationName, tags, eventType,
        locationAddress, lat, lng, imageUrl, isPrivate, format, onlineInfo
    };
    
    // Сохраняем в скрытое поле (как JSON строку)
    document.getElementById('modal-event-data').value = JSON.stringify(currentEventData);
    
    // Проверяем доступ для приватных мероприятий
    if (isPrivate && !checkAccess(eventId)) {
        showPasswordPrompt();
    } else {
        showEventContent();
    }
    
    document.getElementById('modal').style.display = 'block';
}

function showPasswordPrompt() {
    // Показываем только форму ввода пароля
    document.getElementById('password-prompt').style.display = 'block';
    document.getElementById('event-content').style.display = 'none';
    
    // Устанавливаем только название и изображение
    document.getElementById('modal-title').textContent = currentEventData.title;
    
    const modalImg = document.getElementById('modal-image');
    modalImg.src = currentEventData.imageUrl 
        ? (currentEventData.imageUrl.startsWith('http') 
            ? currentEventData.imageUrl 
            : `/static/${currentEventData.imageUrl}`)
        : '/static/images/no-image.jpg';
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
    // Скрываем форму ввода пароля
    document.getElementById('password-prompt').style.display = 'none';
    document.getElementById('event-content').style.display = 'block';
    
    // Заполняем все данные
    const e = currentEventData;
    document.getElementById('event-id').value = e.eventId;
    document.getElementById('modal-title').textContent = e.title;
    document.getElementById('modal-description').textContent = e.description;
    document.getElementById('modal-tags').textContent = e.tags;
    document.getElementById('modal-event-type').textContent = e.eventType;

    // Устанавливаем изображение
    const modalImg = document.getElementById('modal-image');
    modalImg.src = e.imageUrl 
        ? (e.imageUrl.startsWith('http') 
            ? e.imageUrl 
            : `/static/${e.imageUrl}`)
        : '/static/images/no-image.jpg';

    // Показываем соответствующие поля для формата
    if (e.format === 'online') {
        document.getElementById('location-info').style.display = 'none';
        document.getElementById('online-info').style.display = 'block';
        document.getElementById('modal-online-info').textContent = e.onlineInfo || 'Информация не указана';
    } else {
        document.getElementById('location-info').style.display = 'block';
        document.getElementById('online-info').style.display = 'none';
        document.getElementById('modal-location-name').textContent = e.locationName || 'Не указано';
        document.getElementById('modal-location-address').textContent = e.locationAddress || 'Не указан';
    }

    // Генерация карты (только для офлайн мероприятий)
    if (e.format === 'offline' && e.lat && e.lng) {
        fetch(`/generate_map?lat=${e.lat}&lng=${e.lng}`)
            .then(response => response.text())
            .then(html => {
                document.getElementById('modal-map').innerHTML = html;
            });
    } else {
        document.getElementById('modal-map').innerHTML = '';
    }
    
    // Загрузка статуса мероприятия
    loadEventStatus(e.eventId);
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
    //if (!document.cookie.includes('session=')) return;
    fetch('/get_all_events_status')
        .then(response => response.json())
        .then(statuses => {
            document.querySelectorAll('.post').forEach(post => {
                const eventId = getEventIdFromPost(post);
                const icon = post.querySelector('.post-status-icon');
                if (statuses[eventId.toString()]) {  alert("2"); //Почему-то alert 2 никогда не вызывается
                    icon.style.cssText = ` /* Принудительное обновление стилей */
                        display: block !important;
                        background-image: url(/static/images/${statuses[eventId]}Mini.png);
                        background-size: cover;
                    `;
                }
            });
        });
}
function getEventIdFromPost(post) {
    const onclickText = post.getAttribute('onclick');
    const match = onclickText.match(/showModal\((\d+),/);
    return match ? parseInt(match[1]) : null;
}
