"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    GRID TRADING ENGINE - MOTOR PRINCIPAL                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Como funciona o Grid Trading:                                             ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║                                                                            ║
║  1. O bot define uma FAIXA DE PREÇO (ex: $1940 - $2060 para ETH)          ║
║  2. Divide essa faixa em N GRIDS (ex: 20 níveis)                          ║
║  3. Coloca ordens de COMPRA abaixo do preço atual                          ║
║  4. Coloca ordens de VENDA acima do preço atual                            ║
║  5. Quando uma COMPRA é executada → coloca VENDA no grid acima             ║
║  6. Quando uma VENDA é executada → coloca COMPRA no grid abaixo            ║
║  7. Cada ciclo compra/venda gera lucro = espaçamento - taxas               ║
║                                                                            ║
║  Exemplo visual:                                                           ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║                                                                            ║
║     $2060 ┤ ── VENDA ──────── Grid 20                                      ║
║     $2048 ┤ ── VENDA ──────── Grid 19                                      ║
║     $2036 ┤ ── VENDA ──────── Grid 18                                      ║
║       ... │                                                                ║
║     $2006 ┤ ── VENDA ──────── Grid 11                                      ║
║  →  $2000 ┤ ══ PREÇO ATUAL ══                                              ║
║     $1994 ┤ ── COMPRA ─────── Grid 10                                      ║
║       ... │                                                                ║
║     $1964 ┤ ── COMPRA ─────── Grid 3                                       ║
║     $1952 ┤ ── COMPRA ─────── Grid 2                                       ║
║     $1940 ┤ ── COMPRA ─────── Grid 1                                       ║
║                                                                            ║
║  Lucro por ciclo (grid spacing 0.30%):                                     ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  • Espaçamento:  0.30%                                                     ║
║  • Taxa compra:  -0.08% (maker)                                            ║
║  • Taxa venda:   -0.08% (maker)                                            ║
║  • LUCRO LÍQUIDO: 0.14% por ciclo                                          ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import csv
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from okx_client import OKXClient

logger = logging.getLogger("GridBot")


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class GridLevel:
    """Representa um nível individual do grid."""

    index: int           # Índice do grid (0 = mais baixo)
    price: float         # Preço deste nível
    side: str            # 'buy' ou 'sell'
    order_id: str = ""   # ID da ordem na OKX (vazio = sem ordem ativa)
    status: str = "idle"  # idle, active, filled
    quantity: float = 0.0


@dataclass
class TradeRecord:
    """Registro de um trade completado (ciclo compra + venda)."""

    timestamp: str
    pair: str
    buy_price: float
    sell_price: float
    quantity: float
    gross_profit_usdt: float   # Lucro bruto (sem taxas)
    fee_buy_usdt: float        # Taxa da compra
    fee_sell_usdt: float       # Taxa da venda
    net_profit_usdt: float     # Lucro líquido (com taxas)
    net_profit_percent: float  # Lucro líquido em %
    grid_index: int


@dataclass
class BotStats:
    """Estatísticas acumuladas do bot."""

    start_time: str = ""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    gross_profit_usdt: float = 0.0
    total_fees_usdt: float = 0.0
    net_profit_usdt: float = 0.0

    max_drawdown_usdt: float = 0.0
    max_drawdown_percent: float = 0.0

    best_trade_usdt: float = 0.0
    worst_trade_usdt: float = 0.0

    current_price: float = 0.0
    grid_lower: float = 0.0
    grid_upper: float = 0.0
    active_buy_orders: int = 0
    active_sell_orders: int = 0

    initial_capital: float = 0.0
    current_capital: float = 0.0

    # Contadores de recalibração
    recalibrations: int = 0
    recalibrations_this_hour: int = 0
    last_recalibration_hour: int = -1

    # Trailing stop
    highest_capital: float = 0.0

    # Daily tracking
    daily_loss_usdt: float = 0.0
    current_day: str = ""

    trades_history: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
