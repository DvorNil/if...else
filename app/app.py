from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import folium

app = Flask(__name__)
app.secret_key = 'x7k9p2m4n6b8v0c1z3q5w8e9r2t4y6u'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
Session(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='participant')

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

# Создание таблиц и добавление начальных данных
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='participant1').first():
        hashed_pwd = bcrypt.generate_password_hash('pass123').decode('utf-8')
        user1 = User(username='participant1', email='participant1@example.com', password=hashed_pwd, role='participant')
        db.session.add(user1)
    if not User.query.filter_by(username='organizer1').first():
        hashed_pwd = bcrypt.generate_password_hash('org456').decode('utf-8')
        user2 = User(username='organizer1', email='organizer1@example.com', password=hashed_pwd, role='organizer')
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
    events = Event.query.filter_by(is_active=True).all()
    tags = Tag.query.all()
    return render_template('index.html', posts=events, tags=tags)

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
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
        user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()
        
        session['username'] = username
        session['role'] = role
        return redirect(url_for('home'))
    
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
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = url_for('static', filename=f'uploads/{filename}')

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

if __name__ == '__main__':
    app.run(debug=True)