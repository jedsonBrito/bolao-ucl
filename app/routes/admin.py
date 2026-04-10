from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from functools import wraps
from ..models import db, User, Match, Prediction, AuditLog
from ..utils import calculate_points

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Acesso negado. Área exclusiva de administradores.', 'danger')
            return redirect(url_for('user.dashboard'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────────────────────────

@admin_bp.route('/')
@admin_required
def dashboard():
    total_users = User.query.filter_by(role='user').count()
    blocked_users = User.query.filter_by(role='user', is_blocked=True).count()
    total_matches = Match.query.count()
    finished_matches = Match.query.filter_by(status='finished').count()
    total_predictions = Prediction.query.count()

    recent_logs = (AuditLog.query
                   .order_by(AuditLog.created_at.desc())
                   .limit(10).all())

    upcoming_matches = (Match.query
                        .filter_by(status='upcoming')
                        .order_by(Match.match_datetime)
                        .limit(5).all())

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           blocked_users=blocked_users,
                           total_matches=total_matches,
                           finished_matches=finished_matches,
                           total_predictions=total_predictions,
                           recent_logs=recent_logs,
                           upcoming_matches=upcoming_matches)


# ── Usuários ───────────────────────────────────────────────────────────────────

@admin_bp.route('/users')
@admin_required
def users():
    users_list = User.query.filter_by(role='user').order_by(User.username).all()
    return render_template('admin/users.html', users=users_list)


@admin_bp.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not username or not email or not password:
        flash('Todos os campos são obrigatórios.', 'danger')
        return redirect(url_for('admin.users'))

    if User.query.filter_by(username=username).first():
        flash('Nome de usuário já existe.', 'danger')
        return redirect(url_for('admin.users'))

    if User.query.filter_by(email=email).first():
        flash('E-mail já cadastrado.', 'danger')
        return redirect(url_for('admin.users'))

    user = User(username=username, email=email, role='user')
    user.set_password(password)
    db.session.add(user)

    _log('CREATE_USER', f'Admin criou usuário: {username}')
    db.session.commit()

    flash(f'Usuário {username} criado com sucesso!', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/edit/<int:user_id>', methods=['POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    email = request.form.get('email', '').strip()
    new_password = request.form.get('password', '').strip()

    if email:
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user_id:
            flash('E-mail já em uso.', 'danger')
            return redirect(url_for('admin.users'))
        user.email = email

    if new_password:
        if len(new_password) < 6:
            flash('Senha deve ter ao menos 6 caracteres.', 'danger')
            return redirect(url_for('admin.users'))
        user.set_password(new_password)

    _log('EDIT_USER', f'Admin editou usuário: {user.username}')
    db.session.commit()

    flash(f'Usuário {user.username} atualizado.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/toggle-block/<int:user_id>', methods=['POST'])
@admin_required
def toggle_block(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = not user.is_blocked
    status = 'bloqueado' if user.is_blocked else 'desbloqueado'
    action = 'BLOCK_USER' if user.is_blocked else 'UNBLOCK_USER'
    _log(action, f'Admin {status} usuário: {user.username}')
    db.session.commit()
    flash(f'Usuário {user.username} {status}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    username = user.username
    Prediction.query.filter_by(user_id=user_id).delete()
    _log('DELETE_USER', f'Admin excluiu usuário: {username}')
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuário {username} excluído.', 'success')
    return redirect(url_for('admin.users'))


# ── Partidas ───────────────────────────────────────────────────────────────────

@admin_bp.route('/matches')
@admin_required
def matches():
    matches_list = Match.query.order_by(Match.match_datetime).all()
    stages = sorted({m.stage for m in matches_list})
    return render_template('admin/matches.html', matches=matches_list, stages=stages)


@admin_bp.route('/matches/add', methods=['POST'])
@admin_required
def add_match():
    try:
        home_team = request.form.get('home_team', '').strip()
        away_team = request.form.get('away_team', '').strip()
        dt_str = request.form.get('match_datetime', '')
        stage = request.form.get('stage', '').strip()
        venue = request.form.get('venue', '').strip()

        if not home_team or not away_team or not dt_str or not stage:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('admin.matches'))

        match_dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')

        match = Match(
            home_team=home_team,
            away_team=away_team,
            match_datetime=match_dt,
            stage=stage,
            venue=venue
        )
        db.session.add(match)
        _log('ADD_MATCH', f'Partida cadastrada: {home_team} x {away_team} ({stage})')
        db.session.commit()
        flash(f'Partida {home_team} x {away_team} cadastrada!', 'success')
    except Exception as e:
        flash(f'Erro ao cadastrar partida: {e}', 'danger')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/matches/edit/<int:match_id>', methods=['POST'])
@admin_required
def edit_match(match_id):
    """Edita times e data/horário de partidas ainda não finalizadas."""
    match = Match.query.get_or_404(match_id)

    if match.status == 'finished':
        flash('Partida já finalizada. Não é possível editar.', 'danger')
        return redirect(url_for('admin.matches'))

    home_team = request.form.get('home_team', '').strip()
    away_team = request.form.get('away_team', '').strip()
    dt_str = request.form.get('match_datetime', '').strip()
    stage = request.form.get('stage', '').strip()
    venue = request.form.get('venue', '').strip()

    old_name = f'{match.home_team} x {match.away_team}'

    if home_team:
        match.home_team = home_team
    if away_team:
        match.away_team = away_team
    if dt_str:
        try:
            match.match_datetime = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Formato de data/hora inválido.', 'danger')
            return redirect(url_for('admin.matches'))
    if stage:
        match.stage = stage
    match.venue = venue

    _log('EDIT_MATCH', f'Partida editada: {old_name} → {match.home_team} x {match.away_team}')
    db.session.commit()
    flash(f'Partida atualizada: {match.home_team} x {match.away_team}', 'success')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/matches/result/<int:match_id>', methods=['POST'])
@admin_required
def set_result(match_id):
    match = Match.query.get_or_404(match_id)

    # Partida finalizada não pode ser alterada
    if match.status == 'finished':
        flash('Esta partida já foi finalizada e não pode ser editada.', 'danger')
        return redirect(url_for('admin.matches'))

    try:
        home_score = int(request.form.get('home_score', 0))
        away_score = int(request.form.get('away_score', 0))

        match.home_score = home_score
        match.away_score = away_score
        match.status = 'finished'

        # Calcular pontos de todos os palpites
        for pred in Prediction.query.filter_by(match_id=match_id).all():
            pred.points_earned = calculate_points(
                pred.home_score_pred, pred.away_score_pred,
                home_score, away_score
            )

        _log('SET_RESULT',
             f'Resultado: {match.home_team} {home_score}x{away_score} {match.away_team}')
        db.session.commit()
        flash(f'Resultado registrado: {match.home_team} {home_score} x {away_score} {match.away_team}', 'success')
    except Exception as e:
        flash(f'Erro ao registrar resultado: {e}', 'danger')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/matches/delete/<int:match_id>', methods=['POST'])
@admin_required
def delete_match(match_id):
    match = Match.query.get_or_404(match_id)

    # Partida finalizada não pode ser excluída
    if match.status == 'finished':
        flash('Não é possível excluir uma partida já finalizada.', 'danger')
        return redirect(url_for('admin.matches'))

    name = f'{match.home_team} x {match.away_team}'
    Prediction.query.filter_by(match_id=match_id).delete()
    _log('DELETE_MATCH', f'Partida excluída: {name}')
    db.session.delete(match)
    db.session.commit()
    flash(f'Partida {name} excluída.', 'success')
    return redirect(url_for('admin.matches'))


# ── Logs ───────────────────────────────────────────────────────────────────────

@admin_bp.route('/logs')
@admin_required
def logs():
    page = request.args.get('page', 1, type=int)
    user_filter = request.args.get('user', '').strip()
    action_filter = request.args.get('action', '').strip()

    query = AuditLog.query.order_by(AuditLog.created_at.desc())

    if user_filter:
        u = User.query.filter_by(username=user_filter).first()
        if u:
            query = query.filter_by(user_id=u.id)
        else:
            query = query.filter(False)

    if action_filter:
        query = query.filter_by(action=action_filter)

    pagination = query.paginate(page=page, per_page=50, error_out=False)

    all_actions = [r[0] for r in db.session.query(AuditLog.action).distinct().all()]

    return render_template('admin/logs.html',
                           logs=pagination,
                           user_filter=user_filter,
                           action_filter=action_filter,
                           all_actions=sorted(all_actions))


# ── helpers internos ───────────────────────────────────────────────────────────

def _log(action: str, details: str):
    """Registra log de auditoria para o admin atual."""
    entry = AuditLog(
        user_id=current_user.id,
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(entry)
