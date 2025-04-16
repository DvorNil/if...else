from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import folium
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

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
Session(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='participant')
    favorite_organizers = db.relationship(
        'User', 
        secondary='user_organizer',
        primaryjoin='UserOrganizer.user_id == User.id',
        secondaryjoin='UserOrganizer.organizer_id == User.id',
        backref=db.backref('followers', lazy='dynamic')
    )
    
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
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmed_on = db.Column(db.DateTime, nullable=True)

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
    format = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(200))
    date_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    event_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    organizer = db.relationship('User', backref='events')
    tags = db.relationship('Tag', secondary='event_tag', backref='events')

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
            email_confirmed=True
        )
        db.session.add(user2)
    
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
                "location": "ул. Ленина, 10, Минск",
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
                "location": "ул. Советская, 5, Гродно",
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
                location=event_data['location'],
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

# Главная страница
@app.route('/', methods=['GET'])
def home():
    search_query = request.args.get('search', '').strip()
    selected_tag = request.args.get('tag', '').strip()
    
    query = Event.query.filter_by(is_active=True)
    
    if search_query:
        # Ищем по основным полям ИЛИ по тегам
        query = query.filter(
            (Event.title.ilike(f'%{search_query}%')) | 
            (Event.description.ilike(f'%{search_query}%')) | 
            (Event.event_type.ilike(f'%{search_query}%')) | 
            (Event.location.ilike(f'%{search_query}%')) |
            (Event.tags.any(Tag.name.ilike(f'%{search_query}%')))
        )
    
    if selected_tag:
        tag = Tag.query.filter_by(name=selected_tag).first()
        if tag:
            query = query.join(Event.tags).filter(Tag.id == tag.id)
    
    events = query.all()
    tags = Tag.query.all()
    
    return render_template('index.html', 
                         posts=events, 
                         tags=tags, 
                         search_query=search_query,
                         selected_tag=selected_tag)

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            if not user.email_confirmed:
                return render_template('login.html', error="Пожалуйста, подтвердите ваш email перед входом.")
            
            session['username'] = username
            session['role'] = user.role
            return redirect(url_for('home'))
        
        return render_template('login.html', error="Неверный логин или пароль")
    return render_template('login.html', error=None)

# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if role not in ['participant', 'organizer']:
            role = 'participant'
        
        if not username or not email or not password:
            return render_template('register.html', error="Все поля обязательны для заполнения")
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error="Пользователь с таким именем уже существует")
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error="Этот email уже зарегистрирован")
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(
            username=username, 
            email=email, 
            password=hashed_password, 
            role=role,
            email_confirmed=False
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
        
        # Явно указываем HTML и текстовую версии
        msg.body = f"Для подтверждения email перейдите по ссылке: {confirm_url}"
        msg.html = render_template(
            'email_confirmation_message.html',
            confirm_url=confirm_url,
            username=user.username
        )
        
        try:
            mail.send(msg)

            # Небольшая отладка
            print("письмо отправлено")

            return render_template('register.html',
                                success="Письмо с подтверждением отправлено!")
        except Exception as e:
            print(f"Ошибка отправки письма: {str(e)}")
            # Логируем детали ошибки SMTP, если они есть
            if hasattr(e, 'smtp_error'):
                print(f"SMTP error: {e.smtp_error}")
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
    if 'username' not in session or session['role'] != 'organizer':
        return redirect(url_for('home'))
    
    tags = Tag.query.all()
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        format_type = request.form.get('format')
        location = request.form.get('location')
        date_time = datetime.strptime(request.form.get('date_time'), '%Y-%m-%dT%H:%M')
        duration = int(request.form.get('duration'))
        lat = float(request.form.get('lat', 0))
        lng = float(request.form.get('lng', 0))
        event_type = request.form.get('event_type')
        selected_tags = request.form.getlist('tags')
        image_url = None

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Создаем папку, если ее нет
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
            location=location,
            date_time=date_time,
            duration=duration,
            lat=lat,
            lng=lng,
            event_type=event_type,
            image_url=image_url
        )
        db.session.add(event)
        db.session.flush()
        for tag_id in selected_tags:
            tag = Tag.query.get(tag_id)
            if tag:
                db.session.add(EventTag(event_id=event.id, tag_id=tag.id))
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
    events = Event.query.filter_by(is_active=True).all()
    m = folium.Map(location=[53.9, 27.5667], zoom_start=7)
    for event in events:
        if event.lat and event.lng:
            folium.Marker(
                [event.lat, event.lng],
                popup=f"{event.title}<br>{event.location}"
            ).add_to(m)
    map_html = m._repr_html_()
    return render_template('map.html', map_html=map_html)


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
    if 'username' not in session or session['role'] != 'organizer':
        return redirect(url_for('home'))
    if request.method == 'POST':
        tag_name = request.form.get('tag_name')
        if tag_name and not Tag.query.filter_by(name=tag_name).first():
            db.session.add(Tag(name=tag_name))
            db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_tag.html')


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
    
    user = User.query.filter_by(username=session['username']).first()
    events = Event.query.filter_by(organizer_id=user.id, is_active=True).all()
    
    return render_template('my_events.html', events=events)

# Удаление мероприятия
@app.route('/delete_event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    if 'username' not in session or session['role'] != 'organizer':
        return jsonify({"error": "Unauthorized"}), 401
    
    event = Event.query.get_or_404(event_id)
    user = User.query.filter_by(username=session['username']).first()
    
    if event.organizer_id != user.id:
        return jsonify({"error": "Forbidden"}), 403
    
    # Мягкое удаление (изменение статуса is_active)
    event.is_active = False
    db.session.commit()
    
    return jsonify({"success": True})

# Редактирование мероприятия
@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'username' not in session or session['role'] != 'organizer':
        return redirect(url_for('home'))
    
    event = Event.query.get_or_404(event_id)
    user = User.query.filter_by(username=session['username']).first()
    
    if event.organizer_id != user.id:
        return redirect(url_for('home'))
    
    tags = Tag.query.all()
    
    if request.method == 'POST':
        event.title = request.form.get('title')
        event.description = request.form.get('description')
        event.format = request.form.get('format')
        event.location = request.form.get('location')
        event.date_time = datetime.strptime(request.form.get('date_time'), '%Y-%m-%dT%H:%M')
        event.duration = int(request.form.get('duration'))
        event.lat = float(request.form.get('lat', 0))
        event.lng = float(request.form.get('lng', 0))
        event.event_type = request.form.get('event_type')
        
        # Обновление тегов
        EventTag.query.filter_by(event_id=event.id).delete()
        selected_tags = request.form.getlist('tags')
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
    
    # Заполняем форму текущими данными
    selected_tag_ids = [tag.id for tag in event.tags]
    return render_template('edit_event.html', event=event, tags=tags, selected_tag_ids=selected_tag_ids)


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

    role_in_text = {
        'organizer': "Организатор",
        'participant': "Участник"
    }

    return render_template('profile.html',
                         username=user.username,
                         email=user.email,
                         role=role_in_text.get(user.role, "Участник"),
                         attended_events=attended_events,
                         planned_events=planned_events)

if __name__ == '__main__':
    app.run(debug=True)