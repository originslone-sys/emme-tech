"""Motor estatístico — Poisson com peso por recência, forma e H2H."""

import math
from scipy.stats import poisson


def poisson_prob(lam, k):
    """Probabilidade de exatamente k gols dado lambda."""
    return poisson.pmf(k, lam)


def _dixon_coles_correction(h, a, lambda_home, lambda_away, rho=-0.13):
    """Correção de Dixon-Coles para placares baixos.

    O modelo Poisson básico assume que gols de casa e fora são independentes.
    Na realidade, placares baixos (0-0, 1-0, 0-1, 1-1) são correlacionados.

    rho negativo (~-0.13) reflete que jogos reais têm MAIS empates 0-0 e 1-1
    e MENOS resultados 1-0 e 0-1 do que o Poisson puro prevê.

    Referência: Dixon & Coles (1997) — "Modelling Association Football Scores"
    """
    if h == 0 and a == 0:
        return 1 - lambda_home * lambda_away * rho
    elif h == 1 and a == 0:
        return 1 + lambda_away * rho
    elif h == 0 and a == 1:
        return 1 + lambda_home * rho
    elif h == 1 and a == 1:
        return 1 - rho
    return 1.0


def _recency_weights(n, decay=0.92):
    """Gera pesos exponenciais para n jogos (mais recente = maior peso).

    Com decay=0.92, os últimos 5 jogos pesam ~2x mais que os 5 mais antigos
    numa temporada de 30 jogos.
    """
    weights = [decay ** (n - 1 - i) for i in range(n)]
    total = sum(weights)
    return [w / total for w in weights]


