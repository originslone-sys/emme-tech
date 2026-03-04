"""Cliente para football-data.org API."""

import requests
from config import FOOTBALL_DATA_API_KEY, LEAGUES

BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}


def _get(endpoint, params=None):
    """Request genérico com tratamento de erro e debug."""
    url = f"{BASE_URL}{endpoint}"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    if not resp.ok:
        print(f"    [DEBUG] {resp.status_code} - {resp.text[:200]}")
    resp.raise_for_status()
    return resp.json()


def get_upcoming_matches(league_code, days_ahead=3):
    """Busca próximos jogos de uma liga nos próximos N dias."""
    from datetime import datetime, timedelta

    date_from = datetime.utcnow().strftime("%Y-%m-%d")
    date_to = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # Busca sem filtro de status (free tier não suporta combinação)
    # Filtra localmente por jogos ainda não realizados
    data = _get(
        f"/competitions/{league_code}/matches",
        params={"dateFrom": date_from, "dateTo": date_to},
    )
    matches = data.get("matches", [])
    # Filtrar apenas jogos agendados/não finalizados
    return [m for m in matches if m.get("status") in ("SCHEDULED", "TIMED")]


def get_season_matches(league_code, status="FINISHED"):
    """Busca todos os jogos finalizados da temporada atual."""
    # Tenta com status, se falhar busca tudo e filtra local
    try:
        data = _get(
            f"/competitions/{league_code}/matches",
            params={"status": status},
        )
        return data.get("matches", [])
    except requests.exceptions.HTTPError:
        data = _get(f"/competitions/{league_code}/matches")
        matches = data.get("matches", [])
        return [m for m in matches if m.get("status") == status]


def get_team_matches(team_id, limit=15):
    """Busca últimos jogos de um time específico."""
    data = _get(
        f"/teams/{team_id}/matches",
        params={"status": "FINISHED", "limit": limit},
    )
    return data.get("matches", [])


def get_head_to_head(match_id):
    """Busca confronto direto via match endpoint."""
    data = _get(f"/matches/{match_id}")
    h2h = data.get("head2head", {})
    return h2h


def get_standings(league_code):
    """Busca classificação atual da liga."""
    data = _get(f"/competitions/{league_code}/standings")
    standings = data.get("standings", [])
    if standings:
        return standings[0].get("table", [])
    return []


def get_all_upcoming(days_ahead=3):
    """Busca próximos jogos de TODAS as ligas configuradas."""
    all_matches = []
    for code in LEAGUES:
        try:
            matches = get_upcoming_matches(code, days_ahead)
            for m in matches:
                m["_league_code"] = code
                m["_league_name"] = LEAGUES[code]["name"]
            all_matches.extend(matches)
        except requests.exceptions.HTTPError as e:
            print(f"  [!] Erro ao buscar {LEAGUES[code]['name']}: {e}")
    return all_matches
