import pytest
from datetime import datetime

# Базовые проверки доступности страниц
def test_index_page_status(client):
    assert client.get("/").status_code == 200

def test_about_page_status(client):
    assert client.get("/about").status_code == 200

def test_posts_index_status(client):
    assert client.get("/posts").status_code == 200

# Тесты для страницы со списком постов
def test_posts_index_content(client):
    response = client.get("/posts")
    assert "Последние посты" in response.text

def test_posts_index_template_used(client, captured_templates, mocker, posts_list):
    with captured_templates as templates:
        mocker.patch("app.posts_list", return_value=posts_list, autospec=True)
        client.get('/posts')
        assert len(templates) == 1
        assert templates[0][0].name == 'posts.html'

def test_posts_index_context_data(client, captured_templates, mocker, posts_list):
    with captured_templates as templates:
        mocker.patch("app.posts_list", return_value=posts_list, autospec=True)
        client.get('/posts')
        context = templates[0][1]
        assert context['title'] == 'Посты'
        assert len(context['posts']) == 1

# Тесты для страницы конкретного поста (Обработка ошибок)
def test_post_invalid_id_returns_404(client):
    response = client.get("/posts/999")
    assert response.status_code == 404

def test_post_negative_id_returns_404(client):
    response = client.get("/posts/-1")
    assert response.status_code == 404

def test_post_valid_id_returns_200(client, mocker, posts_list):
    mocker.patch("app.posts_list", return_value=posts_list, autospec=True)
    assert client.get("/posts/0").status_code == 200

# Тесты рендеринга и передачи данных в шаблон
def test_post_template_used(client, captured_templates, mocker, posts_list):
    with captured_templates as templates:
        mocker.patch("app.posts_list", return_value=posts_list, autospec=True)
        client.get('/posts/0')
        assert templates[0][0].name == 'post.html'

def test_post_context_passed(client, captured_templates, mocker, posts_list):
    with captured_templates as templates:
        mocker.patch("app.posts_list", return_value=posts_list, autospec=True)
        client.get('/posts/0')
        context = templates[0][1]
        assert 'post' in context
        assert context['post']['title'] == 'Заголовок поста'

def test_post_renders_title_and_text(client, mocker, posts_list):
    mocker.patch("app.posts_list", return_value=posts_list, autospec=True)
    response = client.get("/posts/0")
    assert "Заголовок поста" in response.text
    assert "Текст поста" in response.text

def test_post_renders_author(client, mocker, posts_list):
    mocker.patch("app.posts_list", return_value=posts_list, autospec=True)
    response = client.get("/posts/0")
    assert "Иванов Иван Иванович" in response.text

def test_post_renders_correct_date_format(client, mocker, posts_list):
    # Дата в фикстуре: 2025, 3, 10
    mocker.patch("app.posts_list", return_value=posts_list, autospec=True)
    response = client.get("/posts/0")
    assert "10.03.2025" in response.text

def test_post_renders_comment_form(client, mocker, posts_list):
    mocker.patch("app.posts_list", return_value=posts_list, autospec=True)
    response = client.get("/posts/0")
    assert "<form>" in response.text
    assert "Отправить" in response.text

def test_footer_is_present_in_base(client):
    response = client.get("/")
    assert "Ермаков Михаил Андреевич, 241-371" in response.text