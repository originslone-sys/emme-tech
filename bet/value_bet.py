"""Filtro de value bets e cálculo de Kelly criterion."""

import math
from config import MIN_EDGE, KELLY_FRACTION, MAX_STAKE_PCT, BANKROLL, MIN_CONFIDENCE


def implied_probability(odd):
    """Converte odd decimal em probabilidade implícita."""
    if odd and odd > 1:
        return 1.0 / odd
    return 0.0


def fair_odd(probability):
    """Converte probabilidade em odd justa (sem margem)."""
    if probability > 0:
        return round(1.0 / probability, 2)
    return 0.0


def calculate_edge(estimated_prob, market_odd):
    """Calcula o edge (vantagem) sobre a casa.

    Edge = (prob_estimada * odd_mercado) - 1
    Se positivo, há value.
    """
    if not market_odd or market_odd <= 1:
        return 0.0
    return (estimated_prob * market_odd) - 1


def kelly_stake(probability, odd, fraction=KELLY_FRACTION, bankroll=BANKROLL):
    """Calcula stake via Kelly Criterion fracionado.

    Kelly = (bp - q) / b
    Onde:
        b = odd - 1 (lucro líquido por unidade)
        p = probabilidade estimada
        q = 1 - p
    """
    if odd <= 1 or probability <= 0 or probability >= 1:
        return 0.0

    b = odd - 1
    p = probability
    q = 1 - p

    kelly = (b * p - q) / b
    if kelly <= 0:
        return 0.0

    # Aplica fração de Kelly e limita ao máximo
    stake_pct = kelly * fraction
    stake_pct = min(stake_pct, MAX_STAKE_PCT)

    return round(stake_pct * bankroll, 2)


def _ai_agrees(ai_analysis, market_type, stats_prob):
    """Verifica se a IA concorda com a direção da aposta.

    Retorna True se a IA concorda ou se não há análise IA.
    Retorna False se a IA contradiz claramente.
    """
    if not ai_analysis:
        return True  # Sem IA, usa só stats

    if "over" in market_type:
        ai_val = ai_analysis.get("adjusted_over_25")
        if ai_val and isinstance(ai_val, (int, float)) and 0 < ai_val < 1:
            # IA contradiz se está >10pp abaixo da estatística
            if ai_val < stats_prob - 0.10:
                return False
    elif "under" in market_type:
        ai_val = ai_analysis.get("adjusted_over_25")
        if ai_val and isinstance(ai_val, (int, float)) and 0 < ai_val < 1:
            ai_under = 1 - ai_val
            if ai_under < stats_prob - 0.10:
                return False
    elif market_type == "btts":
        ai_val = ai_analysis.get("adjusted_btts_yes")
        if ai_val and isinstance(ai_val, (int, float)) and 0 < ai_val < 1:
            if ai_val < stats_prob - 0.10:
                return False
    elif market_type == "btts_no":
        ai_val = ai_analysis.get("adjusted_btts_yes")
        if ai_val and isinstance(ai_val, (int, float)) and 0 < ai_val < 1:
            ai_no = 1 - ai_val
            if ai_no < stats_prob - 0.10:
                return False

    return True


