from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
import folium
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
import math
from sqlalchemy.orm import joinedload
from pyotp import TOTP, random_base32
import qrcode
from io import BytesIO
import base64
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)
app.secret_key = '6jujmgkxze4png8ch3xg8r3052a01ia'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tesamye.ifelse@gmail.com'
app.config['MAIL_PASSWORD'] = 'dzfo lmul vkkv yymx'
app.config['MAIL_DEFAULT_SENDER'] = 'tesamye.ifelse@gmail.com'
app.config['SECRET_KEY'] = '6jujmgkxze4png8ch3xg8r3052a01ia'
app.config['SECURITY_PASSWORD_SALT'] = 'salt52n1o0jnv2omiv0kmn94aoaomm6sex5'
app.config['SECURITY_PASSWORD_RESET_SALT'] = 'passwordreset1xms4p9t8qyiapwpe2zsq'
app.config['MAX_AVATAR_SIZE'] = 2 * 1024 * 1024  # 2MB
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)
app.config['MAX_LOGIN_ATTEMPTS'] = 20  # Максимальное количество попыток входа
app.config['LOGIN_BLOCK_TIME'] = 300  # Время блокировки в секундах (5 минут)

Session(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


ROLE_TRANSLATIONS = {
    'participant': 'Участник',
    'organizer': 'Организатор',
    'admin': 'Администратор',
    'moderator': 'Модератор'
}

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='participant')
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmed_on = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_private = db.Column(db.Boolean, default=False, nullable=False)
    occupation = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(200), nullable=True)
    validation = db.Column(db.String(20), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    totp_secret = db.Column(db.String(32), nullable=True)
    is_2fa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    is_blocked = db.Column(db.Boolean, default=False)
    blocked_until = db.Column(db.DateTime, nullable=True)
    block_reason = db.Column(db.Text, nullable=True)
    favorite_organizers = db.relationship(
        'User', 
        secondary='user_organizer',
        primaryjoin='UserOrganizer.user_id == User.id',
        secondaryjoin='UserOrganizer.organizer_id == User.id',
        backref=db.backref('followers', lazy='dynamic')
    )
    @property
    def unread_event_ids(self):
        return [n.event_id for n in self.notifications if not n.is_read]
    
    favorite_tags = db.relationship(
        'Tag',
        secondary='user_tag',
        backref=db.backref('users_favorited', lazy='dynamic')
    )
    event_statuses = db.relationship(
        'UserEventStatus',
        backref=db.backref('user', lazy='joined'),
        lazy='dynamic'
    )

    @property
    def friends(self):
        """Получить всех подтвержденных друзей"""
        sent = [f.receiver for f in self.sent_requests if f.status == 'accepted']
        received = [f.sender for f in self.received_requests if f.status == 'accepted']
        return list(set(sent + received))
    
    def calculate_recommendation_scores(self, user_coords=None):
        """Рассчитывает баллы для рекомендаций"""
        events = Event.query.filter_by(is_active=True).options(joinedload(Event.tags)).all()
        scores = []
        
        favorite_tags = {t.id for t in self.favorite_tags}
        friend_ids = [f.id for f in self.friends]
        
        for event in events:
            score = 0

            # 1. Теги
            common_tags = len(favorite_tags & {t.id for t in event.tags})
            score += common_tags * 15

            # 2. Рейтинг
            score += float(event.average_rating) * 5  # Явное преобразование

            # 3. Свежесть (исправленная формула)
            now = datetime.utcnow()
            if event.date_time > now:
                delta_days = (event.date_time - now).days
                score += 80  # Базовый балл
                
                if delta_days <= 3:
                    deduction = delta_days * 5
                elif delta_days <= 7:
                    deduction = 15 + (delta_days - 3) * 3
                elif delta_days <= 30:
                    deduction = 27 + (delta_days - 7) * 1
                else:
                    deduction = 50 + (delta_days - 30) * 0.2
                
                score -= deduction
            else:
                score -= 50  #  штраф за прошедшие

            # 4. Приватность
            if event.is_private:
                score -= 1000

            # 5. Рекомендации друзей
            rec_count = Recommendation.query.filter(
                Recommendation.event_id == event.id,
                Recommendation.sender_id.in_(friend_ids)
            ).count()
            score += 30 * rec_count

            # 6. Популярность (исправление формулы)
            views = event.views_count or 0
            if views > 0:
                if views < 10:
                    score += views
                else:
                    score += 5 + (math.log(views/10, 2) * 5)

            # 7. Близость (только если есть координаты пользователя)
            if user_coords and event.lat and event.lng:
                distance = haversine(
                    user_coords[0], user_coords[1],
                    event.lat, event.lng
                )
                if distance <= 10:
                    proximity_score = 100 * (1 - (distance / 10)) ** 2
                    score += proximity_score

            scores.append((event, score))
        
        return sorted(scores, key=lambda x: x[1], reverse=True)


# Модель тега
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

# Модель мероприятия
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    format = db.Column(db.String(20), nullable=False)  # 'online' или 'offline'
    location_name = db.Column(db.String(200))  # Название места
    location_address = db.Column(db.String(200))  # Физический адрес
    online_info = db.Column(db.Text)  # Информация для онлайн мероприятий
    date_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    event_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_private = db.Column(db.Boolean, default=False)
    password = db.Column(db.String(100))  # Пароль для приватных мероприятий
    organizer = db.relationship('User', backref='events')
    tags = db.relationship('Tag', secondary='event_tag', backref='events')
    personalities = db.Column(db.JSON)
    user_statuses = db.relationship(
        'UserEventStatus',
        backref=db.backref('event', lazy='joined'),
        lazy='dynamic'
    )
    @hybrid_property
    def average_rating(self):
        return db.session.query(func.avg(Rating.rating)).filter(
            Rating.event_id == self.id
        ).scalar() or 0.0

    @property
    def ratings_count(self):
        return Rating.query.filter_by(event_id=self.id).count()
    
    @hybrid_property
    def views_count(self):
        return EventView.query.filter_by(event_id=self.id).count()
    
    @property
    def distance(self):
        return getattr(self, '_distance', None)
    
    @distance.setter
    def distance(self, value):
        self._distance = value

# Связующая таблица для тегов и мероприятий
class EventTag(db.Model):
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), primary_key=True)

# Связующая Модель для избранных организаторов 
class UserOrganizer(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

# Связующая Модель для избранных тегов 
class UserTag(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), primary_key=True)

# Связующая Модель для статуса мероприятий пользователя
class UserEventStatus(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), primary_key=True)
    status = db.Column(db.Enum('planned', 'attended', name='event_status'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 

# Модель друзей
class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Enum('pending', 'accepted', 'rejected', name='friendship_status'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи с пользователями
    sender = db.relationship('User', foreign_keys=[user_id], backref='sent_requests')
    receiver = db.relationship('User', foreign_keys=[friend_id], backref='received_requests')

# Модель рекоммендаций событий
class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    event = db.relationship('Event')

# Модель для отслеживания попыток ввода кода
class TwoFAAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    attempts = db.Column(db.Integer, default=0)
    last_attempt = db.Column(db.DateTime)
    blocked_until = db.Column(db.DateTime)

# Модель оценки мероприятия
class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='ratings')
    event = db.relationship('Event', backref='ratings')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'event_id', name='unique_user_event_rating'),
    )

# Модель для отслеживания просмотров мероприятий
class EventView(db.Model):
    __tablename__ = 'event_view'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), primary_key=True)
    last_viewed_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

db.Index('ix_recommendation_receiver', Recommendation.receiver_id)

# Модель для отслеживания попыток входа
class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    attempts = db.Column(db.Integer, default=0)
    last_attempt = db.Column(db.DateTime)
    blocked_until = db.Column(db.DateTime)

# Модель комментария
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='comments')
    event = db.relationship('Event', backref='comments')

# Модель для уведомлений о новых мероприятиях
class SubscriptionNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    organizer = db.relationship('User', foreign_keys=[organizer_id])
    event = db.relationship('Event')

