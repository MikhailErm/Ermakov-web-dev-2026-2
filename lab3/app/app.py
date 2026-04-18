import random
import re
from functools import lru_cache
from flask import Flask, render_template, abort, request, make_response
from faker import Faker
from flask import session, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
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

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Пожалуйста, авторизуйтесь для доступа к этой странице."
login_manager.login_message_category = "warning"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

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

@login_manager.user_loader
def load_user(user_id):
    if user_id == 'user':
        return User(user_id)
    return None

@lru_cache
def posts_list():
    return sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)

@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        if username == 'user' and password == 'qwerty':
            login_user(User(username), remember=remember)
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

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html', title='Секретная страница')