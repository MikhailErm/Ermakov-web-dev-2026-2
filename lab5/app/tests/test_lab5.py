import unittest
from app import app, db, User, Role
from werkzeug.security import generate_password_hash

class FlaskAppTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            db.drop_all()
            db.create_all()
            
            # Настройка ролей и пользователей
            admin_role = Role(name='Администратор')
            user_role = Role(name='Пользователь')
            db.session.add_all([admin_role, user_role])
            db.session.commit()

            # Создаем пользователей с реальными хешами паролей для тестов логина
            admin = User(
                login='admin', 
                password_hash=generate_password_hash('Admin123'), 
                last_name='Adminov', 
                first_name='A', 
                role_id=admin_role.id
            )
            user = User(
                login='user1', 
                password_hash=generate_password_hash('User123'), 
                last_name='Userov', 
                first_name='U', 
                role_id=user_role.id
            )
            db.session.add_all([admin, user])
            db.session.commit()
            
            # Сохраняем ID для использования в тестах
            self.admin_id = admin.id
            self.user_id = user.id

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_visit_logging(self):
        """Проверка добавления логов при запросе"""
        self.client.get('/about')
        with app.app_context():
            from app import VisitLog
            log = VisitLog.query.filter_by(path='/about').first()
            self.assertIsNotNone(log)

    def test_rbac_access_denied(self):
        """Проверка запрета доступа обычному пользователю к чужому профилю"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user_id)
            
        response = self.client.get(f'/users/edit/{self.admin_id}', follow_redirects=True)
        self.assertIn('У вас недостаточно прав'.encode('utf-8'), response.data)
        
    def test_csv_export(self):
        """Проверка генерации CSV файла администратором"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.admin_id)
            
        self.client.get('/about')
        
        response = self.client.get('/logs/pages/csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-type'], 'text/csv; charset=utf-8-sig')
        self.assertIn(b'/about', response.data)

    def test_login_success_valid_credentials(self):
        """Успешный вход с правильными логином и паролем"""
        response = self.client.post('/login', data={
            'username': 'admin',
            'password': 'Admin123',
            'remember': False
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Вы успешно вошли в систему'.encode('utf-8'), response.data)
        
        # Проверяем, что пользователь действительно авторизован
        response = self.client.get('/secret', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Секретная страница'.encode('utf-8'), response.data)

    def test_login_failure_wrong_password(self):
        """Отказ входа при неверном пароле"""
        response = self.client.post('/login', data={
            'username': 'admin',
            'password': 'WrongPassword123',
            'remember': False
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Неверный логин или пароль'.encode('utf-8'), response.data)
        
        # Проверяем, что пользователь НЕ авторизован
        response = self.client.get('/secret', follow_redirects=True)
        self.assertIn('Вход'.encode('utf-8'), response.data)

    def test_login_failure_nonexistent_user(self):
        """Отказ входа при несуществующем пользователе"""
        response = self.client.post('/login', data={
            'username': 'nonexistent_user',
            'password': 'SomePassword123',
            'remember': False
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Неверный логин или пароль'.encode('utf-8'), response.data)

    def test_login_failure_empty_fields(self):
        """Отказ входа при пустых полях"""
        response = self.client.post('/login', data={
            'username': '',
            'password': '',
            'remember': False
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Неверный логин или пароль'.encode('utf-8'), response.data)

    def test_logout_functionality(self):
        """Выход из системы работает корректно"""
        # Сначала входим
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'Admin123'
        })
        
        # Проверяем, что секретная страница доступна
        response = self.client.get('/secret', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Выходим из системы
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get('/secret', follow_redirects=True)
        self.assertIn('Вход'.encode('utf-8'), response.data)  # Перенаправление на страницу входа

    def test_protected_pages_redirect_to_login(self):
        """Защищенные страницы перенаправляют неавторизованных пользователей"""
        # Страницы, которые требуют авторизации
        protected_pages = ['/secret', '/users/create', '/change_password']
        
        for page in protected_pages:
            response = self.client.get(page, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            # Проверяем, что на странице есть форма входа
            self.assertIn('Вход'.encode('utf-8'), response.data)
            self.assertIn('Логин'.encode('utf-8'), response.data)
            self.assertIn('Пароль'.encode('utf-8'), response.data)
    
    def test_users_page_accessible_to_authenticated(self):
        """Страница /users доступна авторизованным пользователям"""
        # Сначала входим
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'Admin123'
        })
        
        # Проверяем, что страница users доступна
        response = self.client.get('/users', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Список пользователей'.encode('utf-8'), response.data)

    def test_login_remember_me_functionality(self):
        """Функция 'Запомнить меня' работает корректно"""
        response = self.client.post('/login', data={
            'username': 'admin',
            'password': 'Admin123',
            'remember': True
        }, follow_redirects=True)
        
        # Проверяем, что установлена сессия
        with self.client.session_transaction() as sess:
            self.assertIsNotNone(sess.get('_user_id'))
        
        # Проверяем, что защищенные страницы доступны
        response = self.client.get('/secret')
        self.assertEqual(response.status_code, 200)

    def test_login_redirect_to_next_parameter(self):
        """Перенаправление на запрошенную страницу после входа"""
        # Пытаемся получить доступ к защищенной странице без авторизации
        response = self.client.get('/secret', follow_redirects=False)
        
        # Проверяем, что происходит редирект
        self.assertEqual(response.status_code, 302)
        
        # Входим с параметром next
        response = self.client.post('/login?next=/secret', data={
            'username': 'admin',
            'password': 'Admin123'
        }, follow_redirects=False)
        
        # Проверяем, что после входа перенаправляет на /secret
        self.assertEqual(response.status_code, 302)
        location = response.headers.get('Location', '')
        self.assertTrue('/secret' in location or location.endswith('/secret'))

if __name__ == '__main__':
    unittest.main()