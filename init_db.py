"""
init_db.py — Inicializa o banco com a Champions League 2025/26.

Execute UMA VEZ antes de iniciar o sistema:
    python init_db.py

Credenciais criadas:
  Admin:  usuario=admin     senha=admin123
  Jogadores de exemplo (todos com senha=ucl2026):
    pedro, ana, lucas, mariana, joao

Partidas carregadas:
  - Quartas de Final — 2a Mao  (14-15/04/2026)  <- proxima rodada
  - Semifinais — 1a e 2a Mao  (29/04 e 06/05/2026)
  - Final  (30/05/2026)
"""

from app import create_app
from app.models import db, User, Match
from datetime import datetime


# ── Champions League 2025/26 — a partir da proxima rodada ───────────────────
PARTIDAS_UCL = [
    # ── QUARTAS DE FINAL — 2ª Mão  (proximos jogos) ─────────────────────────
    #  Resultado da 1a mao entre parenteses para referencia do bolao
    #  Real Madrid 2-1 Arsenal (IDA)
    ("Arsenal",         "Real Madrid",      "2026-04-15 20:00", "Quartas - 2ª Mão", "Emirates Stadium, Londres"),
    #  PSG 1-1 Bayern Munich (IDA)
    ("PSG",             "Bayern Munich",    "2026-04-15 20:00", "Quartas - 2ª Mão", "Parc des Princes, Paris"),
    #  Barcelona 0-2 Manchester City (IDA)
    ("Manchester City", "Barcelona",        "2026-04-14 20:00", "Quartas - 2ª Mão", "Etihad Stadium, Manchester"),
    #  Liverpool 3-1 Inter Milan (IDA)
    ("Inter Milan",     "Liverpool",        "2026-04-14 20:00", "Quartas - 2ª Mão", "San Siro, Milao"),

    # ── SEMIFINAIS — 1ª Mão ─────────────────────────────────────────────────
    ("Venc. QF1",       "Venc. QF4",        "2026-04-29 20:00", "Semifinal - 1ª Mão", "A definir"),
    ("Venc. QF2",       "Venc. QF3",        "2026-04-30 20:00", "Semifinal - 1ª Mão", "A definir"),

    # ── SEMIFINAIS — 2ª Mão ─────────────────────────────────────────────────
    ("Venc. QF4",       "Venc. QF1",        "2026-05-06 20:00", "Semifinal - 2ª Mão", "A definir"),
    ("Venc. QF3",       "Venc. QF2",        "2026-05-07 20:00", "Semifinal - 2ª Mão", "A definir"),

    # ── FINAL ────────────────────────────────────────────────────────────────
    ("Venc. SF1",       "Venc. SF2",        "2026-05-30 19:00", "Final", "Wembley, Londres"),
]


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        if User.query.count() > 0:
            print("[AVISO] Banco ja populado. Nada foi alterado.")
            print("        Para resetar, delete 'instance/ucl2526.db' e rode novamente.")
            return

        # ── Admin ─────────────────────────────────────────────────────────────
        admin = User(username='admin', email='admin@ucl2526.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)

        # ── Participantes de exemplo ──────────────────────────────────────────
        exemplos = [
            ('pedro',   'pedro@email.com'),
            ('ana',     'ana@email.com'),
            ('lucas',   'lucas@email.com'),
            ('mariana', 'mariana@email.com'),
            ('joao',    'joao@email.com'),
        ]
        for username, email in exemplos:
            u = User(username=username, email=email, role='user')
            u.set_password('ucl2026')
            db.session.add(u)

        # ── Partidas ──────────────────────────────────────────────────────────
        for home, away, dt_str, stage, venue in PARTIDAS_UCL:
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
            match = Match(
                home_team=home,
                away_team=away,
                match_datetime=dt,
                stage=stage,
                venue=venue,
            )
            db.session.add(match)

        db.session.commit()

        total_m = Match.query.count()
        total_u = User.query.filter_by(role='user').count()

        print("=" * 60)
        print("  [OK] Banco inicializado — Champions League 2025/26")
        print("=" * 60)
        print(f"  [ADMIN] Admin:         admin / admin123")
        print(f"  [USER]  Participantes: {total_u} usuarios (senha: ucl2026)")
        print(f"  [JOG]   Partidas:      {total_m} cadastradas")
        print("=" * 60)
        print("  Proxima rodada: Quartas - 2a Mao (14-15/04/2026)")
        print("=" * 60)
        print("  Acesse: http://localhost:5000")
        print("=" * 60)


if __name__ == '__main__':
    seed()
