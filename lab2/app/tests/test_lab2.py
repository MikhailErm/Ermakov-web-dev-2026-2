import pytest

# 1. Отображение переданных параметров URL
def test_url_params_displayed(client):
    response = client.get('/url_params?key1=value1&test=flask')
    assert b'key1' in response.data
    assert b'value1' in response.data
    assert b'flask' in response.data

# 2. Отображение заголовков
def test_headers_displayed(client):
    response = client.get('/headers', headers={'X-Test-Header': 'Hello'})
    assert b'X-Test-Header' in response.data
    assert b'Hello' in response.data

# 3. Установка cookie, если оно не было установлено
def test_cookie_set_if_missing(client):
    response = client.get('/cookies')
    assert b'lab_test_cookie=123456' in response.headers.get('Set-Cookie', b'')

# 4. Удаление cookie, если оно уже установлено
def test_cookie_deleted_if_present(client):
    client.set_cookie('localhost', 'lab_test_cookie', '123456')
    response = client.get('/cookies')
    assert b'lab_test_cookie=;' in response.headers.get('Set-Cookie', b'') or b'Expires=Thu, 01 Jan 1970' in response.headers.get('Set-Cookie', b'')

# 5. Отображение параметров формы после POST-запроса
def test_form_params_displayed(client):
    response = client.post('/form_params', data={'testInput': 'MyTestValue'})
    assert b'testInput' in response.data
    assert 'MyTestValue'.encode('utf-8') in response.data

# 6. Валидация телефона: Успешная валидация номера 11 цифр с '+7'
def test_phone_valid_plus7(client):
    response = client.post('/phone', data={'phone': '+7 (123) 456-75-90'})
    assert b'8-123-456-75-90' in response.data

# 7. Валидация телефона: Успешная валидация номера 11 цифр с '8'
def test_phone_valid_8(client):
    response = client.post('/phone', data={'phone': '8(123)4567590'})
    assert b'8-123-456-75-90' in response.data

# 8. Валидация телефона: Успешная валидация номера 10 цифр
def test_phone_valid_10(client):
    response = client.post('/phone', data={'phone': '123.456.75.90'})
    assert b'8-123-456-75-90' in response.data

# 9. Валидация телефона: Ошибка недопустимых символов (буквы)
def test_phone_invalid_chars_letters(client):
    response = client.post('/phone', data={'phone': '+7 (123) abc-75-90'})
    assert 'В номере телефона встречаются недопустимые символы'.encode('utf-8') in response.data

# 10. Валидация телефона: Ошибка недопустимых символов (спецзнаки, которых нет в условии)
def test_phone_invalid_chars_symbols(client):
    response = client.post('/phone', data={'phone': '8(123)456-75-90!'})
    assert 'В номере телефона встречаются недопустимые символы'.encode('utf-8') in response.data

# 11. Валидация телефона: Ошибка неверного количества цифр (слишком короткий номер)
def test_phone_invalid_length_short(client):
    response = client.post('/phone', data={'phone': '8 (123) 456'})
    assert 'Неверное количество цифр'.encode('utf-8') in response.data

# 12. Валидация телефона: Ошибка неверного количества цифр (11 цифр, но не начинается с 7 или 8)
def test_phone_invalid_length_11_bad_start(client):
    response = client.post('/phone', data={'phone': '9 (123) 456-75-90'})
    assert 'Неверное количество цифр'.encode('utf-8') in response.data

# 13. Валидация телефона: Ошибка неверного количества цифр (слишком длинный номер)
def test_phone_invalid_length_long(client):
    response = client.post('/phone', data={'phone': '+7 (123) 456-75-90-12'})
    assert 'Неверное количество цифр'.encode('utf-8') in response.data

# 14. Валидация телефона: Использование классов Bootstrap is-invalid и invalid-feedback при ошибке
def test_phone_bootstrap_error_classes(client):
    response = client.post('/phone', data={'phone': 'invalid_phone'})
    assert b'is-invalid' in response.data
    assert b'invalid-feedback' in response.data

# 15. Валидация телефона: Отсутствие классов Bootstrap при успешном вводе
def test_phone_no_error_classes_on_success(client):
    response = client.post('/phone', data={'phone': '8(123)4567590'})
    assert b'is-invalid' not in response.data
    assert b'invalid-feedback' not in response.data