#  GRID TRADING BOT
# ═══════════════════════════════════════════════════════════════════════════════


class GridBot:
    """
    Motor principal do Grid Trading.

    Fluxo de operação:
    1. initialize() → Conecta, valida config, obtém preço atual
    2. setup_grid() → Calcula níveis e coloca ordens iniciais
    3. run() → Loop principal: monitora e gerencia ordens
    """

    def __init__(self):
        self.client = OKXClient()
        self.grids: list[GridLevel] = []
        self.stats = BotStats()
        self.running = False

        # Diretório de logs
        self.log_dir = config.LOG_DIR
        self.log_dir.mkdir(exist_ok=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  INICIALIZAÇÃO
    # ═══════════════════════════════════════════════════════════════════════

    def initialize(self) -> bool:
        """
        Inicializa o bot:
        1. Valida configuração
        2. Testa conexão com a API
        3. Verifica saldo disponível
        4. Obtém informações do instrumento
        """
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║           OKX GRID TRADING BOT - INICIALIZANDO             ║")
        print("╚══════════════════════════════════════════════════════════════╝")

        # Valida configuração
        if not config.validate_config():
            return False

        # Testa conexão
        if not self.client.test_connection():
            logger.error("Falha na conexão com a OKX")
            return False

        # Verifica saldo
        balance = self.client.get_balance("USDT")
        available = balance["available"]

        if available < config.INVESTMENT_USDT:
            logger.warning(
                f"Saldo disponível (${available:.2f}) menor que o investimento "
                f"configurado (${config.INVESTMENT_USDT:.2f})."
            )
            if available < config.MIN_ORDER_SIZE_USDT * config.GRID_COUNT:
                logger.error("Saldo insuficiente para operar. Abortando.")
                return False
            print(f"  ⚠ Usando saldo disponível: ${available:.2f}")
            self.stats.initial_capital = available
        else:
            self.stats.initial_capital = config.INVESTMENT_USDT

        self.stats.current_capital = self.stats.initial_capital
        self.stats.highest_capital = self.stats.initial_capital
        self.stats.start_time = datetime.now().isoformat()
        self.stats.current_day = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Bot inicializado | Capital: ${self.stats.initial_capital:.2f}")
        return True

    # ═══════════════════════════════════════════════════════════════════════
    #  SETUP DO GRID
    # ═══════════════════════════════════════════════════════════════════════

    def setup_grid(self) -> bool:
        """
        Configura e ativa o grid:
        1. Obtém preço atual
        2. Calcula limites superior e inferior
        3. Calcula cada nível de preço
        4. Distribui capital entre os grids
        5. Coloca ordens em cada nível

        Retorno esperado do grid:
        ─────────────────────────────────────────
        | Parâmetro              | Valor         |
        |─────────────────────────────────────────|
        | Grid Range             | ±3.0%         |
        | Grids                  | 20            |
        | Espaçamento            | 0.30%         |
        | Taxa round-trip        | 0.16%         |
        | Lucro por ciclo        | 0.14%         |
        | Capital por grid       | $25.00        |
        | Lucro por ciclo (USD)  | $0.035        |
        ─────────────────────────────────────────
        """
        ticker = self.client.get_ticker()
        if not ticker:
            logger.error("Não foi possível obter preço atual")
            return False

        current_price = ticker["last"]
        self.stats.current_price = current_price

        # Calcula limites do grid
        range_decimal = config.GRID_RANGE_PERCENT / 100
        self.stats.grid_lower = current_price * (1 - range_decimal)
        self.stats.grid_upper = current_price * (1 + range_decimal)

        # Espaçamento entre grids
        grid_step = (self.stats.grid_upper - self.stats.grid_lower) / config.GRID_COUNT

        # Informações do instrumento para precisão
        inst_info = self.client.get_instrument_info()
        price_prec = inst_info["price_precision"]

        # Capital por grid
        capital_per_grid = self.stats.initial_capital / config.GRID_COUNT

        # Cria os níveis do grid
        self.grids = []
        for i in range(config.GRID_COUNT + 1):
            price = round(self.stats.grid_lower + (i * grid_step), price_prec)
            quantity = round(capital_per_grid / price, inst_info["qty_precision"])

            side = "buy" if price < current_price else "sell"
            if abs(price - current_price) / current_price < 0.001:
                # Muito próximo do preço atual, pula este nível
                continue

            grid = GridLevel(
                index=i,
                price=price,
                side=side,
                quantity=quantity,
            )
            self.grids.append(grid)

        # Mostra detalhes do grid
        buy_grids = [g for g in self.grids if g.side == "buy"]
        sell_grids = [g for g in self.grids if g.side == "sell"]

        spacing_pct = (grid_step / current_price) * 100
        profit_per_cycle = spacing_pct - (config.ROUND_TRIP_FEE * 100)
        profit_per_cycle_usd = capital_per_grid * (profit_per_cycle / 100)

        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║                     GRID CONFIGURADO                        ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print(f"║  Preço Atual:          ${current_price:>12,.2f}                  ║")
        print(f"║  Limite Inferior:      ${self.stats.grid_lower:>12,.2f}                  ║")
        print(f"║  Limite Superior:      ${self.stats.grid_upper:>12,.2f}                  ║")
        print(f"║  Espaçamento:          {spacing_pct:>12.4f}%                 ║")
        print(f"║  Capital por grid:     ${capital_per_grid:>12,.2f}                  ║")
        print(f"║  Grids de COMPRA:      {len(buy_grids):>12}                  ║")
        print(f"║  Grids de VENDA:       {len(sell_grids):>12}                  ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║  PROJEÇÃO DE LUCRO POR CICLO:                              ║")
        print(f"║  Espaçamento:          +{spacing_pct:>11.4f}%                 ║")
        print(f"║  Taxa compra (maker):  -{config.MAKER_FEE * 100:>11.4f}%                 ║")
        print(f"║  Taxa venda (maker):   -{config.MAKER_FEE * 100:>11.4f}%                 ║")
        print(f"║  LUCRO LÍQUIDO:        +{profit_per_cycle:>11.4f}%                 ║")
        print(f"║  LUCRO EM USD:         ${profit_per_cycle_usd:>12.4f}                 ║")
        print("╚══════════════════════════════════════════════════════════════╝\n")

        # Cancela ordens existentes antes de colocar novas
        self.client.cancel_all_orders()

        # Coloca ordens em cada nível
        orders_placed = 0
        for grid in self.grids:
            result = self.client.place_limit_order(
                side=grid.side,
                price=grid.price,
                size=grid.quantity,
                client_order_id=f"grid_{grid.index}_{int(time.time())}",
            )
            if result["success"]:
                grid.order_id = result["order_id"]
                grid.status = "active"
                orders_placed += 1
            else:
                logger.warning(
                    f"Falha ao colocar ordem grid {grid.index} "
                    f"({grid.side} @ ${grid.price}): {result['message']}"
                )

        self.stats.active_buy_orders = len([g for g in self.grids if g.side == "buy" and g.status == "active"])
        self.stats.active_sell_orders = len([g for g in self.grids if g.side == "sell" and g.status == "active"])

        logger.info(
            f"Grid ativado: {orders_placed}/{len(self.grids)} ordens colocadas | "
            f"{self.stats.active_buy_orders} compras, "
            f"{self.stats.active_sell_orders} vendas"
        )

        return orders_placed > 0

    # ═══════════════════════════════════════════════════════════════════════
    #  MONITORAMENTO DE ORDENS
    # ═══════════════════════════════════════════════════════════════════════

    def check_filled_orders(self):
        """
        Verifica quais ordens foram executadas (filled).

        Quando uma ordem de COMPRA é filled:
        → Coloca nova ordem de VENDA no grid acima (lucro = espaçamento - taxas)

        Quando uma ordem de VENDA é filled:
        → Coloca nova ordem de COMPRA no grid abaixo (prepara próximo ciclo)
        """
        for grid in self.grids:
            if grid.status != "active" or not grid.order_id:
                continue

            status = self.client.get_order_status(grid.order_id)
            if not status:
                continue

            if status["status"] == "filled":
                self._handle_filled_order(grid, status)
            elif status["status"] == "canceled":
                grid.status = "idle"
                grid.order_id = ""
                logger.info(f"Ordem cancelada externamente: grid {grid.index}")

    def _handle_filled_order(self, grid: GridLevel, order_status: dict):
        """
        Processa uma ordem que foi executada (filled).

        Lógica:
        - COMPRA filled → cria VENDA no grid acima
        - VENDA filled → cria COMPRA no grid abaixo + registra lucro
        """
        fill_price = order_status["avg_price"] or grid.price
        fill_qty = order_status["filled"]
        fee = abs(order_status.get("fee", 0))

        logger.info(
            f"{'COMPRA' if grid.side == 'buy' else 'VENDA'} EXECUTADA | "
            f"Grid {grid.index} | Preço: ${fill_price:,.2f} | "
            f"Qty: {fill_qty} | Taxa: ${fee:.4f}"
        )

        grid.status = "filled"
        grid.order_id = ""

        # Encontra o grid vizinho para a contra-ordem
        grid_idx = self.grids.index(grid)

        if grid.side == "buy":
            # Compra executada → coloca venda no grid acima
            if grid_idx + 1 < len(self.grids):
                target_grid = self.grids[grid_idx + 1]
                self._place_counter_order(target_grid, "sell", fill_qty)
            # Registra trade parcial (compra realizada, aguardando venda)
            grid.side = "sell"  # Marca para tracking

        elif grid.side == "sell":
            # Venda executada → coloca compra no grid abaixo + registra lucro
            if grid_idx - 1 >= 0:
                target_grid = self.grids[grid_idx - 1]
                self._place_counter_order(target_grid, "buy", fill_qty)

            # Registra trade completo
            buy_grid_price = self.grids[grid_idx - 1].price if grid_idx > 0 else fill_price
            self._record_trade(buy_grid_price, fill_price, fill_qty, grid.index)
            grid.side = "buy"  # Marca para tracking

    def _place_counter_order(self, grid: GridLevel, side: str, quantity: float):
        """Coloca a contra-ordem em um grid vizinho."""
        result = self.client.place_limit_order(
            side=side,
            price=grid.price,
            size=quantity,
            client_order_id=f"grid_{grid.index}_{int(time.time())}",
        )
        if result["success"]:
            grid.order_id = result["order_id"]
            grid.side = side
            grid.status = "active"
        else:
            logger.error(
                f"Falha na contra-ordem: {side} @ ${grid.price} | {result['message']}"
            )

    def _record_trade(
        self,
        buy_price: float,
        sell_price: float,
        quantity: float,
        grid_index: int,
    ):
        """
        Registra um ciclo completo de trade (compra + venda).

        Cálculo detalhado:
        ─────────────────────────────────────────────────
        Valor compra    = buy_price × quantity
        Valor venda     = sell_price × quantity
        Lucro bruto     = valor_venda - valor_compra
        Taxa compra     = valor_compra × 0.08%
        Taxa venda      = valor_venda × 0.08%
        Lucro líquido   = lucro_bruto - taxa_compra - taxa_venda
        ─────────────────────────────────────────────────
        """
        buy_value = buy_price * quantity
        sell_value = sell_price * quantity

        gross_profit = sell_value - buy_value
        fee_buy = buy_value * config.MAKER_FEE
        fee_sell = sell_value * config.MAKER_FEE
        net_profit = gross_profit - fee_buy - fee_sell
        net_profit_pct = (net_profit / buy_value) * 100 if buy_value > 0 else 0

        trade = TradeRecord(
            timestamp=datetime.now().isoformat(),
            pair=config.PAIR,
            buy_price=buy_price,
            sell_price=sell_price,
            quantity=quantity,
            gross_profit_usdt=gross_profit,
            fee_buy_usdt=fee_buy,
            fee_sell_usdt=fee_sell,
            net_profit_usdt=net_profit,
            net_profit_percent=net_profit_pct,
            grid_index=grid_index,
        )

        # Atualiza estatísticas
        self.stats.total_trades += 1
        self.stats.gross_profit_usdt += gross_profit
        self.stats.total_fees_usdt += fee_buy + fee_sell
        self.stats.net_profit_usdt += net_profit
        self.stats.current_capital += net_profit

        if net_profit > 0:
            self.stats.winning_trades += 1
        else:
            self.stats.losing_trades += 1

        if net_profit > self.stats.best_trade_usdt:
            self.stats.best_trade_usdt = net_profit
        if net_profit < self.stats.worst_trade_usdt:
            self.stats.worst_trade_usdt = net_profit

        # Tracking de capital máximo (para drawdown)
        if self.stats.current_capital > self.stats.highest_capital:
            self.stats.highest_capital = self.stats.current_capital

        drawdown = self.stats.highest_capital - self.stats.current_capital
        if drawdown > self.stats.max_drawdown_usdt:
            self.stats.max_drawdown_usdt = drawdown
            self.stats.max_drawdown_percent = (
                (drawdown / self.stats.highest_capital) * 100
            )

        # Daily loss tracking
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.stats.current_day:
            self.stats.daily_loss_usdt = 0.0
            self.stats.current_day = today
        if net_profit < 0:
            self.stats.daily_loss_usdt += abs(net_profit)

        # Salva no histórico
        self.stats.trades_history.append(trade)
        self._save_trade_csv(trade)

        logger.info(
            f"TRADE COMPLETO #{self.stats.total_trades} | "
            f"Compra: ${buy_price:,.2f} → Venda: ${sell_price:,.2f} | "
            f"Bruto: ${gross_profit:+.4f} | "
            f"Taxas: ${fee_buy + fee_sell:.4f} | "
            f"Líquido: ${net_profit:+.4f} ({net_profit_pct:+.4f}%) | "
            f"Acumulado: ${self.stats.net_profit_usdt:+.4f}"
        )

    # ═══════════════════════════════════════════════════════════════════════
    #  CONTROLE DE RISCO
    # ═══════════════════════════════════════════════════════════════════════

    def check_risk_limits(self) -> Optional[str]:
        """
        Verifica limites de risco. Retorna ação a tomar ou None se tudo ok.

        Verificações:
        1. Stop Loss: preço caiu demais
        2. Take Profit: preço subiu demais
        3. Max Daily Loss: perda diária excedida
        4. Trailing Stop: capital caiu do pico

        Returns:
            'stop_loss' | 'take_profit' | 'daily_limit' | 'trailing_stop' | None
        """
        ticker = self.client.get_ticker()
        if not ticker:
            return None

        price = ticker["last"]
        self.stats.current_price = price

        # Stop Loss
        stop_price = self.stats.grid_lower * (1 - config.STOP_LOSS_PERCENT / 100)
        if price <= stop_price:
            logger.warning(
                f"STOP LOSS atingido! Preço ${price:,.2f} <= ${stop_price:,.2f}"
            )
            return "stop_loss"

        # Take Profit
        tp_price = self.stats.grid_upper * (1 + config.TAKE_PROFIT_PERCENT / 100)
        if price >= tp_price:
            logger.info(
                f"TAKE PROFIT atingido! Preço ${price:,.2f} >= ${tp_price:,.2f}"
            )
            return "take_profit"

        # Max Daily Loss
        if self.stats.daily_loss_usdt >= config.MAX_DAILY_LOSS_USDT:
            logger.warning(
                f"LIMITE DIÁRIO DE PERDA atingido: "
                f"${self.stats.daily_loss_usdt:.2f} >= "
                f"${config.MAX_DAILY_LOSS_USDT:.2f}"
            )
            return "daily_limit"

        daily_loss_pct = (
            (self.stats.daily_loss_usdt / self.stats.initial_capital) * 100
        )
        if daily_loss_pct >= config.MAX_DAILY_LOSS_PERCENT:
            logger.warning(
                f"LIMITE DIÁRIO DE PERDA (%) atingido: "
                f"{daily_loss_pct:.2f}% >= {config.MAX_DAILY_LOSS_PERCENT}%"
            )
            return "daily_limit"

        # Trailing Stop
        if config.TRAILING_STOP_ENABLED:
            trail_threshold = self.stats.highest_capital * (
                1 - config.TRAILING_STOP_PERCENT / 100
            )
            if self.stats.current_capital <= trail_threshold:
                logger.warning(
                    f"TRAILING STOP atingido! Capital ${self.stats.current_capital:.2f} "
                    f"<= ${trail_threshold:.2f} "
                    f"(pico: ${self.stats.highest_capital:.2f})"
                )
                return "trailing_stop"

        return None

    def check_recalibrate(self) -> bool:
        """
        Verifica se o grid precisa ser recalibrado.

        Recalibra quando o preço está muito próximo da borda do grid,
        indicando que o preço está saindo da faixa.
        """
        if not self.stats.current_price:
            return False

        price = self.stats.current_price
        threshold = config.RECALIBRATE_THRESHOLD / 100

        # Verifica se está muito perto da borda inferior
        lower_dist = (price - self.stats.grid_lower) / self.stats.grid_lower
        if lower_dist < threshold:
            return True

        # Verifica se está muito perto da borda superior
        upper_dist = (self.stats.grid_upper - price) / self.stats.grid_upper
        if upper_dist < threshold:
            return True

        return False

    def recalibrate(self):
        """
        Recalibra o grid: cancela todas as ordens e reconfigura
        baseado no preço atual.

        Proteção: máximo de N recalibrações por hora.
        """
        current_hour = datetime.now().hour
        if current_hour != self.stats.last_recalibration_hour:
            self.stats.recalibrations_this_hour = 0
            self.stats.last_recalibration_hour = current_hour

        if self.stats.recalibrations_this_hour >= config.MAX_RECALIBRATIONS_PER_HOUR:
            logger.warning(
                f"Máximo de recalibrações/hora atingido "
                f"({config.MAX_RECALIBRATIONS_PER_HOUR}). Aguardando."
            )
            return

        logger.info("RECALIBRANDO GRID...")
        self.stats.recalibrations += 1
        self.stats.recalibrations_this_hour += 1

        self.client.cancel_all_orders()
        time.sleep(1)  # Aguarda cancelamentos processarem
        self.setup_grid()

    # ═══════════════════════════════════════════════════════════════════════
    #  ENCERRAMENTO DE EMERGÊNCIA
    # ═══════════════════════════════════════════════════════════════════════

    def emergency_close(self, reason: str):
        """
        Encerra todas as posições e ordens imediatamente.

        Usado para:
        - Stop Loss atingido
        - Take Profit atingido
        - Limite diário de perda
        - Trailing stop
        - Encerramento manual (Ctrl+C)
        """
        logger.warning(f"ENCERRAMENTO DE EMERGÊNCIA: {reason}")
        print(f"\n  ⚠ ENCERRANDO BOT: {reason}")

        # 1. Cancela todas as ordens pendentes
        cancelled = self.client.cancel_all_orders()
        print(f"  ✓ {cancelled} ordens canceladas")

        # 2. Verifica se há posição aberta para vender
        pair_base = config.PAIR.split("-")[0]  # Ex: 'ETH' de 'ETH-USDT'
        balance = self.client.get_balance(pair_base)

        if balance["available"] > 0:
            print(
                f"  Vendendo {balance['available']} {pair_base} a mercado "
                f"(taxa: {config.TAKER_FEE * 100}%)..."
            )
            result = self.client.place_market_order("sell", balance["available"])
            if result["success"]:
                print(f"  ✓ Posição fechada: ordem {result['order_id']}")
            else:
                print(f"  ✗ Falha ao fechar posição: {result['message']}")

        # 3. Salva relatório final
        self._save_performance_report()
        self.running = False

    # ═══════════════════════════════════════════════════════════════════════
    #  PERSISTÊNCIA E RELATÓRIOS
    # ═══════════════════════════════════════════════════════════════════════

    def _save_trade_csv(self, trade: TradeRecord):
        """Salva trade no arquivo CSV de histórico."""
        csv_path = self.log_dir / config.TRADES_HISTORY_FILE
        file_exists = csv_path.exists()

        with open(csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "timestamp", "pair", "buy_price", "sell_price", "quantity",
                    "gross_profit_usdt", "fee_buy_usdt", "fee_sell_usdt",
                    "net_profit_usdt", "net_profit_percent", "grid_index",
                ])
            writer.writerow([
                trade.timestamp, trade.pair, trade.buy_price, trade.sell_price,
                trade.quantity, f"{trade.gross_profit_usdt:.6f}",
                f"{trade.fee_buy_usdt:.6f}", f"{trade.fee_sell_usdt:.6f}",
                f"{trade.net_profit_usdt:.6f}", f"{trade.net_profit_percent:.6f}",
                trade.grid_index,
            ])

    def _save_performance_report(self):
        """Salva relatório de performance em JSON."""
        report_path = self.log_dir / config.PERFORMANCE_FILE

        runtime = ""
        if self.stats.start_time:
            start = datetime.fromisoformat(self.stats.start_time)
            duration = datetime.now() - start
            hours = duration.total_seconds() / 3600
            runtime = f"{hours:.2f} horas"

        win_rate = (
            (self.stats.winning_trades / self.stats.total_trades * 100)
            if self.stats.total_trades > 0
            else 0
        )

        roi = (
            (self.stats.net_profit_usdt / self.stats.initial_capital * 100)
            if self.stats.initial_capital > 0
            else 0
        )

        report = {
            "resumo": {
                "inicio": self.stats.start_time,
                "fim": datetime.now().isoformat(),
                "duracao": runtime,
                "par": config.PAIR,
                "capital_inicial": self.stats.initial_capital,
                "capital_final": self.stats.current_capital,
                "modo": "DEMO" if config.DEMO_TRADING else "PRODUÇÃO",
            },
            "performance": {
                "total_trades": self.stats.total_trades,
                "trades_positivos": self.stats.winning_trades,
                "trades_negativos": self.stats.losing_trades,
                "win_rate": f"{win_rate:.2f}%",
                "lucro_bruto_usdt": f"${self.stats.gross_profit_usdt:.4f}",
                "total_taxas_usdt": f"${self.stats.total_fees_usdt:.4f}",
                "lucro_liquido_usdt": f"${self.stats.net_profit_usdt:.4f}",
                "roi": f"{roi:.4f}%",
                "melhor_trade": f"${self.stats.best_trade_usdt:.4f}",
                "pior_trade": f"${self.stats.worst_trade_usdt:.4f}",
            },
            "risco": {
                "max_drawdown_usdt": f"${self.stats.max_drawdown_usdt:.4f}",
                "max_drawdown_percent": f"{self.stats.max_drawdown_percent:.4f}%",
                "recalibracoes": self.stats.recalibrations,
            },
            "taxas_detalhamento": {
                "maker_fee": f"{config.MAKER_FEE * 100}%",
                "taker_fee": f"{config.TAKER_FEE * 100}%",
                "custo_por_ciclo": f"{config.ROUND_TRIP_FEE * 100}%",
                "total_gasto_taxas": f"${self.stats.total_fees_usdt:.4f}",
            },
            "configuracao": {
                "grids": config.GRID_COUNT,
                "range": f"±{config.GRID_RANGE_PERCENT}%",
                "stop_loss": f"-{config.STOP_LOSS_PERCENT}%",
                "take_profit": f"+{config.TAKE_PROFIT_PERCENT}%",
                "trailing_stop": config.TRAILING_STOP_ENABLED,
            },
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Relatório salvo em: {report_path}")

    # ═══════════════════════════════════════════════════════════════════════
    #  LOOP PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════

    def run(self):
        """
        Loop principal do bot.

        Ciclo a cada CHECK_INTERVAL segundos:
        1. Verifica limites de risco
        2. Verifica ordens preenchidas
        3. Recalibra se necessário
        4. Atualiza dashboard
        """
        self.running = True
        last_recalibrate_check = 0

        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║             BOT EM EXECUÇÃO - Ctrl+C para parar            ║")
        print("╚══════════════════════════════════════════════════════════════╝\n")

        try:
            while self.running:
                # 1. Verifica riscos
                risk_action = self.check_risk_limits()
                if risk_action:
                    self.emergency_close(risk_action)
                    break

                # 2. Verifica ordens preenchidas
                self.check_filled_orders()

                # 3. Recalibra se necessário
                now = time.time()
                if now - last_recalibrate_check >= config.RECALIBRATE_INTERVAL:
                    if self.check_recalibrate():
                        self.recalibrate()
                    last_recalibrate_check = now

                # 4. Atualiza contadores
                self.stats.active_buy_orders = len(
                    [g for g in self.grids if g.side == "buy" and g.status == "active"]
                )
                self.stats.active_sell_orders = len(
                    [g for g in self.grids if g.side == "sell" and g.status == "active"]
                )

                # Aguarda próximo ciclo
                time.sleep(config.CHECK_INTERVAL)

        except KeyboardInterrupt:
            self.emergency_close("Interrupção manual (Ctrl+C)")

        print("\n  Bot encerrado.")

    def get_stats(self) -> dict:
        """Retorna estatísticas atuais para o dashboard."""
        runtime = ""
        if self.stats.start_time:
            start = datetime.fromisoformat(self.stats.start_time)
            duration = datetime.now() - start
            total_secs = int(duration.total_seconds())
            hours, remainder = divmod(total_secs, 3600)
            minutes, seconds = divmod(remainder, 60)
            runtime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        win_rate = (
            (self.stats.winning_trades / self.stats.total_trades * 100)
            if self.stats.total_trades > 0
            else 0
        )

        roi = (
            (self.stats.net_profit_usdt / self.stats.initial_capital * 100)
            if self.stats.initial_capital > 0
            else 0
        )

        return {
            "running": self.running,
            "runtime": runtime,
            "pair": config.PAIR,
            "mode": "DEMO" if config.DEMO_TRADING else "LIVE",
            "current_price": self.stats.current_price,
            "grid_lower": self.stats.grid_lower,
            "grid_upper": self.stats.grid_upper,
            "initial_capital": self.stats.initial_capital,
            "current_capital": self.stats.current_capital,
            "total_trades": self.stats.total_trades,
            "winning_trades": self.stats.winning_trades,
            "losing_trades": self.stats.losing_trades,
            "win_rate": win_rate,
            "gross_profit": self.stats.gross_profit_usdt,
            "total_fees": self.stats.total_fees_usdt,
            "net_profit": self.stats.net_profit_usdt,
            "roi": roi,
            "max_drawdown": self.stats.max_drawdown_usdt,
            "max_drawdown_pct": self.stats.max_drawdown_percent,
            "active_buys": self.stats.active_buy_orders,
            "active_sells": self.stats.active_sell_orders,
            "recalibrations": self.stats.recalibrations,
            "best_trade": self.stats.best_trade_usdt,
            "worst_trade": self.stats.worst_trade_usdt,
            "daily_loss": self.stats.daily_loss_usdt,
        }