def calc_team_stats(matches, team_name):
    """Calcula estatísticas ofensivas/defensivas de um time com peso por recência.

    Retorna dict com:
        goals_scored_avg, goals_conceded_avg (casa e fora separados),
        form (últimos 5 jogos: W/D/L),
        total_matches,
        recent_over25_pct, recent_btts_pct (últimos 10 jogos)
    """
    home_scored, home_conceded = [], []
    away_scored, away_conceded = [], []
    form = []
    recent_goals = []  # (total_gols, btts) dos últimos jogos

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
            if h_goals > a_goals:
                form.append("W")
            elif h_goals == a_goals:
                form.append("D")
            else:
                form.append("L")
            recent_goals.append((h_goals + a_goals, h_goals > 0 and a_goals > 0))
        elif m["awayTeam"]["name"] == team_name:
            away_scored.append(a_goals)
            away_conceded.append(h_goals)
            if a_goals > h_goals:
                form.append("W")
            elif a_goals == h_goals:
                form.append("D")
            else:
                form.append("L")
            recent_goals.append((h_goals + a_goals, h_goals > 0 and a_goals > 0))

    home_count = len(home_scored)
    away_count = len(away_scored)

    # Médias ponderadas por recência
    if home_count > 0:
        hw = _recency_weights(home_count)
        home_scored_avg = sum(g * w for g, w in zip(home_scored, hw))
        home_conceded_avg = sum(g * w for g, w in zip(home_conceded, hw))
    else:
        home_scored_avg = 0
        home_conceded_avg = 0

    if away_count > 0:
        aw = _recency_weights(away_count)
        away_scored_avg = sum(g * w for g, w in zip(away_scored, aw))
        away_conceded_avg = sum(g * w for g, w in zip(away_conceded, aw))
    else:
        away_scored_avg = 0
        away_conceded_avg = 0

    # Tendências recentes (últimos 10 jogos)
    last10 = recent_goals[-10:] if len(recent_goals) >= 5 else recent_goals
    recent_over25_pct = sum(1 for g, _ in last10 if g > 2) / len(last10) if last10 else 0
    recent_btts_pct = sum(1 for _, b in last10 if b) / len(last10) if last10 else 0

    # Forma recente — pontuação (W=3, D=1, L=0) normalizada
    form_last5 = form[-5:] if form else []
    form_points = sum(3 if r == "W" else 1 if r == "D" else 0 for r in form_last5)
    form_score = form_points / (len(form_last5) * 3) if form_last5 else 0.5

    return {
        "home_scored_avg": home_scored_avg,
        "home_conceded_avg": home_conceded_avg,
        "away_scored_avg": away_scored_avg,
        "away_conceded_avg": away_conceded_avg,
        "home_matches": home_count,
        "away_matches": away_count,
        "total_matches": home_count + away_count,
        "form_last5": form_last5,
        "form_score": form_score,
        "recent_over25_pct": round(recent_over25_pct, 4),
        "recent_btts_pct": round(recent_btts_pct, 4),
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


def predict_match(home_stats, away_stats, league_avg, h2h=None):
    """Gera previsão usando Poisson + ajustes de forma e H2H.

    1. Calcula lambda base via attack/defense strength (Poisson clássico)
    2. Ajusta pela forma recente dos times (±10%)
    3. Gera matriz de placares e probabilidades dos mercados
    4. Incorpora tendências recentes e H2H como correção final
    """
    if league_avg["home_avg"] == 0 or league_avg["away_avg"] == 0:
        return None

    # Attack/Defense strength
    home_attack = home_stats["home_scored_avg"] / league_avg["home_avg"]
    home_defense = home_stats["home_conceded_avg"] / league_avg["away_avg"]
    away_attack = away_stats["away_scored_avg"] / league_avg["away_avg"]
    away_defense = away_stats["away_conceded_avg"] / league_avg["home_avg"]

    # Expected goals (lambda) base
    lambda_home = home_attack * away_defense * league_avg["home_avg"]
    lambda_away = away_attack * home_defense * league_avg["away_avg"]

    # Ajuste pela forma recente (time em boa forma ataca ~5-10% mais)
    home_form_adj = 1.0 + (home_stats["form_score"] - 0.5) * 0.15
    away_form_adj = 1.0 + (away_stats["form_score"] - 0.5) * 0.15

    lambda_home *= home_form_adj
    lambda_away *= away_form_adj

    # Limitar lambdas a valores razoáveis
    lambda_home = max(0.3, min(lambda_home, 4.5))
    lambda_away = max(0.2, min(lambda_away, 4.0))

    # Matriz de placares com correção Dixon-Coles (0-6 gols para cada time)
    max_goals = 7
    score_matrix = {}
    for i in range(max_goals):
        for j in range(max_goals):
            base_prob = poisson_prob(lambda_home, i) * poisson_prob(lambda_away, j)
            dc_factor = _dixon_coles_correction(i, j, lambda_home, lambda_away)
            score_matrix[(i, j)] = base_prob * dc_factor

    # Normalizar para somar 1.0 (a correção pode alterar ligeiramente o total)
    total_prob = sum(score_matrix.values())
    if total_prob > 0:
        for key in score_matrix:
            score_matrix[key] /= total_prob

    # Over/Under 2.5
    under_25 = sum(
        prob for (h, a), prob in score_matrix.items() if h + a < 3
    )
    over_25_poisson = 1 - under_25

    # BTTS
    btts_no = sum(
        prob for (h, a), prob in score_matrix.items() if h == 0 or a == 0
    )
    btts_yes_poisson = 1 - btts_no

    # Ajustar com tendências recentes dos times (peso 25%)
    # Média das tendências recentes dos dois times
    avg_recent_over25 = (home_stats["recent_over25_pct"] + away_stats["recent_over25_pct"]) / 2
    avg_recent_btts = (home_stats["recent_btts_pct"] + away_stats["recent_btts_pct"]) / 2

    over_25 = 0.75 * over_25_poisson + 0.25 * avg_recent_over25
    btts_yes = 0.75 * btts_yes_poisson + 0.25 * avg_recent_btts

    # Ajustar com H2H se disponível (peso 10%, tira dos 75% do Poisson)
    if h2h and h2h["count"] >= 2:
        over_25 = 0.65 * over_25_poisson + 0.25 * avg_recent_over25 + 0.10 * h2h["over_25_pct"]
        btts_yes = 0.65 * btts_yes_poisson + 0.25 * avg_recent_btts + 0.10 * h2h["btts_pct"]

    # Garantir limites válidos
    over_25 = max(0.05, min(0.95, over_25))
    btts_yes = max(0.05, min(0.95, btts_yes))

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
        "under_25": round(1 - over_25, 4),
        "btts_yes": round(btts_yes, 4),
        "btts_no": round(1 - btts_yes, 4),
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
