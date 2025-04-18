const userContainer = document.getElementById('userContainer');
const userMenu = document.getElementById('userMenu');


// Глобальная переменная для хранения данных о текущем мероприятии
let currentEventData = null;


document.addEventListener('DOMContentLoaded', () => {
    loadPostStatusIcons();
});

if (userContainer && userMenu) {
    let timeoutId; 
    
    userContainer.addEventListener('mouseenter', function() {
        clearTimeout(timeoutId);
        userMenu.classList.add('visible');
    });

    userContainer.addEventListener('mouseleave', function() {
        timeoutId = setTimeout(() => {
            userMenu.classList.remove('visible');
        }, 300);
    });

    userMenu.addEventListener('mouseenter', function() {
        clearTimeout(timeoutId);
    });

    userMenu.addEventListener('mouseleave', function() {
        timeoutId = setTimeout(() => {
            userMenu.classList.remove('visible');
        }, 300);
    });
} else {
    console.log('User menu elements not found - skipping hover logic');
}

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
        onlineInfo: element.dataset.onlineInfo,
        dateTime: element.dataset.dateTime, 
        duration: parseInt(element.dataset.duration) || 0,
        organizerUsername: element.dataset.organizerUsername
    };

    showModal(eventData);
}

function showModal(eventData) {
    currentEventData = eventData;
    
    eventId = currentEventData.eventId;

    const statusIcon = document.getElementById('status-icon');

    document.getElementById('modal').style.display = 'block';
    
    if (!statusIcon) {
        console.error('Элемент с id="status-icon" не найден!');
        return;
    }

    fetch(`/get_event_status?event_id=${eventId}`)
        .then(response => {
            if (!response.ok) throw new Error('Ошибка сети');
            return response.json();
        })
        .then(data => {
            if (data.status === 'planned') {
                statusIcon.src = '/static/images/plannedMini.png';
                statusIcon.style.display = 'block';
            } else if (data.status === 'attended') {
                statusIcon.src = '/static/images/attendedMini.png';
                statusIcon.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Ошибка получения статуса:', error);
            //statusIcon.style.display = 'none';
        });

    const statusControls = document.querySelector('.status-controls');
    const newControls = statusControls.cloneNode(true);
    statusControls.parentNode.replaceChild(newControls, statusControls);

    // Обработчик кликов (объявлен внутри showModal)
    const handleStatusClick = async (e) => {
        const button = e.target.closest('.status-btn');
        if (!button) return;
    
        try {
            const response = await fetch('/update_event_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    event_id: eventId,
                    status: button.dataset.status
                })
            });
    
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ошибка сервера');
            }
    
            const data = await response.json();
            if (data.success) {
                // Обновляем иконку в модалке
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
                // Обновляем иконку в посте
                const posts = document.querySelectorAll('.post');
                posts.forEach(post => {
                    const postEventId = getEventIdFromPost(post);
                    if (postEventId == eventId) {
                        const postIcon = post.querySelector('.post-status-icon');
                        postIcon.src = `/static/images/${data.status}Mini.png`;
                        postIcon.style.display = 'block';
                    }
                });
            }
        } catch (error) {
            console.error('Error:', error);
            alert(error.message || 'Ошибка обновления статуса');
        }
    };
    // Добавляем обработчик на новый контейнер
    newControls.addEventListener('click', handleStatusClick);




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

    const dateOptions = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    const formattedDate = new Date(e.dateTime).toLocaleDateString('ru-RU', dateOptions);
    document.getElementById('modal-date').textContent = formattedDate;

    // Преобразование продолжительности (минуты → часы + минуты)
    const hours = Math.floor(e.duration / 60);
    const minutes = e.duration % 60;
    document.getElementById('modal-duration').textContent = `${hours} ч ${minutes} мин`;

    // Формат мероприятия
    document.getElementById('modal-format').textContent = e.format === 'online' ? 'Онлайн' : 'Офлайн';

    // Организатор
    document.getElementById('modal-organizer').textContent = e.organizerUsername || "Не указан";

    // Изображение
    const img = document.getElementById('modal-image');
    img.src = e.imageUrl ? `/static/${e.imageUrl}` : '/static/images/no-image.jpg';
    img.onerror = function() {
        this.src = '/static/images/no-image.jpg';
    };

    document.getElementById('modal-image').addEventListener('click', function(e) {
        e.stopPropagation();
        showImageModal(this.src);
    });

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