# Создание таблиц и добавление начальных данных
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='participant1').first():
        hashed_pwd = bcrypt.generate_password_hash('pass123').decode('utf-8')
        user1 = User(
            username='participant1', 
            email='participant1@example.com', 
            password=hashed_pwd, 
            role='participant',
            email_confirmed=True
        )
        db.session.add(user1)
    
    if not User.query.filter_by(username='organizer1').first():
        hashed_pwd = bcrypt.generate_password_hash('org456').decode('utf-8')
        user2 = User(
            username='organizer1', 
            email='organizer1@example.com', 
            password=hashed_pwd, 
            role='organizer',
            email_confirmed=True,
            validation=None
        )
        db.session.add(user2)

    if not User.query.filter_by(username='moderator1').first():
        hashed_pwd = bcrypt.generate_password_hash('moderator789').decode('utf-8')
        user3 = User(
            username='moderator1', 
            email='moderator1@example.com', 
            password=hashed_pwd, 
            role='moderator',
            email_confirmed=True,
            validation=None
        )
        db.session.add(user3)

    if not User.query.filter_by(username='admin1').first():
        hashed_pwd = bcrypt.generate_password_hash('nimda').decode('utf-8')
        user4 = User(
            username='admin1', 
            email='admin1@example.com', 
            password=hashed_pwd, 
            role='admin',
            email_confirmed=True
        )
        db.session.add(user4)
    
    if not Tag.query.first():
        tags = ['музыка', 'отдых', 'искусство', 'культура', 'концерт']
        for tag_name in tags:
            db.session.add(Tag(name=tag_name))
    
    if not Event.query.first():
        organizer = User.query.filter_by(username='organizer1').first()
        events = [
            {
                "title": "Концерт в Минске",
                "description": "Живой концерт популярной группы.",
                "format": "offline",
                "location_name": "Концертный зал 'Минск'",  # Новое поле
                "location_address": "ул. Ленина, 10, Минск",  # Новое поле
                "date_time": datetime(2024, 11, 15, 19, 0),
                "duration": 120,
                "lat": 53.9,
                "lng": 27.5667,
                "event_type": "Концерт",
                "tags": ["музыка", "концерт"]
            },
            {
                "title": "Выставка картин",
                "description": "Экспозиция современных художников.",
                "format": "offline",
                "location_name": "Гродненский художественный музей",  # Новое поле
                "location_address": "ул. Советская, 5, Гродно",  # Новое поле
                "date_time": datetime(2024, 11, 20, 10, 0),
                "duration": 180,
                "lat": 53.6833,
                "lng": 23.8333,
                "event_type": "Выставка",
                "tags": ["искусство", "культура"]
            }
        ]
        for event_data in events:
            event = Event(
                title=event_data['title'],
                description=event_data['description'],
                organizer_id=organizer.id,
                format=event_data['format'],
                location_name=event_data['location_name'],  # Используем новое поле
                location_address=event_data['location_address'],  # Используем новое поле
                date_time=event_data['date_time'],
                duration=event_data['duration'],
                lat=event_data['lat'],
                lng=event_data['lng'],
                event_type=event_data['event_type']
            )
            db.session.add(event)
            db.session.flush()
            for tag_name in event_data['tags']:
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag:
                    db.session.add(EventTag(event_id=event.id, tag_id=tag.id))
        db.session.commit()

# Вспомогательная функция для проверки расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.context_processor
def inject_nearby_status():
    return {'nearby_filter_active': 'nearby' in request.args}


# Главная страница
@app.route('/', methods=['GET'])
def home():
    search_query = request.args.get('search', '').strip()
    selected_tag = request.args.get('tag', '').strip()
    selected_sort = request.args.get('sort', 'recommended' if 'username' in session else 'newest').strip()
    
    query = Event.query.filter_by(is_active=True)
    
    user_coords = None
    if 'nearby' in request.args:
        try:
            lat_str, lng_str = request.args['nearby'].split(',')
            user_lat = float(lat_str)
            user_lng = float(lng_str)
            user_coords = (user_lat, user_lng)
        except:
            pass

    # Фильтры поиска и тегов
    if search_query:
        query = query.filter(
            (Event.title.ilike(f'%{search_query}%')) | 
            (Event.description.ilike(f'%{search_query}%')) | 
            (Event.tags.any(Tag.name.ilike(f'%{search_query}%')))
        )
    
    if selected_tag:
        tag = Tag.query.filter_by(name=selected_tag).first()
        if tag:
            query = query.join(Event.tags).filter(Tag.id == tag.id)
    
    # Логика сортировки
    if selected_sort == 'recommended' and 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user_coords = None
            if 'nearby' in request.args:
                try:
                    lat_str, lng_str = request.args['nearby'].split(',')
                    user_coords = (float(lat_str), float(lng_str))
                except:
                    pass
            recommended = user.calculate_recommendation_scores(user_coords)
            events = [e for e, _ in recommended]
        else:
            events = query.order_by(Event.created_at.desc()).all()
    else:
        # Если выбрано "Для вас" без авторизации - сбросить на дефолт
        if selected_sort == 'recommended':
            selected_sort = 'newest'
        # Сортировки, основанные на SQL
        if selected_sort == 'popular':
            query = query.outerjoin(EventView).group_by(Event.id).order_by(func.count(EventView.event_id).desc())
        elif selected_sort == 'rating':
            query = query.outerjoin(Rating).group_by(Event.id).order_by(func.coalesce(func.avg(Rating.rating), 0).desc())
        elif selected_sort == 'oldest':
            query = query.order_by(Event.created_at.asc())
        else:  # newest
            query = query.order_by(Event.created_at.desc())
        
        events = query.all()
    
    filtered_events = []
    for event in events:
        if user_coords and event.lat and event.lng:
            distance = haversine(user_coords[0], user_coords[1], event.lat, event.lng)
            if distance <= 10:
                event.distance = distance
                filtered_events.append(event)
        else:
            event.distance = None
            filtered_events.append(event)

    if user_coords:
        events = [e for e in filtered_events if e.distance is not None]
    else:
        events = filtered_events

    tags = Tag.query.all()
    
    return render_template('index.html', 
                         posts=events,
                         nearby_filter_active='nearby' in request.args,
                         tags=tags,
                         search_query=search_query,
                         selected_tag=selected_tag,
                         selected_sort=selected_sort)


@app.route('/login', methods=['GET', 'POST'])
#@limiter.limit("50 per minute")
def login():
    if request.method == 'POST':
        ip_address = request.remote_addr
        attempt = LoginAttempt.query.filter_by(ip_address=ip_address).first()
        
        # Если записи нет, создаём новую
        if not attempt:
            attempt = LoginAttempt(ip_address=ip_address, attempts=0)
            db.session.add(attempt)
            db.session.commit()  # Фиксируем сразу, чтобы избежать проблем
        
        # Проверка блокировки
        if attempt.blocked_until and attempt.blocked_until > datetime.utcnow():
            time_left = (attempt.blocked_until - datetime.utcnow()).seconds
            return render_template('login.html', 
                                error=f"Слишком много попыток входа. Попробуйте снова через {time_left} секунд")
        
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        # Проверка блокировки пользователя
        if user and user.is_blocked and bcrypt.check_password_hash(user.password, password):
            error_msg = "Аккаунт заблокирован"
            if user.blocked_until:
                if user.blocked_until > datetime.utcnow():
                    error_msg += f" до {(user.blocked_until + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M')}"
                else:
                    user.is_blocked = False  # Автоматическая разблокировка
                    user.blocked_until = None
                    user.block_reason = None
                    db.session.commit()
            else:
                error_msg += " навсегда"
                
            if user.block_reason:
                error_msg += f". Причина: {user.block_reason}"
                
            return render_template('login.html', error=error_msg)

        if user and bcrypt.check_password_hash(user.password, password):
            # Успешный вход - сбрасываем счетчик попыток
            attempt.attempts = 0
            attempt.blocked_until = None
            db.session.commit()
            
            if not user.email_confirmed:
                return render_template('login.html', error="Пожалуйста, подтвердите ваш email перед входом.")
            
            if user.is_2fa_enabled:
                session['pending_2fa_user'] = user.username
                return redirect(url_for('verify_2fa_login'))

            session['username'] = username
            session['role'] = user.role
            return redirect(url_for('home'))
        else:
            # Неудачная попытка входа
            attempt.attempts += 1
            attempt.last_attempt = datetime.utcnow()
            
            if attempt.attempts >= app.config['MAX_LOGIN_ATTEMPTS']:
                attempt.blocked_until = datetime.utcnow() + timedelta(
                    seconds=app.config['LOGIN_BLOCK_TIME'])
            
            db.session.commit()
            
            return render_template('login.html', 
                                error="Неверный логин или пароль. Осталось попыток: {}".format(
                                    app.config['MAX_LOGIN_ATTEMPTS'] - attempt.attempts))
    
    return render_template('login.html', error=None)


# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        role = request.form.get('role')
        comment = request.form.get('comment', '')
        
        if not username or not email or not password or not password_confirm:
            return render_template('register.html', error="Все поля обязательны для заполнения")
        
        if password != password_confirm:
            return render_template('register.html', error="Пароли не совпадают")
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error="Пользователь с таким именем уже существует")
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error="Этот email уже зарегистрирован")
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        user_role = 'participant'
        validation = None
        if role in ['organizer', 'moderator']:
            validation = role

        user = User(
            username=username, 
            email=email, 
            password=hashed_password, 
            role=user_role,
            email_confirmed=False,
            validation=validation,
            comment=comment if role in ['organizer', 'moderator'] else None
        )
        db.session.add(user)
        db.session.commit()
        
        # Отправка письма с подтверждением
        token = serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])
        confirm_url = url_for('confirm_email', token=token, _external=True)
        
        msg = Message(
            subject="Подтверждение регистрации",
            recipients=[user.email],
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        msg.body = f"Для подтверждения email перейдите по ссылке: {confirm_url}"
        msg.html = render_template(
            'email_confirmation_message.html',
            confirm_url=confirm_url,
            username=user.username
        )
        
        try:
            mail.send(msg)
            return render_template('register.html',
                                success="Письмо с подтверждением отправлено!")
        except Exception as e:
            print(f"Ошибка отправки письма: {str(e)}")
            return render_template('register.html',
                                error=f"Ошибка отправки письма: {str(e)}")
    
    return render_template('register.html', error=None)

# Выход из системы
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('home'))

# Добавление мероприятия
@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if 'username' not in session:
        return redirect(url_for('home'))
    
    user = User.query.filter_by(username=session['username']).first()
    
    if not user or user.role == 'participant' or user.validation:
        return redirect(url_for('home'))
    
    tags = Tag.query.all()
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        format_type = request.form.get('format')
        location_name = request.form.get('location_name')
        location_address = request.form.get('location_address')
        online_info = request.form.get('online_info')
        date_time = datetime.strptime(request.form.get('date_time'), '%Y-%m-%dT%H:%M')
        duration = int(request.form.get('duration'))
        lat = float(request.form.get('lat', 0)) if format_type == 'offline' else None
        lng = float(request.form.get('lng', 0)) if format_type == 'offline' else None
        event_type = request.form.get('event_type')
        selected_tags = request.form.get('tags', '').split(',')
        selected_tags = [tag_id for tag_id in selected_tags if tag_id]
        is_private = request.form.get('is_private') == 'true'
        password = request.form.get('password') if is_private else None
        image_url = None
        personalities = []
        names = request.form.getlist('personality_name[]')
        links = request.form.getlist('personality_link[]')
        
        for name, link in zip(names, links):
            if name.strip():  # Добавляем только если указано имя
                personalities.append({"name": name.strip(), "link": link.strip()})

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_url = f'uploads/{filename}'

        user = User.query.filter_by(username=session['username']).first()
        event = Event(
            title=title,
            description=description,
            organizer_id=user.id,
            format=format_type,
            location_name=location_name,
            location_address=location_address,
            online_info=online_info,
            date_time=date_time,
            duration=duration,
            lat=lat,
            lng=lng,
            event_type=event_type,
            image_url=image_url,
            is_private=is_private,
            password=password,
            personalities=personalities
        )
        db.session.add(event)
        db.session.flush()
        for tag_id in selected_tags:
            tag = Tag.query.get(tag_id)
            if tag:
                db.session.add(EventTag(event_id=event.id, tag_id=tag.id))

        db.session.add(event)
        db.session.flush()
        for follower in user.followers:
            notification = SubscriptionNotification(
                user_id=follower.id,
                organizer_id=user.id,
                event_id=event.id
            )
            db.session.add(notification)
        
        db.session.commit()
        return redirect(url_for('home'))
    
    return render_template('add_event.html', tags=tags)

# страница подтверждения почты
@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=3600  # Токен действителен 1 час
        )
    except:
        return render_template('email_confirmation.html', error="Ссылка подтверждения недействительна или срок ее действия истек.")
    
    user = User.query.filter_by(email=email).first_or_404()
    
    if user.email_confirmed:
        return render_template('email_confirmation.html', message="Email уже подтвержден.")
    else:
        user.email_confirmed = True
        user.email_confirmed_on = datetime.utcnow()
        db.session.commit()
        
        # Автоматический вход после подтверждения
        session['username'] = user.username
        session['role'] = user.role
        
        return render_template('email_confirmation.html', 
                             success="Ваш email успешно подтвержден! Теперь вы можете пользоваться всеми возможностями сайта.")

# повторная отправка письма
@app.route('/resend-confirmation')
def resend_confirmation():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    
    if user.email_confirmed:
        return redirect(url_for('home'))
    
    token = serializer.dumps(user.email, salt=app.config['SECURITY_PASSWORD_SALT'])
    confirm_url = url_for('confirm_email', token=token, _external=True)
    
    msg = Message(
        'Подтвердите ваш email',
        recipients=[user.email],
        html=render_template(
            'email_confirmation_message.html',
            confirm_url=confirm_url,
            username=user.username
        )
    )
    mail.send(msg)
    
    return render_template('email_confirmation.html',
                         message="Письмо с подтверждением отправлено повторно.")

# Страница карты
@app.route('/map', methods=['GET'])
def show_map():
    events = Event.query.filter_by(is_active=True, is_private=False).all()
    m = folium.Map(location=[53.9, 27.5667], zoom_start=7)
    
    for event in events:
        if event.lat and event.lng:
            # Создаем popup с информацией о мероприятии
            popup = folium.Popup(f"""
                <b>{event.title}</b><br>
                {event.location_name}<br>
                {event.location_address}<br>
                <button onclick="window.parent.showEventFromMap({event.id})">Подробнее</button>
            """, max_width=300)
            
            # Добавляем маркер с дополнительными данными
            folium.Marker(
                [event.lat, event.lng],
                popup=popup,
                icon=folium.Icon(color='green' if any(s.status == 'planned' for s in event.user_statuses) else 'blue')
            ).add_to(m)
    
    map_html = m._repr_html_()
    
    # Добавляем данные о мероприятиях в HTML
    events_data = {
        event.id: {
            'title': event.title,
            'description': event.description,
            'locationName': event.location_name,
            'locationAddress': event.location_address,
            'dateTime': event.date_time.isoformat(),
            'organizerUsername': event.organizer.username,
            'eventType': event.event_type,
            'tags': [tag.name for tag in event.tags],
            'format': event.format,
            'duration': event.duration,
            'lat': event.lat,
            'lng': event.lng,
            'isPrivate': event.is_private,
            'imageUrl': event.image_url
        }
        for event in events if event.lat and event.lng
    }

    return render_template('map.html', map_html=map_html, events_data=events_data)


