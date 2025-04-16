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




    const statusIcon = document.getElementById('status-icon');
    
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
                    if (postEventId === eventId) {
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
    const statusIcon = document.getElementById('status-icon');
    
   // modalImg.src = '/static/images/no-image.jpg';
    statusIcon.style.display = 'none'; // Скрываем иконку при закрытии
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

function loadPostStatusIcons() {
    fetch('/get_all_events_status')
        .then(response => response.json())
        .then(statuses => {
            document.querySelectorAll('.post').forEach(post => {
                const eventId = getEventIdFromPost(post);
                const icon = post.querySelector('.post-status-icon');
                
                // Сброс к состоянию по умолчанию
                icon.style.display = 'none';
                icon.src = '/static/images/nullMini.png';

                if (eventId !== null && statuses[eventId]) {
                    icon.style.display = 'block';
                    icon.src = `/static/images/${statuses[eventId]}Mini.png`;
                }
            });
        });
}

function getEventIdFromPost(post) {
    const onclickText = post.getAttribute('onclick');
    if (!onclickText) return null;
    const match = onclickText.match(/showModal\(\s*(\d+)/);
    return match ? parseInt(match[1], 10) : null;
}