import random
import re
from functools import lru_cache
from datetime import datetime
from flask import Flask, render_template, abort, request, make_response, session, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from faker import Faker
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlsplit

fake = Faker()
app = Flask(__name__)
application = app

images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
              '2d2ab7df-cdbc-48a8-a936-35bba702def5',
              '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
              'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
              'cab5b7f2-774e-4884-a200-0c0180fa777f']

app.secret_key = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lab4.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Пожалуйста, авторизуйтесь для доступа к этой странице."
login_manager.login_message_category = "warning"

def generate_comments(replies=True):
    comments = []
    for _ in range(random.randint(1, 3)):
        comment = { 'author': fake.name(), 'text': fake.text() }
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments

def generate_post(i):
    return {
        'title': 'Заголовок поста',
        'text': fake.paragraph(nb_sentences=100),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-2y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': generate_comments()
    }

@lru_cache
def posts_list():
    return sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)

#Модели БД
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    role = db.relationship('Role', backref='users')

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#Валидация
def validate_user_form(data, is_edit=False):
    errors = {}
    
    if not data.get('last_name', '').strip():
        errors['last_name'] = "Поле не может быть пустым"
    if not data.get('first_name', '').strip():
        errors['first_name'] = "Поле не может быть пустым"

    if not is_edit:
        login = data.get('login', '').strip()
        if not login:
            errors['login'] = "Поле не может быть пустым"
        elif len(login) < 5 or not re.match(r'^[a-zA-Z0-9]+$', login):
            errors['login'] = "Логин должен содержать только латиницу и цифры, длина от 5 символов"
        elif User.query.filter_by(login=login).first():
            errors['login'] = "Такой логин уже занят"

        pwd = data.get('password', '')
        if not pwd:
            errors['password'] = "Поле не может быть пустым"
        else:
            if not (8 <= len(pwd) <= 128):
                errors['password'] = "Пароль должен быть от 8 до 128 символов"
            elif ' ' in pwd:
                errors['password'] = "Пароль не должен содержать пробелы"
            # Проверка допустимых символов (32 кириллические буквы, без Ё/ё)
            elif not re.match(r'^[a-zA-Zа-еж-яА-ЕЖ-Я0-9\~\!\?\@\#\$\%\^\&\*\_\-\+\(\)\[\]\{\}\>\<\/\\\|\'\"\.\,\:\;]+$', pwd):
                errors['password'] = "Пароль содержит недопустимые символы"
            elif not re.search(r'[a-zа-еж-я]', pwd) or not re.search(r'[A-ZА-ЕЖ-Я]', pwd):
                errors['password'] = "Пароль должен содержать как минимум одну строчную и одну заглавную букву"
            elif not re.search(r'[0-9]', pwd):
                errors['password'] = "Пароль должен содержать как минимум одну цифру"

    return errors

#Инициализация БД для тестов
with app.app_context():
    db.create_all()
    if not Role.query.first():
        db.session.add(Role(name='Администратор', description='Полные права'))
        db.session.add(Role(name='Пользователь', description='Базовые права'))
        db.session.commit()

#Маршруты CRUD пользователей
@app.route('/users')
def users():
    users_list = User.query.all()
    return render_template('users.html', title='Список пользователей', users=users_list)

@app.route('/users/view/<int:user_id>')
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('view_user.html', title='Просмотр', user=user)

