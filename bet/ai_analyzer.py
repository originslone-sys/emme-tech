"""Camada de IA — Análise qualitativa via OpenRouter."""

import json
import requests
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL


def analyze_match(match_data, stats_prediction, odds_info=None):
    """Envia dados do jogo para IA analisar fatores qualitativos.

    A IA recebe os dados estatísticos já calculados e busca informações
    adicionais (lesões, contexto, motivação) para ajustar a previsão.
    """
    home = match_data["homeTeam"]["name"]
    away = match_data["awayTeam"]["name"]
    league = match_data.get("_league_name", "Unknown")
    match_date = match_data.get("utcDate", "")

    prompt = _build_prompt(home, away, league, match_date, stats_prediction, odds_info)

    try:
        response = _call_openrouter(prompt)
        return _parse_response(response)
    except Exception as e:
        print(f"  [!] Erro na análise IA de {home} vs {away}: {e}")
        return None


def _build_prompt(home, away, league, date, stats, odds):
    """Monta o prompt detalhado para a IA."""
    odds_section = ""
    if odds:
        odds_section = f"""
## Odds disponíveis no mercado:
- Over 2.5: {odds.get('over_25', 'N/A')}
- Under 2.5: {odds.get('under_25', 'N/A')}
- BTTS Sim: {odds.get('btts_yes', 'N/A')}
- BTTS Não: {odds.get('btts_no', 'N/A')}
"""

    return f"""Você é um analista esportivo especializado em futebol europeu.
Analise o jogo abaixo e forneça sua avaliação qualitativa.

## Jogo
{home} vs {away}
Liga: {league}
Data: {date}

## Dados estatísticos já calculados (modelo Poisson):
- Gols esperados {home}: {stats['lambda_home']}
- Gols esperados {away}: {stats['lambda_away']}
- Prob. Over 2.5: {stats['over_25']:.1%}
- Prob. Under 2.5: {stats['under_25']:.1%}
- Prob. BTTS Sim: {stats['btts_yes']:.1%}
- Prob. BTTS Não: {stats['btts_no']:.1%}
- Placar mais provável: {stats['most_likely_score']} ({stats['most_likely_score_prob']:.1%})
{odds_section}

## Sua tarefa:
Pesquise e analise os seguintes fatores qualitativos para AJUSTAR as probabilidades:

1. **Lesões e suspensões** de jogadores-chave de ambos os times
2. **Forma recente** — momento dos times nas últimas rodadas
3. **Contexto da partida** — posição na tabela, briga por título/rebaixamento/vaga europeia
4. **Motivação** — é clássico? derby? jogo decisivo?
5. **Fadiga** — calendário apertado? jogou meio de semana?
6. **Histórico recente do confronto direto**
7. **Troca de treinador recente** — se houve, impacto provável

## Responda EXATAMENTE neste formato JSON:
```json
{{
    "analysis_summary": "Resumo em 2-3 frases da sua análise",
    "key_factors": ["fator 1", "fator 2", "fator 3"],
    "adjusted_over_25": 0.XX,
    "adjusted_btts_yes": 0.XX,
    "confidence_over_25": "alta/media/baixa",
    "confidence_btts": "alta/media/baixa",
    "risk_factors": ["risco 1", "risco 2"],
    "recommendation": "Sua recomendação final para este jogo"
}}
```

IMPORTANTE:
- Os valores adjusted devem ser probabilidades entre 0 e 1
- Ajuste para CIMA ou BAIXO com base nos fatores qualitativos encontrados
- Se não encontrar informações suficientes, mantenha próximo aos valores estatísticos
- Seja conservador nos ajustes (máximo ±10% de variação)"""


def _call_openrouter(prompt):
    """Faz a chamada para a API do OpenRouter."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/bet-analyzer",
        "X-Title": "Bet Analyzer",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Você é um analista esportivo profissional. Responda sempre em JSON válido conforme solicitado.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1500,
    }

    resp = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return content


def _parse_response(response_text):
    """Extrai JSON da resposta da IA."""
    text = response_text.strip()

    # Tenta extrair JSON de blocos de código
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Tenta encontrar o primeiro { e último }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None