def evaluate_bets(prediction, ai_analysis, odds_info, bankroll=BANKROLL):
    """Avalia todos os mercados e retorna recomendações de aposta.

    Combina predição estatística + ajuste conservador da IA.
    Filtra por convergência (stats e IA devem concordar).
    """
    recommendations = []

    if not odds_info:
        return recommendations

    # Probabilidades finais (80% stats, 20% IA — IA é complemento, não driver)
    over_25_prob = prediction["over_25"]
    btts_prob = prediction["btts_yes"]

    if ai_analysis:
        ai_over = ai_analysis.get("adjusted_over_25")
        ai_btts = ai_analysis.get("adjusted_btts_yes")
        if ai_over and isinstance(ai_over, (int, float)) and 0 < ai_over < 1:
            over_25_prob = 0.80 * prediction["over_25"] + 0.20 * ai_over
        if ai_btts and isinstance(ai_btts, (int, float)) and 0 < ai_btts < 1:
            btts_prob = 0.80 * prediction["btts_yes"] + 0.20 * ai_btts

    # Avaliar Acima 2.5
    if odds_info.get("over_25"):
        edge = calculate_edge(over_25_prob, odds_info["over_25"])
        if edge >= MIN_EDGE and _ai_agrees(ai_analysis, "over_25", over_25_prob):
            confidence = _calc_confidence(edge, ai_analysis, "over_25", over_25_prob, prediction["over_25"])
            if confidence >= MIN_CONFIDENCE:
                stake = kelly_stake(over_25_prob, odds_info["over_25"], bankroll=bankroll)
                recommendations.append({
                    "market": "Acima 2.5 Gols",
                    "probability": round(over_25_prob, 4),
                    "fair_odd": fair_odd(over_25_prob),
                    "market_odd": odds_info["over_25"],
                    "edge": round(edge, 4),
                    "edge_pct": f"{edge:.1%}",
                    "stake": stake,
                    "stake_pct": round(stake / bankroll * 100, 1) if bankroll else 0,
                    "confidence": confidence,
                    "is_value_bet": True,
                })

    # Avaliar Abaixo 2.5
    under_prob = 1 - over_25_prob
    if odds_info.get("under_25"):
        edge = calculate_edge(under_prob, odds_info["under_25"])
        if edge >= MIN_EDGE and _ai_agrees(ai_analysis, "under_25", under_prob):
            confidence = _calc_confidence(edge, ai_analysis, "under_25", under_prob, prediction["under_25"])
            if confidence >= MIN_CONFIDENCE:
                stake = kelly_stake(under_prob, odds_info["under_25"], bankroll=bankroll)
                recommendations.append({
                    "market": "Abaixo 2.5 Gols",
                    "probability": round(under_prob, 4),
                    "fair_odd": fair_odd(under_prob),
                    "market_odd": odds_info["under_25"],
                    "edge": round(edge, 4),
                    "edge_pct": f"{edge:.1%}",
                    "stake": stake,
                    "stake_pct": round(stake / bankroll * 100, 1) if bankroll else 0,
                    "confidence": confidence,
                    "is_value_bet": True,
                })

    # Avaliar BTTS Sim
    if odds_info.get("btts_yes"):
        edge = calculate_edge(btts_prob, odds_info["btts_yes"])
        if edge >= MIN_EDGE and _ai_agrees(ai_analysis, "btts", btts_prob):
            confidence = _calc_confidence(edge, ai_analysis, "btts", btts_prob, prediction["btts_yes"])
            if confidence >= MIN_CONFIDENCE:
                stake = kelly_stake(btts_prob, odds_info["btts_yes"], bankroll=bankroll)
                recommendations.append({
                    "market": "BTTS Sim",
                    "probability": round(btts_prob, 4),
                    "fair_odd": fair_odd(btts_prob),
                    "market_odd": odds_info["btts_yes"],
                    "edge": round(edge, 4),
                    "edge_pct": f"{edge:.1%}",
                    "stake": stake,
                    "stake_pct": round(stake / bankroll * 100, 1) if bankroll else 0,
                    "confidence": confidence,
                    "is_value_bet": True,
                })

    # Avaliar BTTS Nao
    btts_no_prob = 1 - btts_prob
    if odds_info.get("btts_no"):
        edge = calculate_edge(btts_no_prob, odds_info["btts_no"])
        if edge >= MIN_EDGE and _ai_agrees(ai_analysis, "btts_no", btts_no_prob):
            confidence = _calc_confidence(edge, ai_analysis, "btts_no", btts_no_prob, prediction["btts_no"])
            if confidence >= MIN_CONFIDENCE:
                stake = kelly_stake(btts_no_prob, odds_info["btts_no"], bankroll=bankroll)
                recommendations.append({
                    "market": "BTTS Nao",
                    "probability": round(btts_no_prob, 4),
                    "fair_odd": fair_odd(btts_no_prob),
                    "market_odd": odds_info["btts_no"],
                    "edge": round(edge, 4),
                    "edge_pct": f"{edge:.1%}",
                    "stake": stake,
                    "stake_pct": round(stake / bankroll * 100, 1) if bankroll else 0,
                    "confidence": confidence,
                    "is_value_bet": True,
                })

    # Ordenar por edge
    recommendations.sort(key=lambda x: x["edge"], reverse=True)
    return recommendations


def _calc_confidence(edge, ai_analysis, market_type, final_prob, stats_prob):
    """Calcula nível de confiança (1-5 estrelas).

    Leva em conta: edge, concordância IA, e força da probabilidade.
    """
    stars = 1

    # Base no edge (critério mais importante)
    if edge >= 0.20:
        stars += 2
    elif edge >= 0.12:
        stars += 1

    # Probabilidade forte (>65% ou <35% — o modelo tem convicção clara)
    if final_prob > 0.65 or final_prob < 0.35:
        stars += 1

    # Concordância da IA
    if ai_analysis:
        conf_key = "confidence_over_25" if "over" in market_type or "under" in market_type else "confidence_btts"
        ai_conf = ai_analysis.get(conf_key, "media")
        if ai_conf == "alta":
            stars += 1

    return min(stars, 5)
