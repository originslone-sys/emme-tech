"""Filtro de value bets e cálculo de Kelly criterion."""

import math
from config import MIN_EDGE, KELLY_FRACTION, MAX_STAKE_PCT, BANKROLL


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


def evaluate_bets(prediction, ai_analysis, odds_info, bankroll=BANKROLL):
    """Avalia todos os mercados e retorna recomendações de aposta.

    Combina predição estatística + ajuste da IA.
    """
    recommendations = []

    if not odds_info:
        return recommendations

    # Probabilidades finais (média ponderada: 60% stats, 40% IA se disponível)
    over_25_prob = prediction["over_25"]
    btts_prob = prediction["btts_yes"]

    if ai_analysis:
        ai_over = ai_analysis.get("adjusted_over_25")
        ai_btts = ai_analysis.get("adjusted_btts_yes")
        if ai_over and isinstance(ai_over, (int, float)) and 0 < ai_over < 1:
            over_25_prob = 0.6 * prediction["over_25"] + 0.4 * ai_over
        if ai_btts and isinstance(ai_btts, (int, float)) and 0 < ai_btts < 1:
            btts_prob = 0.6 * prediction["btts_yes"] + 0.4 * ai_btts

    # Avaliar Over 2.5
    if odds_info.get("over_25"):
        edge = calculate_edge(over_25_prob, odds_info["over_25"])
        if edge >= MIN_EDGE:
            stake = kelly_stake(over_25_prob, odds_info["over_25"], bankroll=bankroll)
            confidence = _calc_confidence(edge, ai_analysis, "over_25")
            recommendations.append({
                "market": "Over 2.5 Gols",
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

    # Avaliar Under 2.5
    under_prob = 1 - over_25_prob
    if odds_info.get("under_25"):
        edge = calculate_edge(under_prob, odds_info["under_25"])
        if edge >= MIN_EDGE:
            stake = kelly_stake(under_prob, odds_info["under_25"], bankroll=bankroll)
            confidence = _calc_confidence(edge, ai_analysis, "under_25")
            recommendations.append({
                "market": "Under 2.5 Gols",
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
        if edge >= MIN_EDGE:
            stake = kelly_stake(btts_prob, odds_info["btts_yes"], bankroll=bankroll)
            confidence = _calc_confidence(edge, ai_analysis, "btts")
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

    # Avaliar BTTS Não
    btts_no_prob = 1 - btts_prob
    if odds_info.get("btts_no"):
        edge = calculate_edge(btts_no_prob, odds_info["btts_no"])
        if edge >= MIN_EDGE:
            stake = kelly_stake(btts_no_prob, odds_info["btts_no"], bankroll=bankroll)
            confidence = _calc_confidence(edge, ai_analysis, "btts")
            recommendations.append({
                "market": "BTTS Não",
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


def _calc_confidence(edge, ai_analysis, market_type):
    """Calcula nível de confiança (1-5 estrelas)."""
    stars = 1

    # Base no edge
    if edge >= 0.15:
        stars += 2
    elif edge >= 0.10:
        stars += 1

    # Boost da confiança da IA
    if ai_analysis:
        conf_key = "confidence_over_25" if "over" in market_type or "under" in market_type else "confidence_btts"
        ai_conf = ai_analysis.get(conf_key, "media")
        if ai_conf == "alta":
            stars += 2
        elif ai_conf == "media":
            stars += 1

    return min(stars, 5)
