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

from config import LEAGUES, BANKROLL, MIN_MATCHES_HISTORY, MIN_MATCHES_SHORT, MIN_CONFIDENCE, SHORT_COMPETITIONS
from football_data_client import get_all_upcoming, get_upcoming_matches, get_season_matches
from odds_client import get_odds, extract_odds_for_match
from stats_engine import calc_team_stats, calc_league_averages, predict_match, calc_h2h_stats
from ai_analyzer import analyze_match
from value_bet import evaluate_bets, fair_odd

# Cores ANSI para terminal
GREEN = "\033[92m"
BOLD_GREEN = "\033[1;92m"
YELLOW = "\033[93m"
BOLD_YELLOW = "\033[1;93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
BG_GREEN = "\033[42;97m"
BG_YELLOW = "\033[43;30m"


def print_header():
    print()
    print("=" * 65)
    print("       BET ANALYZER — Analise Estatistica + IA")
    print("=" * 65)
    print(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 65)
    print()


def _edge_color(edge):
    """Retorna cor baseada no edge."""
    if edge >= 0.15:
        return BOLD_GREEN
    elif edge >= 0.10:
        return GREEN
    elif edge >= 0.05:
        return YELLOW
    return DIM


def _confidence_bar(confidence):
    """Retorna barra visual de confiança."""
    filled = confidence
    empty = 5 - confidence
    if confidence >= 4:
        color = BOLD_GREEN
    elif confidence >= 3:
        color = GREEN
    else:
        color = YELLOW
    return f"{color}{'█' * filled}{'░' * empty}{RESET}"


