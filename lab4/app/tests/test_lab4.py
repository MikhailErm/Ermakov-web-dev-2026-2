import pytest
from app import app, db, User
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-key'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            u = User(login='admin1', last_name='Иванов', first_name='Иван')
            u.password_hash = generate_password_hash('passworD1!')
            db.session.add(u)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()
            
def login(client, username, password):
    return client.post('/login', data=dict(username=username, password=password), follow_redirects=True)

def test_users_page_access(client):
    response = client.get('/users')
    assert response.status_code == 200
    assert 'Иванов Иван'.encode('utf-8') in response.data

def test_unauth_create_redirect(client):
    response = client.get('/users/create', follow_redirects=True)
    assert 'Пожалуйста, авторизуйтесь'.encode('utf-8') in response.data

def test_create_validation_error(client):
    auth_response = login(client, 'admin1', 'passworD1!')
    assert "Неверный логин или пароль".encode('utf-8') not in auth_response.data
    
    response = client.post('/users/create', data={
        'login': 'newuser1',
        'password': 'Bad Password 1',
        'last_name': 'П',
        'first_name': 'П'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "Создание пользователя".encode('utf-8') in response.data