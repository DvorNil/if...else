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

async function checkCurrentStatus(eventId) {
    try {
        const response = await fetch(`/event/${eventId}/status`);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        
        document.querySelectorAll('.status-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.status === data.status) {
                btn.classList.add('active');
            }
        });
    } catch (error) {
        console.error('Ошибка проверки статуса:', error);
    }
}

function showModal(eventId, title, description, location, tags, eventType, address, lat, lng, imageUrl) {
    // 1. Убедитесь, что eventId передан корректно (число)
    if (typeof eventId !== 'number') {
        console.error('Invalid eventId:', eventId);
        return;
    }

    // 2. Заполнение данных модального окна
    document.getElementById('event-id').value = eventId;
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-description').textContent = description;
    document.getElementById('modal-location').textContent = location;
    document.getElementById('modal-address').textContent = address;
    document.getElementById('modal-tags').textContent = tags;
    document.getElementById('modal-event-type').textContent = eventType;

    // 3. Обработка изображения
    const modalImg = document.getElementById('modal-image');
    modalImg.src = '/static/images/no-image.jpg'; // Сброс перед открытием
    if (imageUrl && imageUrl.trim() !== '') {
        modalImg.src = imageUrl.startsWith('http') 
            ? imageUrl 
            : `/static/${imageUrl}`;
    } else {
        modalImg.src = '/static/images/no-image.jpg';
    }

    // 4. Показ модального окна
    document.getElementById('modal').style.display = 'block';

    // 5. Запрос статуса мероприятия (используем eventId, а не eventData)
    fetch(`/get_status?event_id=${eventId}`)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        const activeBtn = data.status 
            ? document.querySelector(`.status-btn[data-status="${data.status}"]`)
            : null;
        if (activeBtn) activeBtn.classList.add('active');
    })
    .catch(error => {
        console.error('Ошибка запроса статуса:', error);
    });

    // 6. Генерация карты (проверяем lat и lng на валидность)
    if (typeof lat === 'number' && typeof lng === 'number') {
        fetch(`/generate_map?lat=${lat}&lng=${lng}`)
            .then(response => {
                if (!response.ok) throw new Error('Map generation failed');
                return response.text();
            })
            .then(html => {
                document.getElementById('modal-map').innerHTML = html;
            })
            .catch(error => console.error('Map fetch error:', error));
    } else {
        console.error('Invalid coordinates:', lat, lng);
    }

    // 7. Убрать вызов checkCurrentStatus, если он дублирует функционал
     checkCurrentStatus(eventId); // Раскомментировать, если функция существует
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
    const modalImg = document.getElementById('modal-image');
    modalImg.src = '/static/images/no-image.jpg'; // Сброс изображения
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