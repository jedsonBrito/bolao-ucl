from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from ..models import db, User, Match, Prediction, AuditLog
from ..utils import calculate_points

user_bp = Blueprint('user', __name__)


def _get_ranking():
    """Retorna lista ordenada de usuários com suas estatísticas para ranking."""
    users = User.query.filter_by(role='user').all()
    data = []
    for u in users:
        finished_preds = [p for p in u.predictions if p.points_earned is not None]
        total_pts = sum(p.points_earned for p in finished_preds)
        exact = sum(1 for p in finished_preds if p.points_earned == 10)
        result_plus = sum(1 for p in finished_preds if p.points_earned == 7)
        result_only = sum(1 for p in finished_preds if p.points_earned == 5)
        one_team = sum(1 for p in finished_preds if p.points_earned == 2)
        total_preds = len(u.predictions)
        earliest = min((p.created_at for p in u.predictions), default=datetime.max)
        data.append({
            'user': u,
            'total_points': total_pts,
            'exact': exact,
            'result_plus': result_plus,
            'result_only': result_only,
            'one_team': one_team,
            'total_preds': total_preds,
            'earliest': earliest,
        })
    # Ordenar: pontos desc, desempate pelo palpite mais antigo (asc)
    data.sort(key=lambda x: (-x['total_points'], x['earliest']))
    for i, item in enumerate(data):
        item['position'] = i + 1
    return data


# ── Dashboard ──────────────────────────────────────────────────────────────────

@user_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))

    ranking = _get_ranking()
    user_pos = next((r for r in ranking if r['user'].id == current_user.id), None)

    now = datetime.utcnow()
    next_match = (Match.query
                  .filter(Match.status == 'upcoming', Match.match_datetime > now)
                  .order_by(Match.match_datetime)
                  .first())

    next_pred = None
    if next_match:
        next_pred = Prediction.query.filter_by(
            user_id=current_user.id, match_id=next_match.id
        ).first()

    recent_preds = (Prediction.query
                    .filter_by(user_id=current_user.id)
                    .join(Match)
                    .filter(Match.status == 'finished')
                    .order_by(Match.match_datetime.desc())
                    .limit(5).all())

    return render_template('user/dashboard.html',
                           ranking=ranking,
                           user_pos=user_pos,
                           next_match=next_match,
                           next_pred=next_pred,
                           recent_preds=recent_preds,
                           now=now)


# ── Palpites ───────────────────────────────────────────────────────────────────

@user_bp.route('/predictions')
@login_required
def predictions():
    if current_user.is_blocked:
        flash('Sua conta está bloqueada. Novos palpites não são permitidos.', 'danger')
        return redirect(url_for('user.dashboard'))

    matches = Match.query.order_by(Match.match_datetime).all()
    user_preds = {p.match_id: p for p in Prediction.query.filter_by(user_id=current_user.id).all()}

    # Agrupar por fase
    grouped = {}
    stage_order = {}
    for m in matches:
        if m.stage not in grouped:
            grouped[m.stage] = []
            stage_order[m.stage] = m.match_datetime
        grouped[m.stage].append({'match': m, 'prediction': user_preds.get(m.id)})

    # Ordenar fases cronologicamente
    ordered_stages = sorted(grouped.keys(), key=lambda s: stage_order[s])

    now = datetime.utcnow()
    return render_template('user/predictions.html',
                           grouped=grouped,
                           ordered_stages=ordered_stages,
                           user_preds=user_preds,
                           now=now)


@user_bp.route('/predictions/save/<int:match_id>', methods=['POST'])
@login_required
def save_prediction(match_id):
    if current_user.is_blocked:
        flash('Sua conta está bloqueada.', 'danger')
        return redirect(url_for('user.predictions'))

    match = Match.query.get_or_404(match_id)

    if match.is_locked:
        flash('Prazo encerrado! Palpites são travados 5 minutos antes do início.', 'danger')
        return redirect(url_for('user.predictions'))

    if match.status == 'finished':
        flash('Esta partida já foi encerrada.', 'danger')
        return redirect(url_for('user.predictions'))

    try:
        home_sc = int(request.form.get('home_score', 0))
        away_sc = int(request.form.get('away_score', 0))
        if home_sc < 0 or away_sc < 0:
            raise ValueError('Placar negativo')
    except (ValueError, TypeError):
        flash('Placar inválido.', 'danger')
        return redirect(url_for('user.predictions'))

    existing = Prediction.query.filter_by(
        user_id=current_user.id, match_id=match_id
    ).first()

    if existing:
        existing.home_score_pred = home_sc
        existing.away_score_pred = away_sc
        existing.updated_at = datetime.utcnow()
        msg = 'atualizado'
    else:
        pred = Prediction(
            user_id=current_user.id,
            match_id=match_id,
            home_score_pred=home_sc,
            away_score_pred=away_sc
        )
        db.session.add(pred)
        msg = 'salvo'

    log = AuditLog(
        user_id=current_user.id,
        action='SAVE_PREDICTION',
        details=f'Palpite {msg}: {match.home_team} {home_sc}x{away_sc} {match.away_team} — jogo {match_id}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Palpite {msg} com sucesso!', 'success')
    return redirect(url_for('user.predictions'))


# ── Classificação ──────────────────────────────────────────────────────────────

@user_bp.route('/ranking')
@login_required
def ranking():
    data = _get_ranking()
    return render_template('user/ranking.html', ranking=data)


# ── Extrato ────────────────────────────────────────────────────────────────────

@user_bp.route('/extract')
@login_required
def extract():
    preds = (Prediction.query
             .filter_by(user_id=current_user.id)
             .join(Match)
             .order_by(Match.match_datetime.desc())
             .all())

    total = sum(p.points_earned or 0 for p in preds if p.points_earned is not None)
    pending = sum(1 for p in preds if p.points_earned is None)
    done = sum(1 for p in preds if p.points_earned is not None)

    return render_template('user/extract.html',
                           predictions=preds,
                           total_points=total,
                           pending=pending,
                           done=done)


# ── Configurações ──────────────────────────────────────────────────────────────

@user_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'change_password':
            cur_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            conf_pw = request.form.get('confirm_password', '')

            if not current_user.check_password(cur_pw):
                flash('Senha atual incorreta.', 'danger')
            elif len(new_pw) < 6:
                flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
            elif new_pw != conf_pw:
                flash('As senhas não conferem.', 'danger')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Senha alterada com sucesso!', 'success')

        elif action == 'change_email':
            new_email = request.form.get('email', '').strip()
            if not new_email or '@' not in new_email:
                flash('E-mail inválido.', 'danger')
            elif User.query.filter(
                User.email == new_email, User.id != current_user.id
            ).first():
                flash('E-mail já em uso por outro usuário.', 'danger')
            else:
                current_user.email = new_email
                db.session.commit()
                flash('E-mail atualizado com sucesso!', 'success')

    return render_template('user/settings.html')
