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
    // Заполнение данных модального окна
    document.getElementById('event-id').value = eventId;
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-description').textContent = description;
    document.getElementById('modal-location').textContent = location;
    document.getElementById('modal-address').textContent = address;
    document.getElementById('modal-tags').textContent = tags;
    document.getElementById('modal-event-type').textContent = eventType;

    // Обработка изображения
    const modalImg = document.getElementById('modal-image');
    modalImg.src = '/static/images/no-image.jpg';
    if (imageUrl && imageUrl.trim() !== '') {
        modalImg.src = imageUrl.startsWith('http') 
            ? imageUrl 
            : `/static/${imageUrl}`;
    }

    // Показ модального окна
    document.getElementById('modal').style.display = 'block';

    // Обработчики статусов
    const statusControls = document.querySelector('.status-controls');
    const eventIdInput = document.getElementById('event-id');

    // Удаляем предыдущие обработчики
    const newControls = statusControls.cloneNode(true);
    statusControls.parentNode.replaceChild(newControls, statusControls);

    // Функция обновления стилей кнопок
    const updateButtonStyles = (currentStatus) => {
        newControls.querySelectorAll('.status-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.status === currentStatus) {
                btn.classList.add('active');
            }
        });
    };

    // Общий обработчик кликов
    const handleStatusClick = async (e) => {
        const button = e.target.closest('.status-btn');
        if (!button) return;

        const status = button.dataset.status;
        
        try {
            const response = await fetch('/update_event_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    event_id: eventId, // Используем напрямую eventId из аргументов
                    status: status === 'none' ? null : status
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка сервера');
            }

            const data = await response.json();
            if (data.success) {
                updateButtonStyles(status === 'none' ? null : status);
            }
        } catch (error) {
            console.error('Error:', error);
            alert(error.message || 'Ошибка обновления статуса');
        }
    };

    // Добавляем обработчик на контейнер
    newControls.addEventListener('click', handleStatusClick);

    // Загрузка текущего статуса
    fetch(`/get_event_status?event_id=${eventId}`)
        .then(response => {
            if (!response.ok) throw new Error('Ошибка сети');
            return response.json();
        })
        .then(data => updateButtonStyles(data.status))
        .catch(error => console.error('Error:', error));

    // Генерация карты
    if (typeof lat === 'number' && typeof lng === 'number') {
        fetch(`/generate_map?lat=${lat}&lng=${lng}`)
            .then(response => {
                if (!response.ok) throw new Error('Ошибка генерации карты');
                return response.text();
            })
            .then(html => {
                document.getElementById('modal-map').innerHTML = html;
            })
            .catch(error => {
                console.error('Map fetch error:', error);
                document.getElementById('modal-map').innerHTML = '<p>Карта недоступна</p>';
            });
    } else {
        document.getElementById('modal-map').innerHTML = '<p>Координаты невалидны</p>';
        }
}

function hideModal() {
    const modalImg = document.getElementById('modal-image');
    modalImg.src = '/static/images/no-image.jpg';
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