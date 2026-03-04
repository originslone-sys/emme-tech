"""Motor estatístico — Poisson, médias, forma, H2H."""

import math
from scipy.stats import poisson


def poisson_prob(lam, k):
    """Probabilidade de exatamente k gols dado lambda."""
    return poisson.pmf(k, lam)


def calc_team_stats(matches, team_name):
    """Calcula estatísticas ofensivas/defensivas de um time.

    Retorna dict com:
        goals_scored_avg, goals_conceded_avg (casa e fora separados),
        form (últimos 5 jogos: W/D/L),
        total_matches
    """
    home_scored, home_conceded, home_count = [], [], 0
    away_scored, away_conceded, away_count = [], [], 0
    form = []

    for m in matches:
        if m.get("status") != "FINISHED":
            continue

        home_team = m["homeTeam"]["name"]
        ft = m["score"]["fullTime"]
        h_goals = ft.get("home", 0) or 0
        a_goals = ft.get("away", 0) or 0

        if home_team == team_name:
            home_scored.append(h_goals)
            home_conceded.append(a_goals)
            home_count += 1
            if h_goals > a_goals:
                form.append("W")
            elif h_goals == a_goals:
                form.append("D")
            else:
                form.append("L")
        else:
            away_scored.append(a_goals)
            away_conceded.append(h_goals)
            away_count += 1
            if a_goals > h_goals:
                form.append("W")
            elif a_goals == h_goals:
                form.append("D")
            else:
                form.append("L")

    return {
        "home_scored_avg": sum(home_scored) / home_count if home_count else 0,
        "home_conceded_avg": sum(home_conceded) / home_count if home_count else 0,
        "away_scored_avg": sum(away_scored) / away_count if away_count else 0,
        "away_conceded_avg": sum(away_conceded) / away_count if away_count else 0,
        "home_matches": home_count,
        "away_matches": away_count,
        "total_matches": home_count + away_count,
        "form_last5": form[-5:] if form else [],
    }


def calc_league_averages(matches):
    """Calcula médias da liga: gols por jogo casa/fora."""
    home_goals, away_goals, count = 0, 0, 0

    for m in matches:
        if m.get("status") != "FINISHED":
            continue
        ft = m["score"]["fullTime"]
        home_goals += ft.get("home", 0) or 0
        away_goals += ft.get("away", 0) or 0
        count += 1

    if count == 0:
        return {"home_avg": 1.5, "away_avg": 1.2, "total_matches": 0}

    return {
        "home_avg": home_goals / count,
        "away_avg": away_goals / count,
        "total_matches": count,
    }


def predict_match(home_stats, away_stats, league_avg):
    """Gera previsão usando Poisson.

    Calcula lambda para cada time e gera matriz de probabilidades de placares.
    Retorna probabilidades para os mercados Over/Under 2.5 e BTTS.
    """
    if league_avg["home_avg"] == 0 or league_avg["away_avg"] == 0:
        return None

    # Attack/Defense strength
    home_attack = home_stats["home_scored_avg"] / league_avg["home_avg"]
    home_defense = home_stats["home_conceded_avg"] / league_avg["away_avg"]
    away_attack = away_stats["away_scored_avg"] / league_avg["away_avg"]
    away_defense = away_stats["away_conceded_avg"] / league_avg["home_avg"]

    # Expected goals (lambda)
    lambda_home = home_attack * away_defense * league_avg["home_avg"]
    lambda_away = away_attack * home_defense * league_avg["away_avg"]

    # Limitar lambdas a valores razoáveis
    lambda_home = max(0.2, min(lambda_home, 5.0))
    lambda_away = max(0.2, min(lambda_away, 5.0))

    # Matriz de placares (0-6 gols para cada time)
    max_goals = 7
    score_matrix = {}
    for i in range(max_goals):
        for j in range(max_goals):
            score_matrix[(i, j)] = poisson_prob(lambda_home, i) * poisson_prob(lambda_away, j)

    # Over/Under 2.5
    under_25 = sum(
        prob for (h, a), prob in score_matrix.items() if h + a < 3
    )
    over_25 = 1 - under_25

    # BTTS
    btts_no = sum(
        prob for (h, a), prob in score_matrix.items() if h == 0 or a == 0
    )
    btts_yes = 1 - btts_no

    # 1X2
    home_win = sum(prob for (h, a), prob in score_matrix.items() if h > a)
    draw = sum(prob for (h, a), prob in score_matrix.items() if h == a)
    away_win = sum(prob for (h, a), prob in score_matrix.items() if h < a)

    # Placar mais provável
    most_likely = max(score_matrix, key=score_matrix.get)

    return {
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "over_25": round(over_25, 4),
        "under_25": round(under_25, 4),
        "btts_yes": round(btts_yes, 4),
        "btts_no": round(btts_no, 4),
        "home_win": round(home_win, 4),
        "draw": round(draw, 4),
        "away_win": round(away_win, 4),
        "most_likely_score": f"{most_likely[0]}-{most_likely[1]}",
        "most_likely_score_prob": round(score_matrix[most_likely], 4),
    }


def calc_h2h_stats(matches, home_team, away_team):
    """Estatísticas de confronto direto."""
    h2h_matches = []
    for m in matches:
        if m.get("status") != "FINISHED":
            continue
        teams = {m["homeTeam"]["name"], m["awayTeam"]["name"]}
        if home_team in teams and away_team in teams:
            h2h_matches.append(m)

    if not h2h_matches:
        return {"count": 0, "over_25_pct": 0, "btts_pct": 0}

    over_25_count = 0
    btts_count = 0
    for m in h2h_matches:
        ft = m["score"]["fullTime"]
        h = ft.get("home", 0) or 0
        a = ft.get("away", 0) or 0
        if h + a > 2:
            over_25_count += 1
        if h > 0 and a > 0:
            btts_count += 1

    total = len(h2h_matches)
    return {
        "count": total,
        "over_25_pct": round(over_25_count / total, 4),
        "btts_pct": round(btts_count / total, 4),
    }