@app.route('/generate_map')
def generate_map():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    
    # Валидация координат
    if lat is None or lng is None:
        return jsonify({"error": "Invalid coordinates"}), 400
    
    # Создаем карту с маркером
    m = folium.Map(location=[lat, lng], zoom_start=15)
    folium.Marker([lat, lng]).add_to(m)
    return m._repr_html_()

# Добавление тега
@app.route('/add_tag', methods=['GET', 'POST'])
def add_tag():
    if 'username' not in session or session['role'] not in ['organizer', 'moderator', 'admin']:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        tag_name = request.form.get('tag_name')
        if tag_name and not Tag.query.filter_by(name=tag_name).first():
            db.session.add(Tag(name=tag_name))
            db.session.commit()
        return redirect(url_for('add_tag'))
    
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('add_tag.html', tags=tags)


@app.route('/update_event_status', methods=['POST'])
def update_event_status():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    event_id = data.get('event_id')
    status = data.get('status')
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        # Если статус 'none' - удаляем запись
        if status == 'none':
            UserEventStatus.query.filter_by(
                user_id=user.id,
                event_id=event_id
            ).delete()
        else:
            # Ищем существующую запись
            status_entry = UserEventStatus.query.filter_by(
                user_id=user.id,
                event_id=event_id
            ).first()

            if status_entry:
                # Обновляем существующую запись
                status_entry.status = status
            else:
                # Создаем новую запись
                new_status = UserEventStatus(
                    user_id=user.id,
                    event_id=event_id,
                    status=status
                )
                db.session.add(new_status)

        db.session.commit()
        return jsonify({
            "success": True,
            "event_id": event_id,
            "user_id": user.id,
            "status": status if status != 'none' else None
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Database error",
            "details": str(e)
        }), 500

@app.route('/get_event_status')
def get_event_status():
    # Проверка авторизации пользователя
    if 'username' not in session:
        return jsonify({"status": None}), 200

    # Получение текущего пользователя
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"status": None}), 200

    # Валидация параметра event_id
    event_id = request.args.get('event_id', type=int)
    if not event_id:
        return jsonify({"error": "Missing or invalid event_id"}), 400

    # Проверка существования события
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Поиск статуса пользователя для события
    status_entry = UserEventStatus.query.filter_by(
        user_id=user.id,
        event_id=event_id
    ).first()

    return jsonify({
        "status": status_entry.status if status_entry else None
    })

@app.route('/get_all_events_status')
def get_all_events_status():
    if 'username' not in session:
        return jsonify({})

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({})

    statuses = UserEventStatus.query.filter_by(user_id=user.id).all()
    return jsonify({
        int(status.event_id): status.status for status in statuses
    })


# Страница мероприятий организатора
@app.route('/my_events')
def my_events():
    if 'username' not in session or session['role'] != 'organizer':
        return redirect(url_for('home'))
    
    search_query = request.args.get('search', '').strip()
    selected_tag = request.args.get('tag', '').strip()
    
    user = User.query.filter_by(username=session['username']).first()
    
    # Базовый запрос
    query = Event.query.filter_by(organizer_id=user.id, is_active=True)
    
    if search_query:
        query = query.filter(
            (Event.title.ilike(f'%{search_query}%')) | 
            (Event.description.ilike(f'%{search_query}%')) | 
            (Event.event_type.ilike(f'%{search_query}%')) | 
            (Event.location_name.ilike(f'%{search_query}%')) |
            (Event.location_address.ilike(f'%{search_query}%')) |
            (Event.tags.any(Tag.name.ilike(f'%{search_query}%')))
        )
    
    if selected_tag:
        tag = Tag.query.filter_by(name=selected_tag).first()
        if tag:
            query = query.join(Event.tags).filter(Tag.id == tag.id)
    
    events = query.all()
    tags = Tag.query.all()
    
    return render_template('my_events.html', events=events, tags=tags)

# Удаление мероприятия
@app.route('/delete_event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    event = Event.query.get_or_404(event_id)
    user = User.query.filter_by(username=session['username']).first()
    
    if event.organizer_id != user.id and session['role'] not in ['moderator', 'admin']:
        return jsonify({"error": "Forbidden"}), 403
    
    # Мягкое удаление (изменение статуса is_active)
    event.is_active = False
    db.session.commit()
    
    return jsonify({"success": True})

# Редактирование мероприятия
@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'username' not in session:
        return redirect(url_for('home'))
    
    event = Event.query.get_or_404(event_id)
    user = User.query.filter_by(username=session['username']).first()
    
    if event.organizer_id != user.id and session.get('role') not in ['moderator', 'admin']:
        return redirect(url_for('home'))
    
    tags = Tag.query.all()
    
    if request.method == 'POST':
        try:
            event.title = request.form.get('title')
            event.description = request.form.get('description')
            event.format = request.form.get('format')
            event.location_name = request.form.get('location_name', '')
            event.location_address = request.form.get('location_address', '')
            event.online_info = request.form.get('online_info', '')
            event.date_time = datetime.strptime(request.form.get('date_time'), '%Y-%m-%dT%H:%M')
            event.duration = int(request.form.get('duration'))
            event.event_type = request.form.get('event_type')
            event.is_private = request.form.get('is_private') == 'true'
            event.password = request.form.get('password') if event.is_private else None
            
            # Обработка координат только для офлайн мероприятий
            if event.format == 'offline':
                lat_str = request.form.get('lat', '0')
                lng_str = request.form.get('lng', '0')
                event.lat = float(lat_str) if lat_str else None
                event.lng = float(lng_str) if lng_str else None
            else:
                event.lat = None
                event.lng = None
            
            # Обновление тегов
            EventTag.query.filter_by(event_id=event.id).delete()
            selected_tags = request.form.get('tags', '').split(',')
            selected_tags = [tag_id for tag_id in selected_tags if tag_id]
            for tag_id in selected_tags:
                tag = Tag.query.get(tag_id)
                if tag:
                    db.session.add(EventTag(event_id=event.id, tag_id=tag.id))
            
            # Обновление изображения
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    event.image_url = f'uploads/{filename}'
            
            db.session.commit()
            return redirect(url_for('my_events'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'error')
            app.logger.error(f"Edit event error: {str(e)}")
            return redirect(url_for('edit_event', event_id=event_id))
    
    # Заполняем форму текущими данными
    selected_tag_ids = [tag.id for tag in event.tags]
    return render_template('edit_event.html', event=event, tags=tags, selected_tag_ids=selected_tag_ids)



# Проверка пароля к приватному ивенту
@app.route('/check_event_password/<int:event_id>', methods=['POST'])
def check_event_password(event_id):
    data = request.get_json()
    event = Event.query.get_or_404(event_id)
    
    if not event.is_private:
        return jsonify({"success": True})
    
    if not event.password or event.password == data.get('password'):
        return jsonify({"success": True})
    
    return jsonify({"success": False})



# Страница профиля
@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('home'))
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # Получаем статусы мероприятий пользователя
    statuses = user.event_statuses.all()

    # Разделяем мероприятия по статусам
    planned_events = []
    attended_events = []
    
    for status in statuses:
        event = Event.query.get(status.event_id)
        if event and event.is_active:
            if status.status == 'planned':
                planned_events.append(event)
            elif status.status == 'attended':
                attended_events.append(event)

    role = ROLE_TRANSLATIONS.get(
        user.role.lower(), 
        user.role.capitalize()  # Для неизвестных ролей
    )
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template('profile.html',
                         user=user,
                         username=user.username,
                         email=user.email,
                         role=role,
                         attended_events=attended_events,
                         planned_events=planned_events,
                         description = user.description,
                         is_2fa_enabled = user.is_2fa_enabled,
                         all_tags=all_tags)


@app.route('/update_description', methods=['POST'])
def update_description():
    # Проверка авторизации
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Получение пользователя из БД
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    try:
        # Парсинг JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Обновление описания
        user.description = data.get('description', user.description)
        db.session.commit()
        
        return jsonify({"success": True, "new_description": user.description})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Маршрут поиска пользователей
@app.route('/search_users')
def search_users():
    if 'username' not in session:
        return jsonify([])
    
    search_query = request.args.get('q', '').strip()
    current_user_id = User.query.filter_by(username=session['username']).first().id
    
    users = User.query.filter(
        User.username.ilike(f'%{search_query}%'),
        User.id != current_user_id
    ).limit(10).all()
    
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'avatar_url': user.avatar_url 
    } for user in users])