@app.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    roles = Role.query.all()
    errors = {}
    if request.method == 'POST':
        errors = validate_user_form(request.form)
        if not errors:
            new_user = User(
                login=request.form.get('login'),
                password_hash=generate_password_hash(request.form.get('password')),
                last_name=request.form.get('last_name'),
                first_name=request.form.get('first_name'),
                middle_name=request.form.get('middle_name') or None,
                role_id=request.form.get('role_id') or None
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Пользователь успешно создан!', 'success')
            return redirect(url_for('users'))
        flash('Допущены ошибки при заполнении формы', 'danger')
    return render_template('create_user.html', title='Создание пользователя', roles=roles, errors=errors)

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    errors = {}
    if request.method == 'POST':
        errors = validate_user_form(request.form, is_edit=True)
        if not errors:
            user.last_name = request.form.get('last_name')
            user.first_name = request.form.get('first_name')
            user.middle_name = request.form.get('middle_name') or None
            user.role_id = request.form.get('role_id') or None
            db.session.commit()
            flash('Данные успешно обновлены!', 'success')
            return redirect(url_for('users'))
        flash('Допущены ошибки при заполнении формы', 'danger')
    return render_template('edit_user.html', title='Редактирование', user=user, roles=roles, errors=errors)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Пользователь {user.full_name} успешно удален!', 'success')
    return redirect(url_for('users'))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    errors = {}
    if request.method == 'POST':
        old_pass = request.form.get('old_password')
        new_pass = request.form.get('new_password')
        repeat_pass = request.form.get('repeat_password')

        if not check_password_hash(current_user.password_hash, old_pass):
            errors['old_password'] = "Неверный старый пароль"
        
        if new_pass != repeat_pass:
            errors['repeat_password'] = "Пароли не совпадают"

        fake_data = {'password': new_pass}
        pwd_errors = validate_user_form(fake_data, is_edit=False)
        if 'password' in pwd_errors:
            errors['new_password'] = pwd_errors['password']

        if not errors:
            current_user.password_hash = generate_password_hash(new_pass)
            db.session.commit()
            flash('Пароль успешно изменен', 'success')
            return redirect(url_for('index'))
            
    return render_template('change_password.html', title='Смена пароля', errors=errors)

#Маршруты
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(login=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            flash('Вы успешно вошли в систему!', 'success')
            next_page = request.args.get('next')
            if not next_page or urlsplit(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
        else:
            flash('Неверный логин или пароль', 'danger')

    return render_template('login.html', title='Вход')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/posts')
def posts():
    return render_template('posts.html', title='Посты', posts=posts_list())

@app.route('/posts/<int:index>')
def post(index):
    posts = posts_list()
    if index < 0 or index >= len(posts):
        abort(404)
    p = posts[index]
    return render_template('post.html', title=p['title'], post=p)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')

@app.route('/url_params')
def url_params():
    return render_template('url_params.html', title='Параметры URL', params=request.args)

@app.route('/headers')
def headers_page():
    return render_template('headers.html', title='Заголовки запроса', headers=request.headers)

@app.route('/cookies')
def cookies_page():
    cookie_name = 'lab_test_cookie'
    cookie_val = request.cookies.get(cookie_name)
    
    if cookie_val:
        msg = f"Куки '{cookie_name}' со значением '{cookie_val}' было установлено. Теперь оно удалено."
        resp = make_response(render_template('cookies.html', title='Cookie', msg=msg))
        resp.delete_cookie(cookie_name)
    else:
        msg = f"Куки '{cookie_name}' не было установлено. Теперь оно задано."
        resp = make_response(render_template('cookies.html', title='Cookie', msg=msg))
        resp.set_cookie(cookie_name, '123456')
        
    return resp

@app.route('/form_params', methods=['GET', 'POST'])
def form_params():
    return render_template('form_params.html', title='Параметры формы', form_data=request.form if request.method == 'POST' else None)

@app.route('/phone', methods=['GET', 'POST'])
def phone():
    phone_input = ""
    error_msg = ""
    formatted_phone = ""
    
    if request.method == 'POST':
        phone_input = request.form.get('phone', '')
        
        if not re.fullmatch(r'[\d\s\(\)\-\.\+]*', phone_input) or not phone_input:
            error_msg = "Недопустимый ввод. В номере телефона встречаются недопустимые символы."
        else:
            digits = re.sub(r'\D', '', phone_input)
            stripped_phone = phone_input.strip()
            
            if stripped_phone.startswith('+7') or stripped_phone.startswith('8'):
                if len(digits) != 11:
                    error_msg = "Недопустимый ввод. Неверное количество цифр."
                else:
                    base = digits[1:]
            else:
                if len(digits) != 10:
                    error_msg = "Недопустимый ввод. Неверное количество цифр."
                else:
                    base = digits
                    
            if not error_msg:
                formatted_phone = f"8-{base[0:3]}-{base[3:6]}-{base[6:8]}-{base[8:10]}"
                
    return render_template('phone.html', title='Проверка телефона', 
                           phone_input=phone_input, 
                           error_msg=error_msg, 
                           formatted_phone=formatted_phone)

@app.route('/counter')
def counter():
    session['visits'] = session.get('visits', 0) + 1
    return render_template('counter.html', title='Счётчик посещений', visits=session['visits'])

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html', title='Секретная страница')