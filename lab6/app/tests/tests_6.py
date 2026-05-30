import pytest
import datetime
from app.models import Review, Course, User, db
from sqlalchemy import select

def login(client, username, password):
    return client.post('/auth/login', data={'login': username, 'password': password}, follow_redirects=True)

# 1. Проверка структуры модели Review: наличие полей id, rating, text, created_at
def test_review_model_structure(client):
    review = Review()
    assert hasattr(review, 'id')
    assert hasattr(review, 'rating')
    assert hasattr(review, 'text')
    assert hasattr(review, 'created_at')

# 2. Проверка отношений модели: наличие связей с таблицами Course и User
def test_review_relations(client):
    assert hasattr(Review, 'course')
    assert hasattr(Review, 'user')

# 3. Проверка отображения блока отзывов на главной странице курса
def test_course_page_reviews_presence(client):
    res = client.get('/courses/1')
    assert res.status_code == 200
    assert "Отзывы" in res.get_data(as_text=True)

# 4. Проверка ограничения: на главной странице курса отображается не более 5 последних отзывов
def test_only_five_reviews_on_main(client, app):
    with app.app_context():
        for i in range(10):
            r = Review(rating=5, text=f"LimitTest_{i}", course_id=1, user_id=1)
            db.session.add(r)
        db.session.commit()
    res = client.get('/courses/1')
    data = res.get_data(as_text=True)
    assert data.count("LimitTest") <= 5

# 5. Проверка доступности страницы со всеми отзывами курса (пагинация)
def test_pagination_url(client):
    res = client.get('/courses/1/reviews')
    assert res.status_code == 200

# 6. Проверка наличия элементов управления сортировкой в HTML-шаблоне
def test_sort_filter_exists(client):
    res = client.get('/courses/1/reviews')
    data = res.get_data(as_text=True)
    assert 'sort_by' in data or 'filter' in data

# 7. Проверка работоспособности сортировки "Сначала новые"
def test_sort_newest(client):
    res = client.get('/courses/1/reviews?sort_by=newest')
    assert res.status_code == 200

# 8. Проверка работоспособности сортировки "Сначала положительные"
def test_sort_positive(client):
    res = client.get('/courses/1/reviews?sort_by=positive')
    assert res.status_code == 200

# 9. Проверка работоспособности сортировки "Сначала отрицательные"
def test_sort_negative(client):
    res = client.get('/courses/1/reviews?sort_by=negative')
    assert res.status_code == 200

# 10. Проверка наличия полей формы (rating, text) для авторизованного пользователя
def test_review_form_fields(client):
    login(client, 'admin', 'admin123')
    res = client.get('/courses/1/reviews')
    data = res.get_data(as_text=True)
    assert 'name="rating"' in data
    assert '<textarea' in data

# 11. Проверка запрета публикации отзыва для неавторизованного пользователя
def test_anonymous_cant_post_review(client):
    res = client.post('/courses/1/add_review', data={'rating': 5, 'text': 'anon'}, follow_redirects=True)
    data = res.get_data(as_text=True).lower()
    login_keywords = ['вход', 'войти', 'авториз', 'login', 'пароль']
    assert any(word in data for word in login_keywords)

# 12. Проверка валидации: наличие в форме выбора оценок в диапазоне 0-5
def test_rating_values_check(client):
    login(client, 'admin', 'admin123')
    res = client.get('/courses/1/reviews')
    data = res.get_data(as_text=True)
    for i in range(6):
        assert f'value="{i}"' in data

# 13. Проверка корректного обновления суммы оценок (rating_sum) в модели Course
def test_rating_sum_update(client, app):
    login(client, 'admin', 'admin123')
    client.post('/courses/1/add_review', data={'rating': 5, 'text': 'Sum test'})
    with app.app_context():
        course = db.session.get(Course, 1)
        assert course.rating_sum >= 5

# 14. Проверка корректного инкремента количества отзывов (rating_num) в модели Course
def test_rating_num_update(client, app):
    login(client, 'admin', 'admin123')
    with app.app_context():
        initial_num = db.session.get(Course, 1).rating_num
    client.post('/courses/1/add_review', data={'rating': 4, 'text': 'Num test'})
    with app.app_context():
        course = db.session.get(Course, 1)
        assert course.rating_num == initial_num + 1

# 15. Проверка скрытия формы отзыва, если текущий пользователь уже оставил отзыв к этому курсу
def test_form_hidden_for_reviewed_user(client):
    login(client, 'admin', 'admin123')
    client.post('/courses/1/add_review', data={'rating': 5, 'text': 'Unique review'})
    res = client.get('/courses/1/reviews')
    assert '<textarea' not in res.get_data(as_text=True)

# 16. Проверка сохранения выбранного типа сортировки при переходе между страницами пагинации
def test_keep_sort_on_next_page(client, app):
    with app.app_context():
        for i in range(15):
            db.session.add(Review(rating=5, text=f"PagSort_{i}", course_id=1, user_id=1))
        db.session.commit()
    res = client.get('/courses/1/reviews?page=1&sort_by=positive')
    data = res.get_data(as_text=True)
    assert 'page=2' in data
    assert 'sort_by=positive' in data