# Маршрут добавления в друзья
@app.route('/add_friend', methods=['POST'])
def add_friend():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    friend_id = data.get('friend_id')
    
    user = User.query.filter_by(username=session['username']).first()
    
    try:
        existing = Friendship.query.filter_by(
            user_id=user.id,
            friend_id=friend_id
        ).first()
        
        if existing:
            return jsonify({"error": "Запрос уже отправлен"}), 400
            
        friendship = Friendship(
            user_id=user.id,
            friend_id=friend_id,
            status='pending'
        )
        db.session.add(friendship)
        db.session.commit()
        
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    

@app.route('/friend_requests')
def get_friend_requests():
    if 'username' not in session:
        return jsonify([])
    
    user = User.query.filter_by(username=session['username']).first()
    requests = Friendship.query.filter_by(friend_id=user.id, status='pending').all()
    
    return jsonify([{
        "id": req.id,
        "sender": req.sender.username,
        "sender_avatar": req.sender.avatar_url,
        "created_at": req.created_at.strftime("%d.%m.%Y %H:%M")
    } for req in requests])

# Ответ на запрос
@app.route('/respond_friend_request', methods=['POST'])
def respond_friend_request():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    request_id = data.get('request_id')
    action = data.get('action')  # 'accept' или 'reject'

    # Проверка прав
    user = User.query.filter_by(username=session['username']).first()
    friend_request = Friendship.query.get(request_id)

    if not friend_request or friend_request.friend_id != user.id:
        return jsonify({"error": "Forbidden"}), 403

    # Обновление статуса
    if action == 'accept':
        friend_request.status = 'accepted'
    elif action == 'reject':
        friend_request.status = 'rejected'
    else:
        return jsonify({"error": "Invalid action"}), 400

    db.session.commit()
    return jsonify({"success": True})

@app.route('/profile/<username>')
def user_profile(username):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    viewer = User.query.filter_by(username=session['username']).first()
    user = User.query.filter_by(username=username).first_or_404()
    
    is_friend = user in viewer.friends
    is_own_profile = (viewer.id == user.id)
    show_events = (not user.is_private) or is_friend or is_own_profile

    planned_events = []
    attended_events = []
    
    if show_events:
        # Получаем последний статус для каждого мероприятия
        subquery = db.session.query(
            UserEventStatus.event_id,
            func.max(UserEventStatus.created_at).label('max_date')
        ).filter_by(user_id=user.id).group_by(UserEventStatus.event_id).subquery()

        statuses = db.session.query(UserEventStatus).join(
            subquery,
            (UserEventStatus.event_id == subquery.c.event_id) &
            (UserEventStatus.created_at == subquery.c.max_date)
        ).all()

        for status in statuses:
            event = Event.query.get(status.event_id)
            if event and event.is_active:
                if status.status == 'planned':
                    planned_events.append(event)
                elif status.status == 'attended':
                    attended_events.append(event)

    role_display = ROLE_TRANSLATIONS.get(user.role.lower(), user.role.capitalize())
    
    return render_template('user_profile.html',
                         user=user,
                         is_friend=is_friend,
                         username=user.username,
                         email=user.email,
                         role_display=role_display,
                         description=user.description,
                         show_events=show_events,
                         is_own_profile=is_own_profile,
                         planned_events=planned_events,
                         attended_events=attended_events)

