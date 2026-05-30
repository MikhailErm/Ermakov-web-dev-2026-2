import pytest
import sys
import os

# 1. Настройка путей (поднимаемся из app/tests в корень проекта)
current_dir = os.path.dirname(__file__) 
app_dir = os.path.abspath(os.path.join(current_dir, '..')) 
base_dir = os.path.abspath(os.path.join(app_dir, '..'))     

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 2. Импортируем фабрику из пакета app
# Поскольку conftest лежит внутри app/tests, импортируем из __init__.py пакета app
try:
    from app import create_app
except ImportError:
    # Если запуск идет из папки app, пробуем прямой импорт
    sys.path.insert(0, app_dir)
    from __init__ import create_app

from app.models import db, User, Course, Review, Category, Image

@pytest.fixture(scope='session')
def app():
    # Создаем приложение с тестовой конфигурацией
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    }
    
    flask_app = create_app(test_config)
    return flask_app

@pytest.fixture
def client(app):
    with app.app_context():
        db.create_all()
        
        # Подготовка необходимых данных для внешних ключей Course
        cat = Category(name="Программирование")
        img = Image(id="test_bg", file_name="bg.jpg", mime_type="image/jpeg", md5_hash="hash_1")
        db.session.add_all([cat, img])
        db.session.commit()

        # Создаем администратора/автора
        user = User(first_name="Admin", last_name="Adminov", login="admin")
        user.set_password("admin123")
        db.session.add(user)
        db.session.commit()

        # Создаем курс для тестов
        course = Course(
            name="Тестовый курс",
            short_desc="Описание",
            full_desc="Полное описание",
            category_id=cat.id,
            author_id=user.id,
            background_image_id=img.id
        )
        db.session.add(course)
        db.session.commit()
        
        yield app.test_client()
        
        db.session.remove()
        db.drop_all()

@pytest.fixture
def db_session(app):
    with app.app_context():
        return db.session