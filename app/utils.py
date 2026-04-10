from datetime import datetime


def calculate_points(pred_home: int, pred_away: int, real_home: int, real_away: int) -> int:
    """
    Calcula pontuação conforme as regras:
      10 — Placar Exato
       7 — Resultado + Gols de um dos times
       5 — Resultado Seco (vencedor/empate correto)
       2 — Gols de um time correto, mas resultado errado
       0 — Erro Total
    """
    # Placar Exato
    if pred_home == real_home and pred_away == real_away:
        return 10

    def result(h, a):
        if h > a:
            return 'H'
        if a > h:
            return 'A'
        return 'D'

    pred_result = result(pred_home, pred_away)
    real_result = result(real_home, real_away)

    correct_result = pred_result == real_result
    correct_home = pred_home == real_home
    correct_away = pred_away == real_away

    # Resultado + Gols de um time
    if correct_result and (correct_home or correct_away):
        return 7

    # Resultado Seco
    if correct_result:
        return 5

    # Gols de um time
    if correct_home or correct_away:
        return 2

    return 0


def format_dt(dt: datetime) -> str:
    if dt is None:
        return '—'
    return dt.strftime('%d/%m/%Y %H:%M')


def format_dt_full(dt: datetime) -> str:
    if dt is None:
        return '—'
    return dt.strftime('%d/%m/%Y %H:%M:%S')