@app.route('/update_privacy', methods=['POST'])
def update_privacy():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    try:
        data = request.get_json()
        user.is_private = data.get('is_private', False)
        db.session.commit()
        return jsonify({"success": True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Получение списка друзей
@app.route('/get_friends')
def get_friends():
    if 'username' not in session:
        return jsonify([])
    
    user = User.query.filter_by(username=session['username']).first()
    return jsonify([{
        'id': friend.id,
        'username': friend.username
    } for friend in user.friends])

# Отправка рекомендации
@app.route('/send_recommendation', methods=['POST'])
def send_recommendation():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    user = User.query.filter_by(username=session['username']).first()
    
    try:
        for friend_id in data['friend_ids']:
            recommendation = Recommendation(
                sender_id=user.id,
                receiver_id=friend_id,
                event_id=data['event_id'] 
            )
            db.session.add(recommendation)
        
        db.session.commit()
        return jsonify({"success": True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/invitations')
def invitations():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    invites = Recommendation.query.options(
        db.joinedload(Recommendation.event)
        .joinedload(Event.tags)
    ).filter_by(receiver_id=user.id).all()
    
    return render_template('invitations.html', invitations=invites)


@app.route('/respond_invitation', methods=['POST'])
def respond_invitation():
    data = request.get_json()
    recommendation = Recommendation.query.get_or_404(data['recommendation_id'])
    user = User.query.filter_by(username=session['username']).first()

    try:
        if data['action'] == 'accept':
            # Обновляем статус мероприятия
            status = UserEventStatus.query.filter_by(
                user_id=user.id,
                event_id=recommendation.event_id
            ).first()

            if not status:
                status = UserEventStatus(
                    user_id=user.id,
                    event_id=recommendation.event_id,
                    status='planned'
                )
                db.session.add(status)
            else:
                status.status = 'planned'

            # Помечаем рекомендацию как обработанную
            db.session.delete(recommendation)

        elif data['action'] == 'decline':
            db.session.delete(recommendation)

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/friends')
def friends():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    return render_template('friends.html', user=user)

@app.route('/update_occupation', methods=['POST'])
def update_occupation():
    if 'username' not in session or session['role'] != 'organizer':
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    user = User.query.filter_by(username=session['username']).first()
    
    try:
        user.occupation = data.get('occupation', '')[:100]  # Ограничение длины
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@app.route('/all_events')
def all_events():
    if 'username' not in session or session.get('role') not in ['moderator', 'admin']:
        return redirect(url_for('home'))
    
    search_query = request.args.get('search', '').strip()
    selected_tag = request.args.get('tag', '').strip()
    
    query = Event.query.filter_by(is_active=True)
    
    # Фильтр по поиску (как в index)
    if search_query:
        query = query.filter(
            (Event.title.ilike(f'%{search_query}%')) | 
            (Event.description.ilike(f'%{search_query}%')) | 
            (Event.event_type.ilike(f'%{search_query}%')) | 
            (Event.location_name.ilike(f'%{search_query}%')) |
            (Event.location_address.ilike(f'%{search_query}%')) |
            (Event.tags.any(Tag.name.ilike(f'%{search_query}%')))
        )
    
    # Фильтр по тегу
    if selected_tag:
        tag = Tag.query.filter_by(name=selected_tag).first()
        if tag:
            query = query.join(Event.tags).filter(Tag.id == tag.id)
    
    events = query.all()
    tags = Tag.query.all()
    
    return render_template('all_events.html', 
                         events=events, 
                         tags=tags,
                         search_query=search_query,
                         selected_tag=selected_tag)

@app.route('/all_organizers')
def all_organizers():
    if 'username' not in session or session.get('role') not in ['moderator', 'admin']:
        return redirect(url_for('home'))
    
    search_query = request.args.get('search', '').strip()
    
    # Получаем всех организаторов с фильтром по поиску
    organizers_query = User.query.filter_by(role='organizer')
    if search_query:
        organizers_query = organizers_query.filter(User.username.ilike(f'%{search_query}%'))
    
    organizers = organizers_query.all()
    return render_template('all_organizers.html', organizers=organizers, search_query=search_query)

@app.route('/edit_organizer/<int:organizer_id>', methods=['GET', 'POST'])
def edit_organizer(organizer_id):
    if 'username' not in session or session.get('role') not in ['moderator', 'admin']:
        return redirect(url_for('home'))
    
    organizer = User.query.get_or_404(organizer_id)
    
    if request.method == 'POST':
        original_is_blocked = organizer.is_blocked
        action = request.form.get('action')
        
        if action == 'block':
            # Проверка прав
            if session['role'] == 'moderator' and organizer.role in ['moderator', 'admin']:
                abort(403)
                
            duration = request.form.get('duration')
            reason = request.form.get('reason')
            
            if duration == 'permanent':
                organizer.blocked_until = None
            else:
                organizer.blocked_until = datetime.utcnow() + timedelta(days=int(duration))
            
            organizer.is_blocked = True
            organizer.block_reason = reason
            if not original_is_blocked:
                duration_text = "Навсегда" if duration == 'permanent' else f"{duration} дней"
                send_account_status_email(
                    organizer,
                    is_blocked=True,
                    block_duration=duration_text,
                    reason=reason
                )
        
        elif action == 'unblock':
            organizer.is_blocked = False
            organizer.blocked_until = None
            organizer.block_reason = None
            if original_is_blocked:
                send_account_status_email(organizer, is_blocked=False)
        
        # Обновление остальных данных
        organizer.username = request.form.get('username', organizer.username)
        organizer.occupation = request.form.get('occupation', organizer.occupation)
        organizer.description = request.form.get('description', organizer.description)
        
        db.session.commit()
        return redirect(url_for('all_organizers'))
    
    return render_template('edit_organizer.html', organizer=organizer)

@app.route('/all_users')
def all_users():
    # Проверка авторизации
    if 'username' not in session or session['role'] not in ['moderator', 'admin']:
        return redirect(url_for('home'))
    
    search_query = request.args.get('search', '').strip()
    
    # Базовый запрос
    users_query = User.query
    
    # Фильтрация в зависимости от роли
    if session['role'] == 'moderator':
        # Модератор видит всех, кроме других модераторов и админов
        users_query = users_query.filter(User.role.notin_(['moderator', 'admin']))
    elif session['role'] == 'admin':
        # Админ видит всех, кроме других админов
        users_query = users_query.filter(User.role != 'admin')
    
    # Применяем поиск, если есть запрос
    if search_query:
        users_query = users_query.filter(User.username.ilike(f'%{search_query}%'))
    
    users = users_query.all()
    return render_template('all_users.html', users=users, search_query=search_query)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    current_user = User.query.filter_by(username=session['username']).first()
    target_user = User.query.get_or_404(user_id)
    
    # Проверка прав
    if session['role'] == 'moderator' and target_user.role in ['admin', 'moderator']:
        abort(403)
    if session['role'] == 'admin' and target_user.role == 'admin':
        abort(403)
    
    if request.method == 'POST':
        # Обработка блокировки/разблокировки
        original_is_blocked = target_user.is_blocked
        action = request.form.get('action')
        
        if action == 'block':
            # Проверка прав на блокировку
            if current_user.role == 'moderator' and target_user.role in ['moderator', 'admin']:
                abort(403)
                
            duration = request.form.get('duration')
            reason = request.form.get('reason')
            
            if duration == 'permanent':
                target_user.blocked_until = None
            else:
                target_user.blocked_until = datetime.utcnow() + timedelta(days=int(duration))
            
            target_user.is_blocked = True
            target_user.block_reason = reason

            if not original_is_blocked:
                duration_text = "Навсегда" if duration == 'permanent' else f"{duration} дней"
                send_account_status_email(
                    target_user,
                    is_blocked=True,
                    block_duration=duration_text,
                    reason=reason
                )
        
        elif action == 'unblock':
            target_user.is_blocked = False
            target_user.blocked_until = None
            target_user.block_reason = None
            if original_is_blocked:
                send_account_status_email(target_user, is_blocked=False)
        
        # Обновление остальных данных
        target_user.username = request.form.get('username', target_user.username)
        target_user.description = request.form.get('description', target_user.description)
        
        db.session.commit()
        return redirect(url_for('all_users'))
    
    return render_template('edit_user.html', user=target_user)


@app.route('/update_avatar', methods=['POST'])
def update_avatar():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = User.query.filter_by(username=session['username']).first()
    if 'avatar' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['avatar']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        user.avatar_url = f'uploads/avatars/{filename}'
        db.session.commit()
        return jsonify({"success": True, "avatar_url": user.avatar_url})
    
    return jsonify({"error": "Invalid file"}), 400

@app.route('/validation')
def validation():
    if 'username' not in session or session['role'] not in ['moderator', 'admin']:
        return redirect(url_for('home'))
    
    # Для модераторов показываем только организаторов
    if session['role'] == 'moderator':
        organizers = User.query.filter_by(validation='organizer').all()
        return render_template('validation.html', organizers=organizers, moderators=[])
    
    # Для админов показываем и организаторов, и модераторов
    organizers = User.query.filter_by(validation='organizer').all()
    moderators = User.query.filter_by(validation='moderator').all()
    return render_template('validation.html', organizers=organizers, moderators=moderators)

@app.route('/validate_user', methods=['POST'])
def validate_user():
    if 'username' not in session or session['role'] not in ['moderator', 'admin']:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    user_id = data.get('user_id')
    role = data.get('role')
    accept = data.get('accept')
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Проверяем права
    if session['role'] == 'moderator' and role != 'organizer':
        return jsonify({"error": "Forbidden"}), 403
    
    if accept:
        user.role = role
    user.validation = None
    db.session.commit()
    
    return jsonify({"success": True})

@app.context_processor
def inject_validation_counts():
    if 'username' in session and session.get('role') in ['moderator', 'admin']:
        pending_organizers = User.query.filter_by(validation='organizer').count()
        if session['role'] == 'admin':
            pending_moderators = User.query.filter_by(validation='moderator').count()
        else:
            pending_moderators = 0
        return {'pending_organizers': pending_organizers, 'pending_moderators': pending_moderators}
    return {}

@app.context_processor
def inject_friend_requests_count():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            pending_requests = Friendship.query.filter_by(
                friend_id=user.id, 
                status='pending'
            ).count()
            return {'pending_friend_requests': pending_requests}
    return {}

@app.context_processor
def inject_user():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        return {'current_user': user}
    return {}

# Сброс пароля
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            try:
                # Генерация токена с отдельной солью
                token = serializer.dumps(
                    email, 
                    salt=app.config['SECURITY_PASSWORD_RESET_SALT']
                )
                reset_url = url_for('reset_password', token=token, _external=True)
                
                # Отправка письма
                msg = Message(
                    subject="Сброс пароля для EventHub",
                    recipients=[user.email],
                    html=render_template(
                        'reset_password_email.html',
                        reset_url=reset_url
                    )
                )
                mail.send(msg)
            except Exception as e:
                app.logger.error(f"Ошибка отправки письма: {str(e)}")
        
        # Всегда показываем одинаковое сообщение для безопасности
        return render_template('reset_password_request.html',
                             message="Если аккаунт с таким email существует, инструкции отправлены на почту")
    
    return render_template('reset_password_request.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_RESET_SALT'],
            max_age=3600  # 1 час
        )
    except:
        return render_template('reset_password_request.html', 
                             error="Ссылка для сброса пароля недействительна или срок её действия истек")
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        
        # Обновляем пароль
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        
        # Очищаем сессии и перенаправляем на вход
        session.clear()
        return redirect(url_for('login', _anchor='password-reset-success'))
    
    return render_template('reset_password.html')

# Генерация секрета для 2FA (активация в профиле)
@app.route('/generate-2fa-secret', methods=['POST'])
def generate_2fa_secret():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = User.query.filter_by(username=session['username']).first()
    secret = random_base32()
    user.totp_secret = secret
    db.session.commit()
    
    # Генерация QR-кода
    totp_uri = TOTP(secret).provisioning_uri(user.email, issuer_name="EventHub")
    img = qrcode.make(totp_uri)
    buffered = BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return jsonify({
        "secret": secret,
        "qrcode": f"data:image/png;base64,{img_str}"
    })

# Подтверждение активации 2FA (в профиле)
@app.route('/verify-2fa-setup', methods=['POST'])
def verify_2fa_setup():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = User.query.filter_by(username=session['username']).first()
    code = request.json.get('code')
    
    if TOTP(user.totp_secret).verify(code):
        user.is_2fa_enabled = True
        db.session.commit()
        return jsonify({"success": True})
    
    return jsonify({"error": "Invalid code"}), 400

# Отключение 2FA
@app.route('/disable-2fa', methods=['POST'])
def disable_2fa():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = User.query.filter_by(username=session['username']).first()
    user.totp_secret = None
    user.is_2fa_enabled = False
    db.session.commit()
    return jsonify({"success": True})

# Обработка 2FA при входе
@app.route("/verify-2fa-login", methods=["GET", "POST"])
def verify_2fa_login():
    try:
        # GET: Показать страницу ввода кода
        if request.method == "GET":
            if "pending_2fa_user" not in session:
                return redirect(url_for("login"))
            return render_template("verify_2fa.html")

        # POST: Проверить код
        if "pending_2fa_user" not in session:
            return jsonify({"error": "Сессия устарела"}), 401

        username = session["pending_2fa_user"]
        user = User.query.filter_by(username=username).first()
        
        if not user:
            app.logger.error(f"User {username} not found in database")
            return jsonify({"error": "Ошибка аутентификации"}), 400

        # Создаем запись TwoFAAttempt при первой попытке
        attempt = TwoFAAttempt.query.filter_by(user_id=user.id).first()
        if not attempt:
            attempt = TwoFAAttempt(user_id=user.id)
            db.session.add(attempt)
            db.session.commit()  # Фиксируем сразу

        code = request.json.get("code", "")
        
        # Проверка блокировки
        if attempt.blocked_until and attempt.blocked_until > datetime.utcnow():
            return jsonify({
                "error": f"Вход заблокирован до {(attempt.blocked_until + timedelta(hours=3)).strftime('%H:%M')}"
            }), 429

        # Проверка кода
        if not TOTP(user.totp_secret).verify(code, valid_window=2):
            attempt.attempts += 1
            attempt.last_attempt = datetime.utcnow()
            
            if attempt.attempts >= 5:
                attempt.blocked_until = datetime.utcnow() + timedelta(hours=1)
            
            db.session.commit()
            remaining = 5 - attempt.attempts
            if remaining == 0:
                return jsonify({
                    "error": f"Вход заблокирован до {(attempt.blocked_until + timedelta(hours=3)).strftime('%H:%M')}"
                }), 429
            return jsonify({
                "error": f"Неверный код. Осталось попыток: {remaining}"
            }), 400

        # Успешная аутентификация
        db.session.delete(attempt)
        db.session.commit()
        
        session.pop("pending_2fa_user", None)
        session["username"] = user.username
        session["role"] = user.role
        
        return jsonify({"success": True, "redirect": url_for("home")})

    except Exception as e:
        app.logger.error(f"2FA Error: {str(e)}", exc_info=True)
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

@app.route('/toggle_tag', methods=['POST'])
def toggle_tag():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = User.query.filter_by(username=session['username']).first()
    tag_id = request.json.get('tag_id')
    
    try:
        tag = Tag.query.get_or_404(tag_id)
        
        # Проверяем текущий статус тега
        if tag in user.favorite_tags:
            user.favorite_tags.remove(tag)
            action = 'removed'
        else:
            user.favorite_tags.append(tag)
            action = 'added'
        
        db.session.commit()
        return jsonify({
            "success": True,
            "action": action,
            "tag_id": tag_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@app.route('/rate_event', methods=['POST'])
def rate_event():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        data = request.get_json()
        event_id = data.get('event_id')
        rating = data.get('rating')

        # Валидация
        if not event_id or rating is None:
            return jsonify({'error': 'Не указаны event_id или rating'}), 400

        rating = int(rating)
        if rating != 0 and not (1 <= rating <= 5):
            return jsonify({'error': 'Оценка должна быть от 1 до 5'}), 400

        user = User.query.filter_by(username=session['username']).first()
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        event = Event.query.get(event_id)
        if not event:
            return jsonify({'error': 'Мероприятие не найдено'}), 404

        existing_rating = Rating.query.filter_by(
            user_id=user.id,
            event_id=event_id
        ).first()

        new_rating = 0

        if existing_rating:
            if existing_rating.rating == rating:
                # Сброс оценки при повторном нажатии
                db.session.delete(existing_rating)
                new_rating = 0
            else:
                # Обновление оценки
                existing_rating.rating = rating
                new_rating = rating
        else:
            if rating != 0:
                # Новая оценка
                new_rating_obj = Rating(
                    user_id=user.id,
                    event_id=event_id,
                    rating=rating
                )
                db.session.add(new_rating_obj)
                new_rating = rating

        db.session.commit()
        event = Event.query.get(event_id)  # Обновляем данные мероприятия

        return jsonify({
            'success': True,
            'average': event.average_rating,
            'count': event.ratings_count,
            'userRating': new_rating
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

@app.route('/get_ratings/<int:event_id>')
def get_ratings(event_id):
    event = Event.query.get_or_404(event_id)
    user_rating = 0
    
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            rating = Rating.query.filter_by(user_id=user.id, event_id=event_id).first()
            user_rating = rating.rating if rating else 0

    return jsonify({
        'average': event.average_rating if event.ratings_count > 0 else 0.0,
        'count': event.ratings_count,
        'userRating': user_rating
    })

@app.route('/track_view', methods=['POST'])
def track_view():
    try:
        if 'username' not in session:
            return jsonify({'success': True, 'message': 'Просмотр не записан (гость)'})

        data = request.get_json()
        event_id = data.get('event_id')
        
        if not event_id:
            return jsonify({'success': False, 'error': 'Не указан event_id'}), 400

        user = User.query.filter_by(username=session['username']).first()
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        event = Event.query.get(event_id)
        if not event:
            return jsonify({'success': False, 'error': 'Мероприятие не найдено'}), 404

        # Проверка временного интервала
        view = EventView.query.filter_by(
            user_id=user.id, 
            event_id=event_id
        ).first()

        if view:
            if (datetime.utcnow() - view.last_viewed_at).total_seconds() < 300:
                return jsonify({'success': True, 'message': 'Просмотр не обновлен'})
            
            view.last_viewed_at = datetime.utcnow()
        else:
            view = EventView(user_id=user.id, event_id=event_id)
            db.session.add(view)

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Track view error: {str(e)}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/get_event_stats/<int:event_id>')
def get_event_stats(event_id):
    try:
        # Проверка авторизации
        if 'username' not in session:
            return jsonify({"error": "Unauthorized"}), 401
            
        event = Event.query.get_or_404(event_id)
        user = User.query.filter_by(username=session['username']).first()
        
        # Проверка прав доступа
        if event.organizer_id != user.id and user.role not in ['moderator', 'admin']:
            return jsonify({"error": "Forbidden"}), 403
        

        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        views_data = db.session.query(
            func.date(EventView.last_viewed_at).label('date'),
            func.count().label('views')
        ).filter(
            EventView.event_id == event_id
        ).group_by('date').all()
        
        # Форматируем в словарь {дата: количество}
        views_by_date = {str(row.date): row.views for row in views_data}

        stats = {
            'views_data': views_by_date,
            'views': EventView.query.filter_by(event_id=event_id).count(),
            'planned': UserEventStatus.query.filter_by(event_id=event_id, status='planned').count(),
            'attended': UserEventStatus.query.filter_by(event_id=event_id, status='attended').count(),
            'recommendations': Recommendation.query.filter_by(event_id=event_id).count(),
            'average_rating': event.average_rating,
            'ratings_count': event.ratings_count
        }

        return jsonify(stats)
    
    except Exception as e:
        app.logger.error(f"Stats error: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/subscriptions')
def subscriptions():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    return render_template('subscriptions.html', user=user)

@app.route('/toggle_subscription', methods=['POST'])
def toggle_subscription():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    organizer_id = data.get('organizer_id')
    
    user = User.query.filter_by(username=session['username']).first()
    organizer = User.query.get(organizer_id)
    
    if not organizer or organizer.role != 'organizer':
        return jsonify({"error": "Organizer not found"}), 404
    
    try:
        # Проверяем текущую подписку
        subscription = UserOrganizer.query.filter_by(
            user_id=user.id,
            organizer_id=organizer.id
        ).first()
        
        if subscription:
            # Отписываемся
            db.session.delete(subscription)
            action = 'unsubscribed'
        else:
            # Подписываемся
            new_sub = UserOrganizer(user_id=user.id, organizer_id=organizer.id)
            db.session.add(new_sub)
            action = 'subscribed'
        
        db.session.commit()
        return jsonify({
            "success": True,
            "action": action,
            "followers_count": organizer.followers.count()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/search_organizers')
def search_organizers():
    if 'username' not in session:
        return jsonify([])
    
    search_query = request.args.get('q', '').strip()
    current_user_id = User.query.filter_by(username=session['username']).first().id
    
    organizers = User.query.filter(
        User.username.ilike(f'%{search_query}%'),
        User.role == 'organizer',
        User.id != current_user_id
    ).limit(10).all()
    
    return jsonify([{
        'id': org.id,
        'username': org.username,
        'avatar_url': org.avatar_url 
    } for org in organizers])

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    friend_id = data.get('friend_id')
    
    user = User.query.filter_by(username=session['username']).first()
    
    try:
        # Удаляем дружбу в обоих направлениях
        Friendship.query.filter(
            ((Friendship.user_id == user.id) & (Friendship.friend_id == friend_id)) |
            ((Friendship.user_id == friend_id) & (Friendship.friend_id == user.id))
        ).delete()
        
        db.session.commit()
        return jsonify({"success": True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/add_comment', methods=['POST'])
def add_comment():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация. Пожалуйста, войдите в систему.'}), 401
        
    data = request.json
    user = User.query.filter_by(username=session['username']).first()
    
    # Проверка ограничения (кроме админов и модераторов)
    if user.role not in ['admin', 'moderator']:
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        recent_comments = Comment.query.filter(
            Comment.user_id == user.id,
            Comment.created_at >= ten_minutes_ago
        ).count()
        
        if recent_comments >= 10:
            return jsonify({
                'error': 'Превышен лимит: не более 10 комментариев за 10 минут'
            }), 429

    new_comment = Comment(
        user_id=user.id,
        event_id=data['event_id'],
        text=data['text'][:500]  # Ограничение длины
    )
    db.session.add(new_comment)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/delete_comment/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
        
    comment = Comment.query.get_or_404(comment_id)
    user = User.query.filter_by(username=session['username']).first()
    
    # Проверка прав: автор или админ/модератор
    if not (comment.user_id == user.id or user.role in ['admin', 'moderator']):
        return jsonify({'error': 'Нет прав на удаление'}), 403
    
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/get_comments')
def get_comments():
    event_id = request.args.get('event_id')
    current_user = User.query.filter_by(username=session.get('username')).first()
    
    comments = Comment.query.options(joinedload(Comment.user)).filter_by(event_id=event_id).all()
    
    return jsonify([{
        'id': c.id,
        'text': c.text,
        'created_at': c.created_at.isoformat(),
        'username': c.user.username,
         'avatar': f"/static/{c.user.avatar_url}" if c.user.avatar_url 
                 else '/static/images/default_avatar.png',
        'can_delete': (
            (current_user and c.user_id == current_user.id) or 
            (current_user and current_user.role in ['admin', 'moderator'])
        )
    } for c in comments])

@app.route('/check_auth')
def check_auth():
    return jsonify({'authenticated': 'username' in session}), 200

@app.route('/get_event_data')
def get_event_data():
    event_id = request.args.get('event_id')
    event = Event.query.get_or_404(event_id)
    user = User.query.filter_by(username=session.get('username')).first()
    
    is_new = False
    if user:
        is_new = SubscriptionNotification.query.filter_by(
            user_id=user.id,
            event_id=event.id,
            is_read=False
        ).first() is not None
    return jsonify({
        'eventId': event.id,
        'title': event.title,
        'description': event.description,
        'locationName': event.location_name,
        'tags': ', '.join([tag.name for tag in event.tags]),
        'eventType': event.event_type,
        'locationAddress': event.location_address,
        'lat': event.lat,
        'lng': event.lng,
        'imageUrl': event.image_url,
        'isPrivate': event.is_private,
        'format': event.format,
        'onlineInfo': event.online_info,
        'dateTime': event.date_time.isoformat(),
        'duration': event.duration,
        'organizerUsername': event.organizer.username,
        'personalities': event.personalities or []
    })

@app.route('/event/<int:event_id>')
def share_event(event_id):
    event = Event.query.get_or_404(event_id)
    return redirect(url_for('home', event_id=event_id))

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def send_account_status_email(user, is_blocked, block_duration=None, reason=None):
    try:
        subject = "Блокировка аккаунта" if is_blocked else "Разблокировка аккаунта"
        msg = Message(
            subject=f"EventHub: {subject}",
            recipients=[user.email],
            html=render_template(
                'account_status_email.html',
                is_blocked=is_blocked,
                block_duration=block_duration,
                reason=reason
            )
        )
        mail.send(msg)
    except Exception as e:
        app.logger.error(f"Ошибка отправки email: {str(e)}")

@app.route('/get_unread_notifications_count')
def get_unread_notifications_count():
    if 'username' not in session:
        return jsonify({"count": 0})
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"count": 0})
    
    count = SubscriptionNotification.query.filter_by(
        user_id=user.id,
        is_read=False
    ).count()
    
    return jsonify({"count": count})

@app.route('/mark_notifications_as_read', methods=['POST'])
def mark_notifications_as_read():
    if 'username' not in session:
        return jsonify({"success": False})
    
    data = request.get_json()
    organizer_id = data.get('organizer_id')
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"success": False})
    
    # Помечаем все уведомления от этого организатора как прочитанные
    SubscriptionNotification.query.filter_by(
        user_id=user.id,
        organizer_id=organizer_id,
        is_read=False
    ).update({"is_read": True})
    
    db.session.commit()
    return jsonify({"success": True})

@app.route('/get_organizer_unread_count/<int:organizer_id>')
def get_organizer_unread_count(organizer_id):
    if 'username' not in session:
        return jsonify({"count": 0})
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"count": 0})
    
    count = SubscriptionNotification.query.filter_by(
        user_id=user.id,
        organizer_id=organizer_id,
        is_read=False
    ).count()
    
    return jsonify({"count": count})

@app.route('/mark_event_as_read/<int:event_id>', methods=['POST'])
def mark_event_as_read(event_id):
    if 'username' not in session:
        return jsonify({"success": False})
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"success": False})
    
    # Помечаем уведомление о конкретном мероприятии как прочитанное
    SubscriptionNotification.query.filter_by(
        user_id=user.id,
        event_id=event_id,
        is_read=False
    ).update({"is_read": True})
    
    db.session.commit()
    return jsonify({"success": True})

@app.route('/delete_tag/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    if 'username' not in session or session['role'] not in ['moderator', 'admin']:
        return jsonify({"error": "Unauthorized"}), 401
    
    tag = Tag.query.get_or_404(tag_id)
    
    try:
        # Удаляем связи тега с мероприятиями
        EventTag.query.filter_by(tag_id=tag.id).delete()
        # Удаляем связи тега с пользователями (из избранного)
        UserTag.query.filter_by(tag_id=tag.id).delete()
        # Удаляем сам тег
        db.session.delete(tag)
        db.session.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)