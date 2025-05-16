const menuIcon = document.querySelector('.menu-icon');
const userMenu = document.getElementById('userMenu');


// Глобальная переменная для хранения данных о текущем мероприятии
let currentEventData = null;
let currentStatsEventId = null;


document.addEventListener('DOMContentLoaded', () => {
    loadPostStatusIcons();
});

if (menuIcon && userMenu) {
    let isMenuOpen = false;
    
    menuIcon.addEventListener('click', function(e) {
        isMenuOpen = !isMenuOpen;
        userMenu.classList.toggle('visible', isMenuOpen);
        e.stopPropagation();
    });

    // Закрытие при клике вне меню
    document.addEventListener('click', function(e) {
        if (!userMenu.contains(e.target)) {
            userMenu.classList.remove('visible');
            isMenuOpen = false;
        }
    });
    
    userMenu.addEventListener('mouseleave', function() {
        if (!isMenuOpen) return;
        timeoutId = setTimeout(() => {
            userMenu.classList.remove('visible');
            isMenuOpen = false;
        }, 300);
    });
} else {
    console.log('User menu elements not found - skipping hover logic');
}

function handlePostClick(element) {
    if (!document.getElementById('modal')) {
        console.error('Модальное окно не инициализировано');
        return;
    }
    if (event.target.closest('.stats-btn')) return;
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
    const modal = document.getElementById('modal');
    if (!modal) {
        console.error('Модальное окно не найдено!');
        return;
    }
    currentEventData = eventData;
    eventId = currentEventData.eventId;
    eventData.tempAccess = false;
    if (eventData.isPrivate && !checkAccess()) {
        showPasswordPrompt();
    } else {
        showEventContent();
    }
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

    //История просмотров
    try {
        trackEventView(eventData.eventId); // Добавляем вызов трекера
    } catch (e) {
        console.error('Ошибка инициализации трекера:', e);
    }

    // Установить ID мероприятия для рейтинга
    const stars = document.querySelectorAll('#modal-star-rating span');
    stars.forEach(star => {
        star.style.color = '#ddd';
        star.classList.remove('active');
    });
    document.getElementById('modal-star-rating').dataset.eventId = eventData.eventId;
    updateRatingStars(eventData.eventId);
    loadComments(eventData.eventId);
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

function trackEventView(eventId) {
    fetch('/track_view', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ event_id: eventId })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { 
                throw new Error(err.error || 'Ошибка сети') 
            });
        }
        return response.json();
    })
    .then(data => {
        if (!data.success) {
            console.warn('Не удалось сохранить просмотр:', data.error);
        }
    })
    .catch(error => {
        console.error('Ошибка:', error.message);
    });
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
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ password: password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentEventData.tempAccess = true; // Временный флаг
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
    document.getElementById('modal-organizer').textContent = e.organizerUsername;
    document.getElementById('modal-organizer-email').textContent = e.organizerEmail;

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
    const organizerLink = document.getElementById('modal-organizer');
    organizerLink.href = `/profile/${e.organizerUsername}`;
    organizerLink.textContent = e.organizerUsername || "Не указан";

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
        document.getElementById('modal-online-info').textContent = e.onlineInfo || "Информация не указана";
        document.getElementById('modal-map').style.display = 'none'; // Скрываем карту
        document.getElementById('modal-map').innerHTML = ''; // Очищаем контейнер
    } else {
        document.getElementById('location-info').style.display = 'block';
        document.getElementById('online-info').style.display = 'none';
        document.getElementById('modal-map').style.display = 'block'; // Показываем карту
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

function checkAccess() {
    return currentEventData?.tempAccess === true;
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


const imageModal = document.getElementById('image-modal');

if (imageModal) {
    imageModal.addEventListener('click', function(e) {
        if(e.target === this || e.target.classList.contains('image-container')) {
            hideImageModal();
        }
    })
}
else {
    console.warn('Элемент #image-modal не найден, обработчик не добавлен.');
}


function hideModal() {
    const modalImg = document.getElementById('modal-image');
    const statusIcon = document.getElementById('status-icon');
    
    if (currentEventData) {
        currentEventData.tempAccess = false;
    }

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
                        <img src="${user.avatar_url 
                            ? '/static/' + user.avatar_url 
                            : '/static/images/default-avatar.png'}" 
                             class="user-avatar"
                             alt="${user.username}">
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
            if (!requests.length) {
                container.innerHTML = '<p class="empty-message">Нет входящих запросов</p>';
                return;
            }

            container.innerHTML = requests.map(req => `
                <div class="request-item" data-request-id="${req.id}">
                    <img src="${req.sender_avatar ? '/static/' + req.sender_avatar : '/static/images/default-avatar.png'}" 
                         class="user-avatar"
                         alt="${req.sender}">
                    <span>${req.sender}</span>
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
            //alert(action === 'accept' ? 'Запрос принят!' : 'Запрос отклонен');
            window.location.reload();
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


let selectedFriends = new Set();

function toggleFriendList() {
    const modal = document.getElementById('friend-list-modal');
    if (modal.style.display === 'none') {
        fetch('/get_friends')
            .then(response => response.json())
            .then(friends => {
                const container = document.getElementById('modal-friends-container');
                container.innerHTML = friends.map(friend => `
                    <div class="friend-item" data-friend-id="${friend.id}">
                        <label>
                            <input type="checkbox" 
                                   onchange="toggleFriendSelection(${friend.id})">
                            ${friend.username}
                        </label>
                    </div>
                `).join('');
                modal.style.display = 'block';
            });
    } else {
        modal.style.display = 'none';
        selectedFriends.clear();
    }
}

function toggleFriendSelection(friendId) {
    if (selectedFriends.has(friendId)) {
        selectedFriends.delete(friendId);
    } else {
        selectedFriends.add(friendId);
    }
}

function sendRecommendation() {
    if (!currentEventData || selectedFriends.size === 0) {
        alert('Выберите друзей!');
        return;
    }
    
    fetch('/send_recommendation', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            event_id: currentEventData.eventId,
            friend_ids: Array.from(selectedFriends)
        })
    })
    .then(response => {
        if (!response.ok) throw new Error('Ошибка сервера');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert('Рекомендации отправлены!');
            toggleFriendList();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Ошибка отправки: ' + error.message);
    });
}

function respondToInvitation(invitationId, action) {
    fetch('/respond_invitation', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            invitation_id: invitationId,
            action: action
        })
    }).then(() => window.location.reload());
}

function handleResponse(recommendationId, action) {
    const item = document.getElementById(`invitation-${recommendationId}`);
    
    fetch('/respond_invitation', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            recommendation_id: recommendationId,
            action: action
        })
    })
    .then(response => {
        if (response.ok) {
            item.classList.add('removing');
            setTimeout(() => item.remove(), 300);
        }
    });
}

// Обработчик клика вне модального окна
window.onclick = function(event) {
    const modal = document.getElementById('map-modal');
    if (event.target == modal) {
        hideMapModal();
    }
    
    const mainModal = document.getElementById('modal');
    if (event.target == mainModal) {
        hideModal();
    }
}

async function updateOccupation(e) {
    e.preventDefault();
    const occupation = document.getElementById('user-occupation').value;
    
    try {
        const response = await fetch('/update_occupation', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ occupation })
        });
        
        if (!response.ok) throw new Error('Ошибка сохранения');
        alert('Данные успешно обновлены!');
    } catch (error) {
        console.error('Ошибка:', error);
        alert(error.message);
    }
}

function confirmDelete(eventId) {
    if (confirm('Вы уверены, что хотите удалить это мероприятие?')) {
        fetch(`/delete_event/${eventId}`, {
            method: 'DELETE',
        }).then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                alert('Ошибка при удалении мероприятия');
            }
        });
    }
}

async function updateAvatar(e) {
    e.preventDefault();
    const formData = new FormData();
    formData.append('avatar', document.getElementById('avatar-input').files[0]);

    try {
        const response = await fetch('/update_avatar', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            document.querySelector('.user-avatar').src = `/static/${data.avatar_url}`;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

function enable2FA() {
    fetch('/generate-2fa-secret', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            document.getElementById('2fa-setup').style.display = 'block';
            document.getElementById('2fa-secret').textContent = data.secret;
            document.getElementById('2fa-qrcode').src = data.qrcode;
        });
}

// Для активации 2FA в профиле
function verify2FA() {
    const code = document.getElementById('2fa-code').value;
    fetch('/verify-2fa-setup', {  // Изменили URL
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code })
    })
    .then(response => {
        if (response.ok) {
            window.location.reload();
        } else {
            alert('Неверный код!');
        }
    });
}

// Для входа с 2FA (новый обработчик)
function verifyLogin2FA(code) {
    fetch('/verify-2fa-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code })
    })
    .then(response => {
        if (response.ok) {
            window.location.href = '/';
        } else {
            showError('Неверный код подтверждения');
        }
    });
}


function disable2FA() {
    if (confirm('Вы уверены, что хотите отключить двухфакторную аутентификацию?')) {
        fetch('/disable-2fa', { method: 'POST' })
            .then(() => window.location.reload());
    }
}

// Переключение вкладок
function switchTab(tabId) {
    // Убираем активные классы
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    // Добавляем активные классы выбранной вкладке
    document.querySelector(`[onclick="switchTab('${tabId}')"]`).classList.add('active');
    document.getElementById(tabId).classList.add('active');
}


function toggleFavoriteTag(tagId) {
    const tagItem = document.querySelector(`.profile-tag-item[data-tag-id="${tagId}"]`);
    
    fetch('/toggle_tag', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ tag_id: tagId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            tagItem.classList.toggle('profile-selected');
            const button = tagItem.querySelector('.profile-tag-toggle');
            button.textContent = data.action === 'added' ? '✓' : '+';
        }
    })
    .catch(error => console.error('Error:', error));
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('modal-star-rating').addEventListener('click', handleRatingClick);
});


// Обработчик mouseover
document.getElementById('modal-star-rating').addEventListener('mouseover', e => {
    const star = e.target.closest('[data-value]');
    if (!star) return;
    
    const hoverValue = parseInt(star.dataset.value);
    const stars = document.querySelectorAll('#modal-star-rating span');
    
    
    stars.forEach(s => {
        const value = parseInt(s.dataset.value);
        s.style.color = value <= hoverValue ? '#ffa500' : '#ddd';
    });
});

// Обработчик mouseleave
document.getElementById('modal-star-rating').addEventListener('mouseleave', () => {
    const stars = document.querySelectorAll('#modal-star-rating span');
    const userRating = parseInt(
        document.querySelector('#modal-star-rating span.active')?.dataset.value || 0
    );
    
    stars.forEach(star => {
        const value = parseInt(star.dataset.value);
        // Если есть оценка пользователя - подсветить её, иначе все серые
        star.style.color = value <= userRating ? '#ffa500' : '#ddd';
    });
});

// Функция для оценки
function handleRatingClick(e) {
    const star = e.target.closest('[data-value]');
    if (!star) return;

    const eventId = document.getElementById('modal-star-rating')?.dataset.eventId;
    const rating = parseInt(star.dataset.value);
    
    if (!eventId || isNaN(rating)) {
        alert('Ошибка: некорректные данные');
        return;
    }

    fetch('/rate_event', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ event_id: eventId, rating })
    })
    .then(async res => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        // Обновление интерфейса
        const stars = document.querySelectorAll('#modal-star-rating span');
        stars.forEach(s => s.classList.remove('active'));
        
        if (data.userRating > 0) {
            stars.forEach(s => {
                if (parseInt(s.dataset.value) <= data.userRating) {
                    s.classList.add('active');
                }
            });
        }
        document.querySelectorAll(`.post[data-event-id="${eventId}"] .average-rating`).forEach(el => {
            el.textContent = data.average.toFixed(1);
        });
        
        document.querySelectorAll(`.post[data-event-id="${eventId}"] .ratings-count`).forEach(el => {
            el.textContent = `(${data.count})`;
        });
        document.getElementById('modal-average-rating').textContent = 
            data.average.toFixed(1);
        document.getElementById('modal-ratings-count').textContent = 
            `(${data.count})`;
    })
    .catch(err => alert(err.message));
}

// Функция обновления звезд
async function updateRatingStars(eventId) {
    try {
        const response = await fetch(`/get_ratings/${eventId}`);
        const { average, count, userRating } = await response.json();
        
        const stars = document.querySelectorAll('#modal-star-rating span');
        const averageRatingEl = document.getElementById('modal-average-rating');
        const ratingsCountEl = document.getElementById('modal-ratings-count');

        averageRatingEl.textContent = average > 0 ? average.toFixed(1) : 'Нет оценок';
        ratingsCountEl.textContent = count > 0 ? `(${count})` : '';

        stars.forEach(star => {
            star.classList.remove('active', 'rated');
            star.style.color = '#ddd';
        });

        if (count > 0) {
            stars.forEach(star => {
                const value = parseInt(star.dataset.value);
                if (value <= average) {
                    star.classList.add('rated');
                }
            });
        }
        if (userRating > 0) {
            stars.forEach(star => {
                const value = parseInt(star.dataset.value);
                if (value <= userRating) {
                    star.classList.add('active');
                }
            });
        }

    } catch (error) {
        console.error('Ошибка обновления звезд:', error);
        document.getElementById('modal-average-rating').textContent = 'Ошибка';
        ratingsCountEl.textContent = '';
    }
}

//Статистика мероприятия
function showEventStats(event, eventId) {
    event.stopPropagation(); // Блокируем всплытие события
    event.preventDefault(); // Отменяем стандартное поведение
    // Закрыть плашку при повторном клике
    if (currentStatsEventId === eventId) {
        hideStats();
        return;
    }
    
    fetch(`/get_event_stats/${eventId}`)
    .then(response => {
        if (response.status === 401) {
            alert('Требуется авторизация!');
            window.location.href = '/login';
            return;
        }
        if (response.status === 403) {
            throw new Error('Это не ваше мероприятие');
        }
        if (response.status === 404) {
            throw new Error('Мероприятие удалено');
        }
        if (!response.ok) {
            throw new Error(`Ошибка ${response.status}`);
        }
        return response.json();
    })
    .then(stats => {
        // Проверка на наличие данных
        if (!stats || typeof stats !== 'object') {
            throw new Error('Некорректные данные');
        }

        // Форматирование данных
        const formattedStats = {
            average_rating: stats.average_rating || 0,
            views: stats.views ?? 'Нет данных',
            planned: stats.planned ?? 0,
            attended: stats.attended ?? 0,
            recommendations: stats.recommendations ?? 0
        };

        // Обновление UI
        document.getElementById('stat-rating').textContent = 
            formattedStats.average_rating.toFixed(1);
        document.getElementById('stat-views').textContent = 
            formattedStats.views;
        document.getElementById('stat-planned').textContent = 
            formattedStats.planned;
        document.getElementById('stat-attended').textContent = 
            formattedStats.attended;
        document.getElementById('stat-recommend').textContent = 
            formattedStats.recommendations;

        // Показ плашки
        document.getElementById('stats-popup').style.display = 'block';
        currentStatsEventId = eventId;
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert(`Ошибка загрузки: ${error.message}`);
        hideStats();
    });
}

function hideStats() {
    document.getElementById('stats-popup').style.display = 'none';
    currentStatsEventId = null;
}

// Закрытие при клике вне плашки
document.addEventListener('click', (e) => {
    const statsPopup = document.getElementById('stats-popup');
    if (statsPopup && !statsPopup.contains(e.target)) {
        hideStats();
    }
});

function confirmDelete(eventId) {
            if (confirm('Вы уверены, что хотите удалить это мероприятие?')) {
                fetch(`/delete_event/${eventId}`, {
                    method: 'DELETE',
                }).then(response => {
                    if (response.ok) {
                        window.location.reload();
                    } else {
                        alert('Ошибка при удалении мероприятия');
                    }
                });
            }
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

function applySorting(value) {
    const params = new URLSearchParams(window.location.search);
    params.set('sort', value);
    window.location.search = params.toString();
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebarMenu');
    const overlay = document.getElementById('sidebarOverlay');
    const menuIcon = document.querySelector('.menu-icon');
    
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
    menuIcon.classList.toggle('active');
    
    // Блокировка скролла при открытом меню
    document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
}

// Закрытие меню при клике на оверлей
document.getElementById('sidebarOverlay').addEventListener('click', toggleSidebar);

// Закрытие меню при клике на пункт меню (если нужно)
document.querySelectorAll('.sidebar-item').forEach(item => {
    item.addEventListener('click', toggleSidebar);
});

function toggleSubscription(organizerId, btn, isUnsubscribe = false) {
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = isUnsubscribe ? 'Отписываюсь...' : 'Подписываюсь...';
    
    fetch('/toggle_subscription', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({organizer_id: organizerId})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (isUnsubscribe) {
                // Удаляем элемент из списка
                const item = btn.closest('.friend-item');
                item.style.opacity = '0';
                setTimeout(() => item.remove(), 300);
                
                // Проверяем, остались ли подписки
                if (!document.querySelector('#subscriptions-list .friend-item')) {
                    document.getElementById('subscriptions-list').innerHTML = 
                        '<p class="empty-message">Вы не подписаны ни на одного организатора</p>';
                }
            } else {
                // Обновляем UI для кнопки подписки
                btn.textContent = '✓ Вы подписаны';
                btn.style.background = '#4CAF50';
                btn.onclick = null;
                
                // Можно добавить анимацию или обновить список
                if (window.location.pathname === '/subscriptions') {
                    window.location.reload(); // Проще перезагрузить страницу
                }
            }
        } else {
            btn.textContent = originalText;
            alert(data.error || 'Произошла ошибка');
        }
        btn.disabled = false;
    })
    .catch(error => {
        console.error('Error:', error);
        btn.textContent = originalText;
        btn.disabled = false;
        alert('Ошибка соединения');
    });
}

function removeFriend(friendId, btn) {
    if (!confirm('Вы уверены, что хотите удалить этого пользователя из друзей?')) {
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Удаление...';

    fetch('/remove_friend', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({friend_id: friendId})
    })
    .then(response => {
        if (!response.ok) throw new Error('Ошибка сервера');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Анимация удаления
            const friendItem = btn.closest('.friend-item');
            friendItem.style.opacity = '0';
            setTimeout(() => friendItem.remove(), 300);
            
            // Если список пуст, показываем сообщение
            if (!document.querySelector('#friends-list .friend-item')) {
                document.getElementById('friends-list').innerHTML = 
                    '<p class="empty-message">У вас пока нет друзей</p>';
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        btn.disabled = false;
        btn.textContent = 'Удалить';
        alert('Ошибка при удалении: ' + error.message);
    });
}

function loadComments(eventId) {
    fetch(`/get_comments?event_id=${eventId}`)
        .then(response => response.json())
        .then(comments => {
            const container = document.getElementById('comments-container');
            container.innerHTML = comments.map(comment => `
                <div class="comment-item" data-comment-id="${comment.id}">
                    <div class="comment-header">
                        <img src="${comment.avatar}" class="comment-avatar" 
                            onerror="this.src='/static/images/default_avatar.png'">
                        <div class="comment-meta">
                            <a href="/profile/${comment.username}" class="comment-author-link">
                                ${comment.username}
                            </a>
                            <span class="comment-date">${new Date(comment.created_at).toLocaleString()}</span>
                        </div>
                        ${comment.can_delete ? 
                            `<div class="delete-comment" onclick="deleteComment(${comment.id})">Удалить</div>` : 
                            ''}
                    </div>
                    <p>${escapeHtml(comment.text)}</p>
                </div>
            `).join('');
        });
}


function handleCommentPost() {
    const textArea = document.getElementById('comment-text');
    const alertBox = document.getElementById('comment-auth-alert');
    
    // Сброс предыдущих сообщений
    alertBox.style.display = 'none';
    textArea.style.borderColor = '#ff6200';

    // Проверка авторизации
    if (!isUserLoggedIn()) {
        textArea.disabled = true;
        alertBox.style.display = 'block';
        textArea.style.borderColor = '#ff4444';
        return;
    }   

    const text = textArea.value.trim();
    if (!text) {
        alertBox.textContent = "Комментарий не может быть пустым!";
        alertBox.style.display = 'block';
        return;
    }

    postComment(text);
}

function isUserLoggedIn() {
    return fetch('/check_auth', { credentials: 'include' })
        .then(response => response.ok)
        .catch(() => false);
}

async function postComment(text) {
    try {
        const response = await fetch('/add_comment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'include',
            body: JSON.stringify({
                event_id: currentEventData.eventId,
                text: escapeHtml(text)
            })
        });

        if (response.status === 401) {
            throw new Error('Требуется авторизация');
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Ошибка сервера');
        }

        document.getElementById('comment-text').value = '';
        loadComments(currentEventData.eventId);
    } catch (error) {
        const alertBox = document.getElementById('comment-auth-alert');
        alertBox.innerHTML = `❌ ${error.message}`;
        alertBox.style.display = 'block';
    }
}

// Утилита для экранирования HTML
function escapeHtml(unsafe) {
    return unsafe.replace(/[&<"'>]/g, m => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[m]));
}

async function deleteComment(commentId) {
    if (!confirm('Удалить комментарий?')) return;

    try {
        const response = await fetch(`/delete_comment/${commentId}`, {
            method: 'DELETE',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (response.ok) {
            document.querySelector(`[data-comment-id="${commentId}"]`).remove();
        } else {
            const error = await response.json();
            alert(error.error || 'Ошибка удаления');
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const eventId = urlParams.get('event_id');
    
    if (eventId) {
        fetch(`/get_event_data?event_id=${eventId}`)
            .then(response => response.json())
            .then(eventData => {
                showModal(eventData);
                history.replaceState({}, document.title, window.location.pathname);
            })
            .catch(error => console.error('Error loading event:', error));
    }
});

function copyEventLink() {
    const eventId = currentEventData.eventId;
    const link = `${window.location.origin}/event/${eventId}`;
    
    navigator.clipboard.writeText(link)
        .then(() => alert('Ссылка скопирована в буфер обмена!'))
        .catch(() => prompt('Скопируйте ссылку вручную:', link));
}