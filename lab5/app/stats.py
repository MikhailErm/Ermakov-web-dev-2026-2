import csv
import io
from flask import Blueprint, render_template, request, make_response
from flask_login import current_user, login_required
from sqlalchemy import desc, func
from app import db, VisitLog, User, check_rights

stats_bp = Blueprint('stats', __name__, url_prefix='/logs')

@stats_bp.route('/')
@login_required
@check_rights('view_logs')
def journal():
    page = request.args.get('page', 1, type=int)
    query = VisitLog.query
    
    if current_user.role.name == 'Пользователь':
        query = query.filter_by(user_id=current_user.id)
        
    logs = query.order_by(VisitLog.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('logs/journal.html', title='Журнал посещений', logs=logs)

@stats_bp.route('/pages')
@login_required
@check_rights('view_logs') # Администраторам
def pages_report():
    if current_user.role.name != 'Администратор':
        return "Доступ запрещен", 403
        
    stats = db.session.query(VisitLog.path, func.count(VisitLog.id).label('count'))\
        .group_by(VisitLog.path).order_by(desc('count')).all()
    return render_template('logs/pages_report.html', title='Статистика по страницам', stats=stats)

@stats_bp.route('/users')
@login_required
@check_rights('view_logs')
def users_report():
    if current_user.role.name != 'Администратор':
        return "Доступ запрещен", 403

    # Группируем логи по user_id
    stats = db.session.query(
        VisitLog.user_id,
        func.count(VisitLog.id).label('count')
    ).group_by(VisitLog.user_id).order_by(desc('count')).all()

    # Формируем список для шаблона, подтягивая ФИО вручную или через Join
    processed_stats = []
    for stat in stats:
        if stat.user_id:
            user = User.query.get(stat.user_id)
            full_name = user.full_name if user else "Удалённый пользователь"
        else:
            full_name = None # Это будет "Неаутентифицированный" в шаблоне
        
        processed_stats.append({
            'user_id': stat.user_id,
            'full_name': full_name,
            'count': stat.count
        })

    return render_template('logs/users_report.html', stats=processed_stats)
    
def generate_csv(header, rows, filename):
    si = io.StringIO()
    cw = csv.writer(si, delimiter=';') # Точка с запятой лучше для русского Excel
    cw.writerow(header)
    for row in rows:
        cw.writerow(row)
    
    output = make_response(si.getvalue().encode('utf-8-sig'))
    output.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    return output

@stats_bp.route('/pages/csv')
@login_required
def pages_csv():
    stats = db.session.query(VisitLog.path, func.count(VisitLog.id).label('count'))\
        .group_by(VisitLog.path).order_by(desc('count')).all()
    rows = [[i+1, stat.path, stat.count] for i, stat in enumerate(stats)]
    return generate_csv(['№', 'Страница', 'Количество посещений'], rows, 'pages_stats')

@stats_bp.route('/users/csv')
@login_required
def users_csv():
    stats = db.session.query(User, func.count(VisitLog.id).label('count'))\
        .outerjoin(VisitLog, User.id == VisitLog.user_id)\
        .group_by(User.id).order_by(desc('count')).all()
    
    rows = [[i+1, s[0].full_name, s[1]] for i, s in enumerate(stats)]
    guest_count = VisitLog.query.filter_by(user_id=None).count()
    if guest_count > 0:
        rows.append([len(rows)+1, 'Неаутентифицированный пользователь', guest_count])
        
    return generate_csv(['№', 'Пользователь', 'Количество посещений'], rows, 'users_stats')