def print_match_report(match, prediction, ai_result, recommendations, odds_info):
    """Imprime relatório detalhado de um jogo."""
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]
    league = match.get("_league_name", "")
    date = match.get("utcDate", "")[:16].replace("T", " ")

    has_value = bool(recommendations)
    border_color = BOLD_GREEN if has_value else DIM

    print()
    print(f"{border_color}+{'-' * 63}+{RESET}")
    if has_value:
        print(f"{border_color}|  {BG_GREEN} APOSTAR {RESET}  {BOLD}{home} vs {away}{RESET}")
    else:
        print(f"{border_color}|{RESET}  {home} vs {away}")
    print(f"{border_color}|{RESET}  {league} — {date} UTC")
    print(f"{border_color}+{'-' * 63}+{RESET}")

    # Previsão estatística
    print(f"|  Gols esperados: {home[:15]} {prediction['lambda_home']:.2f} | {away[:15]} {prediction['lambda_away']:.2f}")
    print(f"|  Placar mais provavel: {prediction['most_likely_score']} ({prediction['most_likely_score_prob']:.1%})")
    print("|")

    # Tabela de probabilidades — destacar mercados com value
    value_markets = {rec['market'] for rec in recommendations} if recommendations else set()
    market_map = {
        "Acima 1.5 Gols": "Acima 1.5", "Abaixo 1.5 Gols": "Abaixo 1.5",
        "Acima 2.5 Gols": "Acima 2.5", "Abaixo 2.5 Gols": "Abaixo 2.5",
        "Acima 3.5 Gols": "Acima 3.5", "Abaixo 3.5 Gols": "Abaixo 3.5",
        "BTTS Sim": "BTTS Sim", "BTTS Nao": "BTTS Nao",
    }
    value_labels = set()
    for vm in value_markets:
        value_labels.add(market_map.get(vm, vm))

    rows = [
        ("Acima 1.5", prediction.get('over_15', 0), odds_info.get('over_15') if odds_info else None),
        ("Abaixo 1.5", prediction.get('under_15', 0), odds_info.get('under_15') if odds_info else None),
        ("Acima 2.5", prediction['over_25'], odds_info.get('over_25') if odds_info else None),
        ("Abaixo 2.5", prediction['under_25'], odds_info.get('under_25') if odds_info else None),
        ("Acima 3.5", prediction.get('over_35', 0), odds_info.get('over_35') if odds_info else None),
        ("Abaixo 3.5", prediction.get('under_35', 0), odds_info.get('under_35') if odds_info else None),
        ("BTTS Sim", prediction['btts_yes'], odds_info.get('btts_yes') if odds_info else None),
        ("BTTS Nao", prediction['btts_no'], odds_info.get('btts_no') if odds_info else None),
    ]

    prob_table = []
    for label, prob, mkt_odd in rows:
        is_value = label in value_labels
        color = GREEN if is_value else ""
        reset = RESET if is_value else ""
        marker = f"{BOLD_GREEN} <<< VALUE{RESET}" if is_value else ""
        odd_display = mkt_odd if mkt_odd else "-"
        prob_table.append([
            f"{color}{label}{reset}",
            f"{color}{prob:.1%}{reset}",
            f"{color}{fair_odd(prob)}{reset}",
            f"{color}{odd_display}{reset}{marker}",
        ])

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
        print(f"|  {BOLD_GREEN}>>> APOSTAR <<<{RESET}")
        for rec in recommendations:
            edge_c = _edge_color(rec['edge'])
            conf_bar = _confidence_bar(rec['confidence'])
            print(f"|")
            print(f"|  {GREEN}>> {BOLD_GREEN}{rec['market']}{RESET}")
            print(f"|     Prob: {rec['probability']:.1%} | Odd mercado: {BOLD}{rec['market_odd']}{RESET}")
            print(f"|     Edge: {edge_c}{rec['edge_pct']}{RESET} | Confianca: {conf_bar}")
            print(f"|     {BOLD_GREEN}Stake: R${rec['stake']:.2f} ({rec['stake_pct']}% da banca){RESET}")
    else:
        print("|")
        print(f"|  {DIM}Sem value bets identificadas para este jogo.{RESET}")

    print(f"{border_color}+{'-' * 63}+{RESET}")


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

    # Determinar mínimo de jogos com base na competição
    # Cups/competições curtas ou início de temporada usam limite menor
    min_matches = MIN_MATCHES_SHORT if league_code in SHORT_COMPETITIONS else MIN_MATCHES_HISTORY
    # Se a liga tem poucos jogos (início de temporada), reduzir o mínimo
    if league_avg["total_matches"] < 80 and min_matches == MIN_MATCHES_HISTORY:
        min_matches = MIN_MATCHES_SHORT
        print(f"  [!] Inicio de temporada detectado — minimo reduzido para {min_matches} jogos.")

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

        if home_stats["total_matches"] < min_matches:
            print(f"    Dados insuficientes para {home} ({home_stats['total_matches']} jogos, minimo: {min_matches}). Pulando.")
            continue

        if away_stats["total_matches"] < min_matches:
            print(f"    Dados insuficientes para {away} ({away_stats['total_matches']} jogos, minimo: {min_matches}). Pulando.")
            continue

        # H2H
        h2h = calc_h2h_stats(season_matches, home, away)

        # Previsão Poisson + forma + H2H
        prediction = predict_match(home_stats, away_stats, league_avg, h2h)
        if not prediction:
            print("    Erro na previsao. Pulando.")
            continue

        # Odds
        odds_info = None
        if odds_data:
            odds_info = extract_odds_for_match(odds_data, home, away, league_code=league_code)

        # IA
        ai_result = None
        if use_ai:
            print("    Consultando IA...")
            ai_result = analyze_match(match, prediction, odds_info)

        # Value bets
        recommendations = evaluate_bets(prediction, ai_result, odds_info, bankroll)

        # Relatório
        print_match_report(match, prediction, ai_result, recommendations, odds_info)

        match_date = match.get("utcDate", "")[:16].replace("T", " ")
        for rec in recommendations:
            rec["match"] = f"{home} vs {away}"
            rec["league"] = league_name
            rec["date"] = match_date
        all_recommendations.extend(recommendations)

    return all_recommendations