function loadEventStatus(eventId) { //функция вообще не применяется
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

// Новые функции для управления модалкой изображения
function showImageModal(src) {
    const modal = document.getElementById('image-modal');
    const img = document.getElementById('full-size-image');
    img.src = src;
    modal.style.display = 'flex';
}

function hideImageModal() {
    document.getElementById('image-modal').style.display = 'none';
}

// Закрытие по клику вне изображения
document.getElementById('image-modal').addEventListener('click', function(e) {
    if(e.target === this || e.target.classList.contains('image-container')) {
        hideImageModal();
    }
})


function hideModal() {
    const modalImg = document.getElementById('modal-image');
    const statusIcon = document.getElementById('status-icon');
    
   // modalImg.src = '/static/images/no-image.jpg';
    statusIcon.style.display = 'none'; // Скрываем иконку при закрытии
    document.getElementById('modal').style.display = 'none';
    currentEventData = null;
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

function loadPostStatusIcons() {
    fetch('/get_all_events_status')
        .then(response => response.json())
        .then(statuses => {
            document.querySelectorAll('.post').forEach(post => {
                const eventId = post.dataset.eventId; // Получаем ID из data-атрибута
                const icon = post.querySelector('.post-status-icon');
                
                if (eventId && statuses[eventId]) {
                    icon.style.display = 'block';
                    icon.src = `/static/images/${statuses[eventId]}Mini.png`;
                }
            });
        });
}

function getEventIdFromPost(post) {
    if (!post) return null;
    return parseInt(post.dataset.eventId) || null;
}


async function updateDescription(e) {
    e.preventDefault();
    const description = document.getElementById('user-description').value;
    
    try {
        const response = await fetch('/update_description', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ description })
        });

        if (!response.ok) throw new Error('Ошибка сохранения');
        alert('Описание успешно обновлено!');
    } catch (error) {
        console.error('Ошибка:', error);
        alert(error.message);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const friendSearch = document.getElementById('friend-search');
    const searchResults = document.getElementById('search-results');

    if (!friendSearch || !searchResults) {
        console.error('Один из элементов поиска не найден!');
        return;
    }

    friendSearch.addEventListener('input', function(e) {
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            searchResults.style.display = 'none';
            return;
        }
        
        fetch(`/search_users?q=${encodeURIComponent(query)}`)
            .then(response => {
                if (!response.ok) throw new Error('Ошибка сети');
                return response.json();
            })
            .then(users => {
                searchResults.innerHTML = users.map(user => `
                    <div class="user-result" data-user-id="${user.id}">
                        <img src="${user.avatar}" class="user-avatar" alt="Аватар">
                        <span>${user.username}</span>
                        <button class="menu-btn add-friend-btn" 
                                onclick="sendFriendRequest(${user.id}, this)">
                            Добавить
                        </button>
                    </div>
                `).join('');
                searchResults.style.display = 'block';
            })
            .catch(error => {
                console.error('Ошибка:', error);
                searchResults.style.display = 'none';
            });
    });
});

function sendFriendRequest(userId, btn) {
    btn.disabled = true;
    btn.textContent = 'Отправка...';
    
    fetch('/add_friend', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({friend_id: userId})
    })
    .then(response => {
        if(response.ok) {
            btn.textContent = 'Запрос отправлен!';
        } else {
            btn.textContent = 'Ошибка';
            setTimeout(() => btn.remove(), 2000);
        }
    })
    .catch(() => {
        btn.textContent = 'Ошибка соединения';
        setTimeout(() => btn.remove(), 2000);
    });
}

function loadFriendRequests() {
    const container = document.getElementById('friend-requests-list');
    
    // Проверка существования элемента
    if (!container) {
        console.error('Элемент friend-requests-list не найден!');
        return;
    }

    fetch('/friend_requests')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(requests => {
            // Проверка на пустой массив
            if (!requests.length) {
                container.innerHTML = '<p class="empty-message">Нет входящих запросов</p>';
                return;
            }

            // Генерация HTML
            container.innerHTML = requests.map(req => `
                <div class="request-item" data-request-id="${req.id}">
                    <span>${req.sender} (${new Date(req.created_at).toLocaleDateString()})</span>
                    <div class="request-actions">
                        <button class="menu-btn accept-btn" 
                                onclick="handleFriendRequestResponse('${req.id}', 'accept')">
                            Принять
                        </button>
                        <button class="menu-btn reject-btn" 
                                onclick="handleFriendRequestResponse('${req.id}', 'reject')">
                            Отклонить
                        </button>
                    </div>
                </div>
            `).join('');
        })
        .catch(error => {
            console.error('Ошибка загрузки запросов:', error);
            container.innerHTML = '<p class="error-message">Ошибка загрузки данных</p>';
        });
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('friend-requests-list')) {
        loadFriendRequests();
    }
});

// Обработка ответа
function handleFriendRequestResponse(requestId, action) {
    fetch('/respond_friend_request', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            request_id: requestId,
            action: action
        })
    })
    .then(response => {
        if (response.ok) {
            loadFriendRequests(); // Обновляем список
            alert(action === 'accept' ? 'Запрос принят!' : 'Запрос отклонен');
        }
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

async function updatePrivacy(e) {
    e.preventDefault();
    const isPrivate = document.getElementById('privacy-checkbox').checked;
    
    try {
        const response = await fetch('/update_privacy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ is_private: isPrivate })
        });

        if (response.ok) {
            alert('Настройки приватности обновлены!');
        } else {
            alert('Ошибка сохранения');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка соединения');
    }
}