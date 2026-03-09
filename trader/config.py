"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    OKX GRID TRADING BOT - CONFIGURAÇÃO                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Este módulo centraliza TODAS as configurações do bot.                     ║
║  Ajuste os parâmetros abaixo conforme sua estratégia.                      ║
║                                                                            ║
║  PARÂMETROS CRÍTICOS:                                                      ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  • PAIR          → Par de negociação (ex: ETH-USDT)                        ║
║  • GRID_COUNT    → Quantidade de grids (mais grids = mais operações)       ║
║  • GRID_RANGE    → Faixa de preço do grid em % (ex: 3.0 = ±3%)            ║
║  • INVESTMENT    → Capital total alocado em USDT                           ║
║  • STOP_LOSS     → Stop loss em % abaixo do preço inferior do grid        ║
║  • TAKE_PROFIT   → Take profit em % acima do preço superior do grid       ║
║                                                                            ║
║  TAXAS OKX (Spot - pares não BRL, Nível 1):                                ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  • Maker/Formador (limit order): 0.10%                                     ║
║  • Taker/Tomador (market order): 0.40%                                     ║
║  • O bot usa APENAS limit orders para pagar a menor taxa (maker)           ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv(Path(__file__).parent / ".env")


# ═══════════════════════════════════════════════════════════════════════════════
#  CREDENCIAIS DA API (carregadas do .env)
# ═══════════════════════════════════════════════════════════════════════════════

API_KEY = os.getenv("OKX_API_KEY", "")
SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
DEMO_TRADING = os.getenv("OKX_DEMO_TRADING", "True").lower() == "true"


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO DO GRID TRADING
# ═══════════════════════════════════════════════════════════════════════════════

# Par de negociação
# Pares recomendados: ETH-USDT, BTC-USDT, SOL-USDT (alta liquidez)
PAIR = "ETH-USDT"

# Número de grids (níveis de preço)
# Mais grids = mais trades, mas lucro menor por trade
# Com $25 e 5 grids = $5 por grid (mínimo da OKX)
GRID_COUNT = 5

# Faixa do grid em porcentagem (±%)
# Ex: 2.0 significa que o grid cobre de -2% a +2% do preço atual
# Range menor com poucos grids = espaçamento maior = mais lucro por ciclo
GRID_RANGE_PERCENT = 2.0

# Capital total em USDT para alocar ao bot
INVESTMENT_USDT = 25.0

# Stop Loss: % abaixo do preço inferior do grid
# Se o preço cair abaixo disso, o bot vende tudo para limitar perdas
STOP_LOSS_PERCENT = 5.0

# Take Profit: % acima do preço superior do grid
# Se o preço subir acima disso, o bot vende tudo para realizar lucro
TAKE_PROFIT_PERCENT = 5.0


# ═══════════════════════════════════════════════════════════════════════════════
#  TAXAS E CUSTOS
# ═══════════════════════════════════════════════════════════════════════════════

# Taxas da OKX para Spot Trading (Nível 1 - pares não BRL)
# https://www.okx.com/fees
MAKER_FEE = 0.0010    # 0.10% - Limit orders (formador - usado pelo bot)
TAKER_FEE = 0.0040    # 0.40% - Market orders (tomador - usado apenas em emergências)

# Custo total por ciclo completo (compra + venda com limit orders)
# = MAKER_FEE * 2 = 0.20% por ciclo grid
ROUND_TRIP_FEE = MAKER_FEE * 2


# ═══════════════════════════════════════════════════════════════════════════════
#  PARÂMETROS OPERACIONAIS
# ═══════════════════════════════════════════════════════════════════════════════

# Intervalo entre verificações de preço (em segundos)
# Menor = mais responsivo, mas mais requests à API
# OKX rate limit: 20 requests/segundo
CHECK_INTERVAL = 2.0

# Intervalo para recalibrar o grid (em segundos)
# Recalibra quando o preço se move muito para fora do range
RECALIBRATE_INTERVAL = 300  # 5 minutos

# Porcentagem do range para triggerar recalibração
# Se o preço estiver a menos de X% da borda do grid, recalibra
RECALIBRATE_THRESHOLD = 0.5  # 0.5% da borda

# Tamanho mínimo de ordem em USDT (OKX exige mínimo por par)
MIN_ORDER_SIZE_USDT = 5.0

# Máximo de ordens abertas simultâneas
MAX_OPEN_ORDERS = 50

# Precisão decimal para preço e quantidade (ajustado por par)
PRICE_PRECISION = 2     # Casas decimais no preço
QTY_PRECISION = 6       # Casas decimais na quantidade


