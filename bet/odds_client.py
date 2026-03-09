"""Cliente para The Odds API."""

import requests
from config import ODDS_API_KEY, ODDS_SPORT_KEYS

BASE_URL = "https://api.the-odds-api.com/v4"


def _get(endpoint, params=None):
    """Request genérico."""
    url = f"{BASE_URL}{endpoint}"
    base_params = {"apiKey": ODDS_API_KEY}
    if params:
        base_params.update(params)
    resp = requests.get(url, params=base_params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_odds(league_code, markets="totals,btts"):
    """Busca odds para uma liga.

    markets: 'totals' para Over/Under, 'btts' para Both Teams To Score
    Regions: 'eu' para odds decimais

    Busca cada mercado separadamente para evitar erro 422 caso
    algum mercado não esteja disponível no plano atual da API.
    """
    sport_key = ODDS_SPORT_KEYS.get(league_code)
    if not sport_key:
        return []

    market_list = [m.strip() for m in markets.split(",")]
    merged = {}  # event_id -> event data

    for mkt in market_list:
        try:
            data = _get(
                f"/sports/{sport_key}/odds",
                params={
                    "regions": "eu",
                    "markets": mkt,
                    "oddsFormat": "decimal",
                },
            )
            for event in data:
                eid = event.get("id")
                if eid not in merged:
                    merged[eid] = event
                else:
                    # Mescla bookmakers/markets do novo request
                    _merge_bookmakers(merged[eid], event)
        except requests.exceptions.HTTPError as e:
            print(f"  [!] Mercado '{mkt}' indisponivel para {league_code}: {e}")
        except Exception as e:
            print(f"  [!] Erro ao buscar odds {league_code}/{mkt}: {e}")

    return list(merged.values())


def _merge_bookmakers(base_event, new_event):
    """Mescla bookmakers/markets de new_event no base_event."""
    existing = {bk["key"]: bk for bk in base_event.get("bookmakers", [])}
    for bk in new_event.get("bookmakers", []):
        if bk["key"] in existing:
            # Adiciona mercados novos ao bookmaker existente
            existing_mkt_keys = {m["key"] for m in existing[bk["key"]].get("markets", [])}
            for mkt in bk.get("markets", []):
                if mkt["key"] not in existing_mkt_keys:
                    existing[bk["key"]]["markets"].append(mkt)
        else:
            base_event.setdefault("bookmakers", []).append(bk)


def extract_odds_for_match(odds_data, home_team, away_team):
    """Extrai odds relevantes para um jogo específico.

    Faz match fuzzy pelos nomes dos times.
    """
    best_match = None
    best_score = 0

    for event in odds_data:
        # Match por similaridade nos nomes
        h_score = _fuzzy_match(event.get("home_team", ""), home_team)
        a_score = _fuzzy_match(event.get("away_team", ""), away_team)
        score = h_score + a_score
        if score > best_score:
            best_score = score
            best_match = event

    if not best_match or best_score < 1.0:
        return None

    result = {
        "home_team": best_match.get("home_team"),
        "away_team": best_match.get("away_team"),
        "commence_time": best_match.get("commence_time"),
        "over_25": None,
        "under_25": None,
        "btts_yes": None,
        "btts_no": None,
    }

    # Coleta TODAS as odds de todas as casas para calcular mediana
    all_odds = {"over_25": [], "under_25": [], "btts_yes": [], "btts_no": []}

    for bookmaker in best_match.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] == "totals":
                for outcome in market.get("outcomes", []):
                    if outcome.get("point") == 2.5:
                        if outcome["name"] == "Over":
                            all_odds["over_25"].append(outcome["price"])
                        elif outcome["name"] == "Under":
                            all_odds["under_25"].append(outcome["price"])

            elif market["key"] == "btts":
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == "Yes":
                        all_odds["btts_yes"].append(outcome["price"])
                    elif outcome["name"] == "No":
                        all_odds["btts_no"].append(outcome["price"])

    # Usa mediana para evitar outliers inflando o edge
    for key in all_odds:
        if all_odds[key]:
            result[key] = _median(all_odds[key])

    return result


def _median(values):
    """Calcula mediana de uma lista de valores."""
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return round((s[n // 2 - 1] + s[n // 2]) / 2, 2)


def _fuzzy_match(name1, name2):
    """Match simples entre nomes de times."""
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()

    if n1 == n2:
        return 1.0

    # Um contém o outro
    if n1 in n2 or n2 in n1:
        return 0.8

    # Palavras em comum
    words1 = set(n1.split())
    words2 = set(n2.split())
    common = words1 & words2
    if common:
        return len(common) / max(len(words1), len(words2))

    return 0.0


def get_all_odds(markets="totals,btts"):
    """Busca odds de todas as ligas configuradas."""
    all_odds = {}
    for league_code in ODDS_SPORT_KEYS:
        odds = get_odds(league_code, markets)
        if odds:
            all_odds[league_code] = odds
    return all_odds
