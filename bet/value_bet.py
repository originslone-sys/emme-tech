"""Filtro de value bets e cálculo de Kelly criterion."""

import math
from config import MIN_EDGE, KELLY_FRACTION, MAX_STAKE_PCT, BANKROLL, MIN_CONFIDENCE

# Edge mínimo menor para mercados de alta probabilidade (over 1.5)
# porque a margem é menor mas a taxa de acerto compensa
MIN_EDGE_HIGH_PROB = 0.05


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


def _market_sanity_check(estimated_prob, market_odd, max_divergence=0.20):
    """Verifica se a probabilidade estimada não diverge demais do mercado.

    Se o modelo diz 70% mas o mercado (todas as casas) diz 45%,
    provavelmente o modelo está errado. O mercado incorpora informações
    (lesões, escalações, etc.) que o modelo não tem.
    """
    if not market_odd or market_odd <= 1:
        return True

    market_implied = implied_probability(market_odd)
    divergence = estimated_prob - market_implied
    return divergence <= max_divergence


def _ai_agrees(ai_analysis, market_type, stats_prob):
    """Verifica se a IA concorda com a direção da aposta.

    Retorna True se a IA concorda ou se não há análise IA.
    Retorna False se a IA contradiz claramente.
    """
    if not ai_analysis:
        return True

    if "over" in market_type:
        ai_val = ai_analysis.get("adjusted_over_25")
        if ai_val and isinstance(ai_val, (int, float)) and 0 < ai_val < 1:
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


def _evaluate_market(market_name, prob, odds_key, odds_info, ai_analysis,
                     ai_market_type, prediction_key, prediction, bankroll,
                     min_edge=MIN_EDGE, min_prob=0.0):
    """Avalia um mercado individual e retorna recomendação se aprovado."""
    odd = odds_info.get(odds_key)
    if not odd:
        return None

    edge = calculate_edge(prob, odd)
    if edge < min_edge:
        return None
    if not _market_sanity_check(prob, odd):
        return None
    if not _ai_agrees(ai_analysis, ai_market_type, prob):
        return None

    # Para mercados de alta probabilidade, exigir prob mínima
    if min_prob > 0 and prob < min_prob:
        return None

    confidence = _calc_confidence(edge, ai_analysis, ai_market_type, prob, prediction.get(prediction_key, prob))
    if confidence < MIN_CONFIDENCE:
        return None

    stake = kelly_stake(prob, odd, bankroll=bankroll)
    return {
        "market": market_name,
        "probability": round(prob, 4),
        "fair_odd": fair_odd(prob),
        "market_odd": odd,
        "edge": round(edge, 4),
        "edge_pct": f"{edge:.1%}",
        "stake": stake,
        "stake_pct": round(stake / bankroll * 100, 1) if bankroll else 0,
        "confidence": confidence,
        "is_value_bet": True,
    }


def evaluate_bets(prediction, ai_analysis, odds_info, bankroll=BANKROLL):
    """Avalia todos os mercados e retorna recomendações de aposta.

    Mercados avaliados:
    - Acima/Abaixo 1.5 Gols (alta taxa de acerto ~80%)
    - Acima/Abaixo 2.5 Gols (mercado clássico)
    - Acima/Abaixo 3.5 Gols (para jogos muito ofensivos)
    - BTTS Sim/Não
    """
    recommendations = []

    if not odds_info:
        return recommendations

    # Probabilidades base do modelo estatístico
    over_15_prob = prediction.get("over_15", 0)
    over_25_prob = prediction["over_25"]
    over_35_prob = prediction.get("over_35", 0)
    btts_prob = prediction["btts_yes"]

    # Ajuste conservador com IA (20% peso)
    if ai_analysis:
        ai_over = ai_analysis.get("adjusted_over_25")
        ai_btts = ai_analysis.get("adjusted_btts_yes")
        if ai_over and isinstance(ai_over, (int, float)) and 0 < ai_over < 1:
            over_25_prob = 0.80 * prediction["over_25"] + 0.20 * ai_over
            # Propagar ajuste proporcionalmente para 1.5 e 3.5
            if prediction["over_25"] > 0:
                ratio = over_25_prob / prediction["over_25"]
                over_15_prob = min(0.98, over_15_prob * (1 + (ratio - 1) * 0.5))
                over_35_prob = max(0.05, over_35_prob * (1 + (ratio - 1) * 1.5))
        if ai_btts and isinstance(ai_btts, (int, float)) and 0 < ai_btts < 1:
            btts_prob = 0.80 * prediction["btts_yes"] + 0.20 * ai_btts

    # === MERCADOS DE ALTA PROBABILIDADE (Acima 1.5) ===
    # Edge mínimo menor (5%), mas exige probabilidade >= 75%
    rec = _evaluate_market(
        "Acima 1.5 Gols", over_15_prob, "over_15", odds_info,
        ai_analysis, "over_15", "over_15", prediction, bankroll,
        min_edge=MIN_EDGE_HIGH_PROB, min_prob=0.75)
    if rec:
        recommendations.append(rec)

    rec = _evaluate_market(
        "Abaixo 1.5 Gols", 1 - over_15_prob, "under_15", odds_info,
        ai_analysis, "under_15", "under_15", prediction, bankroll)
    if rec:
        recommendations.append(rec)

    # === MERCADOS CLÁSSICOS (Acima/Abaixo 2.5) ===
    rec = _evaluate_market(
        "Acima 2.5 Gols", over_25_prob, "over_25", odds_info,
        ai_analysis, "over_25", "over_25", prediction, bankroll)
    if rec:
        recommendations.append(rec)

    rec = _evaluate_market(
        "Abaixo 2.5 Gols", 1 - over_25_prob, "under_25", odds_info,
        ai_analysis, "under_25", "under_25", prediction, bankroll)
    if rec:
        recommendations.append(rec)

    # === MERCADOS DE GOLEADA (Acima/Abaixo 3.5) ===
    # Só recomenda acima 3.5 se a probabilidade for forte (>55%)
    rec = _evaluate_market(
        "Acima 3.5 Gols", over_35_prob, "over_35", odds_info,
        ai_analysis, "over_35", "over_35", prediction, bankroll,
        min_prob=0.55)
    if rec:
        recommendations.append(rec)

    rec = _evaluate_market(
        "Abaixo 3.5 Gols", 1 - over_35_prob, "under_35", odds_info,
        ai_analysis, "under_35", "under_35", prediction, bankroll)
    if rec:
        recommendations.append(rec)

    # === BTTS ===
    rec = _evaluate_market(
        "BTTS Sim", btts_prob, "btts_yes", odds_info,
        ai_analysis, "btts", "btts_yes", prediction, bankroll)
    if rec:
        recommendations.append(rec)

    rec = _evaluate_market(
        "BTTS Nao", 1 - btts_prob, "btts_no", odds_info,
        ai_analysis, "btts_no", "btts_no", prediction, bankroll)
    if rec:
        recommendations.append(rec)

    # Ordenar por confiança primeiro, depois por edge
    recommendations.sort(key=lambda x: (x["confidence"], x["edge"]), reverse=True)
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

    # Probabilidade forte (>75% — modelo muito confiante)
    if final_prob > 0.75:
        stars += 1

    # Concordância da IA
    if ai_analysis:
        conf_key = "confidence_over_25" if "over" in market_type or "under" in market_type else "confidence_btts"
        ai_conf = ai_analysis.get(conf_key, "media")
        if ai_conf == "alta":
            stars += 1

    return min(stars, 5)
