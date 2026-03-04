#!/usr/bin/env python3
"""
Bet Analyzer — Análise estatística + IA para apostas esportivas.

Uso:
    python main.py                  # Analisa jogos dos próximos 3 dias
    python main.py --days 7         # Próximos 7 dias
    python main.py --league PL      # Só Premier League
    python main.py --no-ai          # Sem análise de IA (só estatística)
    python main.py --bankroll 500   # Banca de 500
"""

import argparse
import sys
import os
from datetime import datetime
from tabulate import tabulate

# Adiciona o diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LEAGUES, BANKROLL, MIN_MATCHES_HISTORY, MIN_CONFIDENCE
from football_data_client import get_all_upcoming, get_upcoming_matches, get_season_matches
from odds_client import get_odds, extract_odds_for_match
from stats_engine import calc_team_stats, calc_league_averages, predict_match, calc_h2h_stats
from ai_analyzer import analyze_match
from value_bet import evaluate_bets, fair_odd


def print_header():
    print()
    print("=" * 65)
    print("       BET ANALYZER — Analise Estatistica + IA")
    print("=" * 65)
    print(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 65)
    print()


def print_match_report(match, prediction, ai_result, recommendations, odds_info):
    """Imprime relatório detalhado de um jogo."""
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]
    league = match.get("_league_name", "")
    date = match.get("utcDate", "")[:16].replace("T", " ")

    print()
    print("+" + "-" * 63 + "+")
    print(f"|  {home} vs {away}")
    print(f"|  {league} — {date} UTC")
    print("+" + "-" * 63 + "+")

    # Previsão estatística
    print(f"|  Gols esperados: {home[:15]} {prediction['lambda_home']:.2f} | {away[:15]} {prediction['lambda_away']:.2f}")
    print(f"|  Placar mais provavel: {prediction['most_likely_score']} ({prediction['most_likely_score_prob']:.1%})")
    print("|")

    # Tabela de probabilidades
    prob_table = [
        ["Over 2.5", f"{prediction['over_25']:.1%}", fair_odd(prediction['over_25']),
         odds_info.get('over_25', '-') if odds_info else '-'],
        ["Under 2.5", f"{prediction['under_25']:.1%}", fair_odd(prediction['under_25']),
         odds_info.get('under_25', '-') if odds_info else '-'],
        ["BTTS Sim", f"{prediction['btts_yes']:.1%}", fair_odd(prediction['btts_yes']),
         odds_info.get('btts_yes', '-') if odds_info else '-'],
        ["BTTS Nao", f"{prediction['btts_no']:.1%}", fair_odd(prediction['btts_no']),
         odds_info.get('btts_no', '-') if odds_info else '-'],
    ]
    print(tabulate(prob_table,
                   headers=["Mercado", "Prob.", "Odd Justa", "Odd Mercado"],
                   tablefmt="simple", stralign="center"))

    # Análise IA
    if ai_result:
        print()
        print(f"|  IA: {ai_result.get('analysis_summary', 'Sem resumo')}")
        factors = ai_result.get('key_factors', [])
        if factors:
            print("|  Fatores-chave:")
            for f in factors[:3]:
                print(f"|    - {f}")
        risks = ai_result.get('risk_factors', [])
        if risks:
            print("|  Riscos:")
            for r in risks[:2]:
                print(f"|    - {r}")

    # Recomendações de aposta
    if recommendations:
        print()
        print("|  >>> RECOMENDACOES <<<")
        for rec in recommendations:
            stars = "*" * rec['confidence']
            print(f"|")
            print(f"|  [{stars:5s}] {rec['market']}")
            print(f"|    Prob: {rec['probability']:.1%} | Odd mercado: {rec['market_odd']}")
            print(f"|    Edge: {rec['edge_pct']} | Stake: R${rec['stake']:.2f} ({rec['stake_pct']}%)")
    else:
        print("|")
        print("|  Sem value bets identificadas para este jogo.")

    print("+" + "-" * 63 + "+")