def print_summary(all_recs, bankroll):
    """Imprime resumo final com todas as recomendações."""
    print("\n")
    print(f"{BOLD_GREEN}{'=' * 65}{RESET}")
    print(f"{BOLD_GREEN}  {'$' * 3}  RESUMO — APOSTAS RECOMENDADAS  {'$' * 3}{RESET}")
    print(f"{BOLD_GREEN}{'=' * 65}{RESET}")

    if not all_recs:
        print()
        print(f"  {DIM}Nenhuma value bet encontrada hoje.{RESET}")
        print(f"  {DIM}Isso e normal — paciencia e disciplina sao parte da estrategia.{RESET}")
        print(f"{DIM}{'=' * 65}{RESET}")
        return

    # Ordenar por confiança > probabilidade (apostas mais seguras primeiro)
    all_recs.sort(key=lambda x: (x["confidence"], x["probability"]), reverse=True)

    # Limitar apostas para não ultrapassar a banca
    selected = []
    total_stake = 0
    for rec in all_recs:
        if total_stake + rec["stake"] > bankroll * 0.50:
            # Máximo 50% da banca em apostas simultâneas
            continue
        selected.append(rec)
        total_stake += rec["stake"]
        if len(selected) >= 10:
            break

    # Imprimir cada aposta de forma clara
    for i, rec in enumerate(selected, 1):
        edge_c = _edge_color(rec["edge"])
        conf_bar = _confidence_bar(rec["confidence"])

        print()
        print(f"  {BOLD_GREEN}[{i}] {rec['match']}{RESET}")
        print(f"      {DIM}{rec['league']} — {rec.get('date', 'N/A')} UTC{RESET}")
        print(f"      Mercado:   {BOLD_GREEN}{rec['market']}{RESET}")
        print(f"      Prob:      {rec['probability']:.1%}  |  Odd Justa: {rec['fair_odd']}")
        print(f"      Odd:       {BOLD}{rec['market_odd']}{RESET}")
        print(f"      Edge:      {edge_c}{rec['edge_pct']}{RESET}")
        print(f"      Confianca: {conf_bar}")
        print(f"      {BG_GREEN} STAKE: R${rec['stake']:.2f} ({rec['stake_pct']}% da banca) {RESET}")

    total_stake = sum(r["stake"] for r in selected)

    if len(selected) < len(all_recs):
        print(f"\n  {DIM}({len(all_recs) - len(selected)} apostas adicionais omitidas — limite de banca){RESET}")

    # Rodapé resumo
    print()
    print(f"{BOLD_GREEN}{'-' * 65}{RESET}")
    print(f"  {BOLD}Total de apostas:  {BOLD_GREEN}{len(selected)}{RESET}")
    print(f"  {BOLD}Stake total:       {BOLD_GREEN}R${total_stake:.2f}{RESET} ({total_stake/bankroll*100:.1f}% da banca)")
    print(f"  {BOLD}Banca disponivel:  {RESET}R${bankroll:.2f}")
    print(f"  {BOLD}Banca restante:    {RESET}R${bankroll - total_stake:.2f}")
    print(f"{BOLD_GREEN}{'-' * 65}{RESET}")
    print()
    print(f"  {YELLOW}AVISO: Apostas envolvem risco. Use com responsabilidade.{RESET}")
    print(f"  {DIM}Este e um sistema de APOIO a decisao, nao garantia de lucro.{RESET}")
    print(f"{BOLD_GREEN}{'=' * 65}{RESET}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Bet Analyzer — Analise estatistica + IA")
    parser.add_argument("--days", type=int, default=3, help="Dias a frente para buscar jogos (default: 3)")
    parser.add_argument("--league", type=str, default=None, help="Codigo da liga (PL, BL1, PD, SA, FL1, BSA, CL, WC, EC)")
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
