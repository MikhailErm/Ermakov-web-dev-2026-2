import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

def login(client, username, password, remember=False):
    return client.post('/login', data=dict(
        username=username,
        password=password,
        remember='y' if remember else ''
    ), follow_redirects=True)

# 1. Счётчик посещений работает корректно
def test_counter_increments(client):
    response1 = client.get('/counter')
    assert b'1' in response1.data
    response2 = client.get('/counter')
    assert b'2' in response2.data

# 2. Изолированность счётчика (симуляция нового пользователя)
def test_counter_isolated():
    with app.test_client() as c1, app.test_client() as c2:
        c1.get('/counter')
        c1.get('/counter')
        assert b'2' in c1.get('/counter').data
        assert b'1' in c2.get('/counter').data

# 3. После успешной аутентификации редирект на главную и сообщение
def test_login_success(client):
    response = login(client, 'user', 'qwerty')
    assert response.status_code == 200
    assert 'Вы успешно вошли в систему!'.encode('utf-8') in response.data
    assert 'Задание к лабораторной работе'.encode('utf-8') in response.data

# 4. После неудачной попытки пользователь остается на странице и видит ошибку
def test_login_failure(client):
    response = login(client, 'admin', 'admin')
    assert 'login' in response.request.path
    assert 'Неверный логин или пароль'.encode('utf-8') in response.data

# 5. Аутентифицированный пользователь имеет доступ к секретной странице
def test_secret_page_access(client):
    login(client, 'user', 'qwerty')
    response = client.get('/secret')
    assert response.status_code == 200
    assert 'Доступ разрешен'.encode('utf-8') in response.data

# 6. Аноним перенаправляется на страницу аутентификации с сообщением
def test_secret_page_redirects_anonymous(client):
    response = client.get('/secret', follow_redirects=True)
    assert 'login' in response.request.path
    assert 'Пожалуйста, авторизуйтесь'.encode('utf-8') in response.data

# 7. Автоматический редирект на секретную страницу после входа по `next`
def test_login_redirect_next(client):
    response = client.post('/login?next=/secret', data=dict(
        username='user',
        password='qwerty'
    ), follow_redirects=False)
    
    assert response.status_code == 302
    assert '/secret' in response.headers['Location']

# 8. Параметр "Запомнить меня" работает (устанавливается remember_token)
def test_remember_me_cookie(client):
    response = client.post('/login', data=dict(
        username='user',
        password='qwerty',
        remember='y'
    ), follow_redirects=False)
    
    set_cookie_headers = response.headers.getlist('Set-Cookie')
    assert any('remember_token' in cookie for cookie in set_cookie_headers)

# 9. В навбаре скрываются ссылки для анонима (нет кнопки "Выйти")
def test_navbar_anonymous(client):
    response = client.get('/')
    assert 'Войти'.encode('utf-8') in response.data
    assert 'Выйти'.encode('utf-8') not in response.data
    assert 'Секретная страница'.encode('utf-8') not in response.data

# 10. В навбаре показываются ссылки для авторизованного (есть кнопка "Выйти")
def test_navbar_authenticated(client):
    login(client, 'user', 'qwerty')
    response = client.get('/')
    assert 'Выйти'.encode('utf-8') in response.data
    assert 'Секретная страница'.encode('utf-8') in response.data
    assert 'Войти'.encode('utf-8') not in response.data