def analyze_league(league_code, days_ahead, use_ai, bankroll):
    """Analisa todos os jogos próximos de uma liga."""
    league_name = LEAGUES[league_code]["name"]
    print(f"\n{'='*50}")
    print(f"  {league_name}")
    print(f"{'='*50}")

    # 1. Buscar jogos agendados
    print(f"  Buscando proximos jogos ({days_ahead} dias)...")
    upcoming = get_upcoming_matches(league_code, days_ahead)

    if not upcoming:
        print("  Nenhum jogo encontrado.")
        return []

    print(f"  {len(upcoming)} jogo(s) encontrado(s).")

    # 2. Buscar histórico da temporada
    print("  Carregando historico da temporada...")
    season_matches = get_season_matches(league_code)
    league_avg = calc_league_averages(season_matches)
    print(f"  {league_avg['total_matches']} jogos no historico. "
          f"Media gols casa: {league_avg['home_avg']:.2f}, fora: {league_avg['away_avg']:.2f}")

    # 3. Buscar odds
    print("  Buscando odds...")
    odds_data = get_odds(league_code)

    all_recommendations = []

    # 4. Analisar cada jogo
    for match in upcoming:
        home = match["homeTeam"]["name"]
        away = match["awayTeam"]["name"]
        match["_league_code"] = league_code
        match["_league_name"] = league_name

        print(f"\n  Analisando: {home} vs {away}...")

        # Stats dos times
        home_stats = calc_team_stats(season_matches, home)
        away_stats = calc_team_stats(season_matches, away)

        if home_stats["total_matches"] < MIN_MATCHES_HISTORY:
            print(f"    Dados insuficientes para {home} ({home_stats['total_matches']} jogos). Pulando.")
            continue

        if away_stats["total_matches"] < MIN_MATCHES_HISTORY:
            print(f"    Dados insuficientes para {away} ({away_stats['total_matches']} jogos). Pulando.")
            continue

        # Previsão Poisson
        prediction = predict_match(home_stats, away_stats, league_avg)
        if not prediction:
            print("    Erro na previsao. Pulando.")
            continue

        # H2H
        h2h = calc_h2h_stats(season_matches, home, away)

        # Odds
        odds_info = None
        if odds_data:
            odds_info = extract_odds_for_match(odds_data, home, away)

        # IA
        ai_result = None
        if use_ai:
            print("    Consultando IA...")
            ai_result = analyze_match(match, prediction, odds_info)

        # Value bets
        recommendations = evaluate_bets(prediction, ai_result, odds_info, bankroll)

        # Relatório
        print_match_report(match, prediction, ai_result, recommendations, odds_info)

        for rec in recommendations:
            rec["match"] = f"{home} vs {away}"
            rec["league"] = league_name
        all_recommendations.extend(recommendations)

    return all_recommendations


def print_summary(all_recs, bankroll):
    """Imprime resumo final com todas as recomendações."""
    print("\n")
    print("=" * 65)
    print("       RESUMO — MELHORES VALUE BETS DO DIA")
    print("=" * 65)

    if not all_recs:
        print("  Nenhuma value bet encontrada hoje.")
        print("  Isso e normal — paciencia e disciplina sao parte da estrategia.")
        print("=" * 65)
        return

    # Ordenar por edge
    all_recs.sort(key=lambda x: x["edge"], reverse=True)

    table_data = []
    total_stake = 0
    for i, rec in enumerate(all_recs, 1):
        stars = "*" * rec["confidence"]
        table_data.append([
            i,
            rec["match"][:30],
            rec["league"][:10],
            rec["market"],
            f"{rec['probability']:.0%}",
            rec["market_odd"],
            rec["edge_pct"],
            f"R${rec['stake']:.0f}",
            stars,
        ])
        total_stake += rec["stake"]

    print(tabulate(
        table_data,
        headers=["#", "Jogo", "Liga", "Mercado", "Prob", "Odd", "Edge", "Stake", "Conf."],
        tablefmt="simple",
    ))

    print(f"\n  Total de apostas: {len(all_recs)}")
    print(f"  Stake total: R${total_stake:.2f} ({total_stake/bankroll*100:.1f}% da banca)")
    print(f"  Banca: R${bankroll:.2f}")
    print("=" * 65)
    print("  AVISO: Apostas envolvem risco. Use com responsabilidade.")
    print("  Este e um sistema de APOIO a decisao, nao garantia de lucro.")
    print("=" * 65)
    print()


def main():
    parser = argparse.ArgumentParser(description="Bet Analyzer — Analise estatistica + IA")
    parser.add_argument("--days", type=int, default=3, help="Dias a frente para buscar jogos (default: 3)")
    parser.add_argument("--league", type=str, default=None, help="Codigo da liga (PL, BL1, PD, SA, FL1)")
    parser.add_argument("--no-ai", action="store_true", help="Desabilitar analise de IA")
    parser.add_argument("--bankroll", type=float, default=BANKROLL, help=f"Valor da banca (default: {BANKROLL})")
    args = parser.parse_args()

    print_header()

    # Validar APIs
    from config import FOOTBALL_DATA_API_KEY, OPENROUTER_API_KEY, ODDS_API_KEY
    if not FOOTBALL_DATA_API_KEY:
        print("[ERRO] FOOTBALL_DATA_API_KEY nao configurada. Crie o arquivo bet/.env")
        sys.exit(1)
    if not args.no_ai and not OPENROUTER_API_KEY:
        print("[AVISO] OPENROUTER_API_KEY nao configurada. Rodando sem IA.")
        args.no_ai = True
    if not ODDS_API_KEY:
        print("[AVISO] ODDS_API_KEY nao configurada. Odds do mercado nao estarao disponiveis.")

    # Definir ligas
    if args.league:
        if args.league not in LEAGUES:
            print(f"[ERRO] Liga '{args.league}' nao reconhecida. Use: {', '.join(LEAGUES.keys())}")
            sys.exit(1)
        leagues_to_analyze = [args.league]
    else:
        leagues_to_analyze = list(LEAGUES.keys())

    # Executar análise
    all_recommendations = []
    for league_code in leagues_to_analyze:
        try:
            recs = analyze_league(league_code, args.days, not args.no_ai, args.bankroll)
            all_recommendations.extend(recs)
        except Exception as e:
            print(f"  [ERRO] Falha ao analisar {LEAGUES[league_code]['name']}: {e}")

    # Resumo final
    print_summary(all_recommendations, args.bankroll)


if __name__ == "__main__":
    main()
