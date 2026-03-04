"""Configurações centrais do sistema de análise."""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# API Keys
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")

# Football-data.org league codes
LEAGUES = {
    "PL": {"name": "Premier League", "code": "PL", "country": "England"},
    "BL1": {"name": "Bundesliga", "code": "BL1", "country": "Germany"},
    "PD": {"name": "La Liga", "code": "PD", "country": "Spain"},
    "SA": {"name": "Serie A", "code": "SA", "country": "Italy"},
    "FL1": {"name": "Ligue 1", "code": "FL1", "country": "France"},
}

# The Odds API sport keys (mapeados para football-data.org codes)
ODDS_SPORT_KEYS = {
    "PL": "soccer_epl",
    "BL1": "soccer_germany_bundesliga",
    "PD": "soccer_spain_la_liga",
    "SA": "soccer_italy_serie_a",
    "FL1": "soccer_france_ligue_one",
}

# Mercados foco
MARKETS = ["over_under_25", "btts"]

# Filtros de value bet
MIN_EDGE = 0.05           # Edge mínimo de 5% para considerar value bet
MIN_MATCHES_HISTORY = 10  # Mínimo de jogos no histórico para análise
MIN_CONFIDENCE = 0.55     # Confiança mínima para recomendar

# Gestão de banca
BANKROLL = 1000.0         # Banca inicial (ajustável)
MAX_STAKE_PCT = 0.05      # Máximo 5% da banca por aposta
KELLY_FRACTION = 0.25     # Kelly fracionado (25% do Kelly completo)

# OpenRouter config
OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