# ═══════════════════════════════════════════════════════════════════════════════
#  CONTROLE DE RISCO
# ═══════════════════════════════════════════════════════════════════════════════

# Máximo de perda diária permitida em USDT
MAX_DAILY_LOSS_USDT = 5.0

# Máximo de perda diária em % do capital
MAX_DAILY_LOSS_PERCENT = 20.0

# Número máximo de recalibrações por hora
# Muitas recalibrações indicam mercado instável demais
MAX_RECALIBRATIONS_PER_HOUR = 6

# Habilitar trailing stop (ajusta stop loss conforme preço sobe)
TRAILING_STOP_ENABLED = True

# Porcentagem do trailing stop
TRAILING_STOP_PERCENT = 2.0


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGGING E RELATÓRIOS
# ═══════════════════════════════════════════════════════════════════════════════

# Diretório para logs
LOG_DIR = Path(__file__).parent / "logs"

# Nome do arquivo de log
LOG_FILE = "trading_bot.log"

# Arquivo de histórico de trades (CSV)
TRADES_HISTORY_FILE = "trades_history.csv"

# Arquivo de relatório de performance
PERFORMANCE_FILE = "performance_report.json"

# Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = "INFO"

# Mostrar dashboard em tempo real no terminal
SHOW_DASHBOARD = True

# Intervalo de atualização do dashboard (segundos)
DASHBOARD_REFRESH = 5


# ═══════════════════════════════════════════════════════════════════════════════
#  VALIDAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def validate_config():
    """Valida todas as configurações antes de iniciar o bot."""
    errors = []

    if not API_KEY:
        errors.append("OKX_API_KEY não configurada no .env")
    if not SECRET_KEY:
        errors.append("OKX_SECRET_KEY não configurada no .env")
    if INVESTMENT_USDT < MIN_ORDER_SIZE_USDT * GRID_COUNT:
        min_required = MIN_ORDER_SIZE_USDT * GRID_COUNT
        errors.append(
            f"INVESTMENT_USDT ({INVESTMENT_USDT}) insuficiente. "
            f"Mínimo necessário para {GRID_COUNT} grids: ${min_required:.2f}"
        )
    if GRID_COUNT < 3:
        errors.append("GRID_COUNT deve ser pelo menos 3")
    if GRID_RANGE_PERCENT <= ROUND_TRIP_FEE * 100:
        errors.append(
            f"GRID_RANGE_PERCENT ({GRID_RANGE_PERCENT}%) é menor que o custo "
            f"de taxas ({ROUND_TRIP_FEE * 100}%). Impossível lucrar."
        )
    if STOP_LOSS_PERCENT <= 0:
        errors.append("STOP_LOSS_PERCENT deve ser positivo")

    if errors:
        print("\n╔══ ERROS DE CONFIGURAÇÃO ══╗")
        for e in errors:
            print(f"║  ✗ {e}")
        print("╚═══════════════════════════╝\n")
        return False

    # Informações calculadas
    grid_spacing = (GRID_RANGE_PERCENT * 2) / GRID_COUNT
    profit_per_grid = grid_spacing - (ROUND_TRIP_FEE * 100)
    capital_per_grid = INVESTMENT_USDT / GRID_COUNT

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║              CONFIGURAÇÃO VALIDADA COM SUCESSO              ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Par:                  {PAIR:<36} ║")
    print(f"║  Capital:              ${INVESTMENT_USDT:<35.2f} ║")
    print(f"║  Grids:                {GRID_COUNT:<36} ║")
    print(f"║  Range:                ±{GRID_RANGE_PERCENT:<35.1f}║")
    print(f"║  Espaçamento por grid: {grid_spacing:<35.4f}%║")
    print(f"║  Capital por grid:     ${capital_per_grid:<35.2f}║")
    print(f"║  Taxa por ciclo:       {ROUND_TRIP_FEE * 100:<35.4f}%║")
    print(f"║  Lucro por grid:       {profit_per_grid:<35.4f}%║")
    print(f"║  Stop Loss:            -{STOP_LOSS_PERCENT:<35.1f}%║")
    print(f"║  Take Profit:          +{TAKE_PROFIT_PERCENT:<35.1f}%║")
    print(f"║  Modo:                 {'DEMO (Simulação)' if DEMO_TRADING else 'PRODUÇÃO ($$$ REAL)':<36}║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    if not DEMO_TRADING:
        print("  ⚠️  ATENÇÃO: Modo PRODUÇÃO ativo! Operando com dinheiro REAL!")
        print("  ⚠️  Certifique-se de que todas as configurações estão corretas.\n")

    return True
