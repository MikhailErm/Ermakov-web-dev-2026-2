from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required
from sqlalchemy.exc import IntegrityError
from app.models import db, Review, Course 
from sqlalchemy import select
from sqlalchemy import select, desc, asc
from flask_login import login_required, current_user
from app.models import db
from app.repositories import CourseRepository, UserRepository, CategoryRepository, ImageRepository

user_repository = UserRepository(db)
course_repository = CourseRepository(db)
category_repository = CategoryRepository(db)
image_repository = ImageRepository(db)

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]

def params():
    return { p: request.form.get(p) or None for p in COURSE_PARAMS }

def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }

@bp.route('/')
def index():
    pagination = course_repository.get_pagination_info(**search_params())
    courses = course_repository.get_all_courses(pagination=pagination)
    categories = category_repository.get_all_categories()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())

@bp.route('/new')
@login_required
def new():
    course = course_repository.new_course()
    categories = category_repository.get_all_categories()
    users = user_repository.get_all_users()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users,
                           course=course)

@bp.route('/create', methods=['POST'])
@login_required
def create():
    #Получаем файл
    f = request.files.get('background_img')
    img = None
    
    try:
        #Проверяем, пришел ли файл, иначе ставим заглушку (если в БД NOT NULL)
        if f and f.filename:
            img = image_repository.add_image(f)
            image_id = img.id
        else:
            #используем ID дефолтной картинки, которую мы создали в БД
            image_id = 'default-course-bg' 

        #Собираем параметры и проверяем категорию
        course_params = params()
        
        # Если категория не выбрана (None), ставим первую попавшуюся из базы, 
        # чтобы избежать IntegrityError
        if not course_params.get('category_id'):
            first_cat = category_repository.get_all_categories()[0]
            course_params['category_id'] = first_cat.id

        #Создаем курс
        course = course_repository.add_course(**course_params, background_image_id=image_id)
        
        db.session.commit() # Явный коммит, если репозиторий его не делает
        flash(f'Курс {course.name} успешно добавлен!', 'success')
        return redirect(url_for('courses.index'))

    except Exception as err:
        db.session.rollback() # Откатываем изменения при ошибке
        flash(f'Ошибка БД: {err}', 'danger')
        
        # Возвращаем пользователя на форму, чтобы он не видел 405 или 500
        categories = category_repository.get_all_categories()
        users = user_repository.get_all_users()
        return render_template('courses/new.html',
                               categories=categories,
                               users=users,
                               course=None)

@bp.route('/<int:course_id>')
def show(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)
    
    from app.models import db, Review 

    #Получаем 5 отзывов через db.session.execute
    query_reviews = select(Review).filter_by(course_id=course.id)\
                                  .order_by(Review.created_at.desc())\
                                  .limit(5)
    reviews = db.session.execute(query_reviews).scalars().all()
    
    #Проверяем отзыв пользователя
    user_review = None
    if current_user.is_authenticated:
        query_user = select(Review).filter_by(course_id=course.id, user_id=current_user.id)
        user_review = db.session.execute(query_user).scalar_one_or_none()

    return render_template('courses/show.html', 
                           course=course, 
                           reviews=reviews, 
                           user_review=user_review)
    
@bp.route('/<int:course_id>/reviews')
def reviews(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None: abort(404)

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'newest')

    from app.models import db, Review
    
    # Создаем базовый запрос
    stmt = select(Review).filter_by(course_id=course.id)

    # Применяем сортировку
    if sort_by == 'positive':
        stmt = stmt.order_by(desc(Review.rating), desc(Review.created_at))
    elif sort_by == 'negative':
        stmt = stmt.order_by(asc(Review.rating), desc(Review.created_at))
    else: # newest
        stmt = stmt.order_by(desc(Review.created_at))

    # Пагинация в стиле Flask-SQLAlchemy 3.0+
    pagination = db.paginate(stmt, page=page, per_page=5)
    
    user_review = None
    if current_user.is_authenticated:
        stmt_user = select(Review).filter_by(course_id=course.id, user_id=current_user.id)
        user_review = db.session.execute(stmt_user).scalar_one_or_none()

    return render_template('courses/reviews.html', 
                           course=course, 
                           pagination=pagination, 
                           sort_by=sort_by,
                           user_review=user_review)
    
@bp.route('/<int:course_id>/add_review', methods=['POST'])
@login_required
def add_review(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None: abort(404)

    rating = int(request.form.get('rating'))
    text = request.form.get('text')

    from app.models import db, Review

    # Проверка на дубликат
    stmt_check = select(Review).filter_by(course_id=course.id, user_id=current_user.id)
    existing_review = db.session.execute(stmt_check).scalar_one_or_none()
    
    if existing_review:
        # Если отзыв уже есть, просто возвращаем назад (или выводим ошибку)
        return redirect(url_for('courses.show', course_id=course.id))

    # Создаем новый объект отзыва
    new_review = Review(
        rating=rating,
        text=text,
        course_id=course.id,
        user_id=current_user.id
    )

    # Обновляем денормализованные данные рейтинга в модели Course
    course.rating_sum += rating
    course.rating_num += 1

    try:
        db.session.add(new_review)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при сохранении отзыва: {e}")
        abort(500)

    return redirect(url_for('courses.show', course_id=course.id))
