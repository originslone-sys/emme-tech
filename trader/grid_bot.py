"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    GRID TRADING ENGINE - MOTOR PRINCIPAL                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Como funciona o Grid Trading (Spot - apenas BUY grids):                   ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║                                                                            ║
║  1. O bot define uma FAIXA DE PREÇO abaixo do preço atual                 ║
║  2. Divide essa faixa em N ZONAS (grids)                                  ║
║  3. Cada zona tem um buy_price e sell_price (grid acima)                   ║
║  4. Coloca ordens de COMPRA em cada zona                                   ║
║  5. Quando uma COMPRA é executada → coloca VENDA no sell_price             ║
║  6. Quando uma VENDA é executada → registra lucro + recoloca COMPRA        ║
║  7. Cada ciclo compra/venda gera lucro = espaçamento - taxas               ║
║                                                                            ║
║  Exemplo visual (ETH @ $2000, range 4%):                                   ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║                                                                            ║
║  →  $2000 ┤ ══ PREÇO ATUAL ══                                              ║
║     $1984 ┤ ── VENDA Grid 4 (sell_price) / COMPRA Grid 4 (buy_price)       ║
║     $1968 ┤ ── VENDA Grid 3 / COMPRA Grid 3                                ║
║     $1952 ┤ ── VENDA Grid 2 / COMPRA Grid 2                                ║
║     $1936 ┤ ── VENDA Grid 1 / COMPRA Grid 1                                ║
║     $1920 ┤ ── COMPRA Grid 0 (mais baixo)                                  ║
║                                                                            ║
║  Ciclo por grid:                                                           ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  COMPRA @ buy_price → VENDA @ sell_price → LUCRO → COMPRA novamente       ║
║                                                                            ║
║  Lucro por ciclo:                                                          ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  • Espaçamento:  0.80%                                                     ║
║  • Taxa compra:  -0.10% (maker/formador)                                   ║
║  • Taxa venda:   -0.10% (maker/formador)                                   ║
║  • LUCRO LÍQUIDO: 0.60% por ciclo                                          ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import csv
import json
import logging
import os
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
    """
    Representa uma zona do grid (entre dois níveis de preço adjacentes).

    Cada grid tem:
    - buy_price: preço onde comprar
    - sell_price: preço onde vender (= nível acima do buy_price)
    - O ciclo é: COMPRA → VENDA → LUCRO → COMPRA novamente
    """

    index: int              # Índice do grid (0 = mais baixo)
    buy_price: float        # Preço de compra
    sell_price: float       # Preço de venda (grid acima)
    side: str = "buy"       # Ordem atual: 'buy' ou 'sell'
    order_id: str = ""      # ID da ordem na OKX (vazio = sem ordem ativa)
    status: str = "idle"    # idle, active, filled
    quantity: float = 0.0   # Quantidade base para este grid
    filled_qty: float = 0.0 # Quantidade preenchida na última compra


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
    2. setup_grid() → Calcula níveis e coloca ordens iniciais (somente COMPRA)
    3. run() → Loop principal: monitora e gerencia ordens
    """

    # Contador global para gerar clOrdId único
    _order_counter = 0

    def __init__(self):
        self.client = OKXClient()
        self.grids: list[GridLevel] = []
        self.stats = BotStats()
        self.running = False

        # Diretório de logs
        self.log_dir = config.LOG_DIR
        self.log_dir.mkdir(exist_ok=True)

    def _gen_client_order_id(self, grid_index: int, side: str) -> str:
        """
        Gera clOrdId único para a OKX (1-32 chars alfanuméricos).
        Formato: g{index}{side_char}{timestamp_curto}{counter}
        Exemplo: g0b7234501, g2s7234502
        """
        GridBot._order_counter += 1
        ts = int(time.time()) % 100000  # 5 dígitos
        side_char = "b" if side == "buy" else "s"
        return f"g{grid_index}{side_char}{ts}{GridBot._order_counter}"

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
        Configura e ativa o grid (somente ordens de COMPRA).

        Arquitetura:
        ─────────────────────────────────────────
        - Todos os grids ficam ABAIXO do preço atual
        - Cada grid é uma ZONA com buy_price e sell_price
        - Apenas ordens de COMPRA são colocadas inicialmente
        - Ordens de VENDA são criadas quando compras são executadas
        - Isso evita o problema de vender ETH que não possuímos (spot)
        ─────────────────────────────────────────

        Cálculo do range:
        - grid_upper = preço atual
        - grid_lower = preço atual × (1 - GRID_RANGE_PERCENT × 2 / 100)
        - Isso dá um range total = GRID_RANGE_PERCENT × 2 (ex: 4% com range 2.0)
        - Todos os N grids ficam nesse range, todos com ordens de compra
        """
        ticker = self.client.get_ticker()
        if not ticker:
            logger.error("Não foi possível obter preço atual")
            return False

        current_price = ticker["last"]
        self.stats.current_price = current_price

        # Range unilateral: do preço atual para baixo
        # GRID_RANGE_PERCENT=2.0 → range total = 4% abaixo do preço atual
        total_range = config.GRID_RANGE_PERCENT * 2 / 100
        self.stats.grid_upper = current_price
        self.stats.grid_lower = current_price * (1 - total_range)

        # N+1 níveis de preço → N zonas (grids)
        num_levels = config.GRID_COUNT + 1
        grid_step = (self.stats.grid_upper - self.stats.grid_lower) / config.GRID_COUNT

        # Informações do instrumento para precisão
        inst_info = self.client.get_instrument_info()
        price_prec = inst_info["price_precision"]
        qty_prec = inst_info["qty_precision"]

        # Calcula todos os níveis de preço
        levels = []
        for i in range(num_levels):
            price = round(self.stats.grid_lower + (i * grid_step), price_prec)
            levels.append(price)

        # Capital por grid (todo o capital vai para os grids de compra)
        capital_per_grid = self.stats.initial_capital / config.GRID_COUNT

        # Cria as zonas do grid
        self.grids = []
        for i in range(config.GRID_COUNT):
            buy_price = levels[i]
            sell_price = levels[i + 1]
            quantity = round(capital_per_grid / buy_price, qty_prec)

            # Valida quantidade mínima
            if quantity < inst_info["min_size"]:
                logger.warning(
                    f"Grid {i}: quantidade {quantity} < mínimo {inst_info['min_size']}. "
                    f"Aumentando para mínimo."
                )
                quantity = inst_info["min_size"]

            grid = GridLevel(
                index=i,
                buy_price=buy_price,
                sell_price=sell_price,
                side="buy",
                quantity=quantity,
            )
            self.grids.append(grid)

        # Mostra detalhes do grid
        spacing_pct = (grid_step / current_price) * 100
        profit_per_cycle = spacing_pct - (config.ROUND_TRIP_FEE * 100)
        profit_per_cycle_usd = capital_per_grid * (profit_per_cycle / 100)

        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║                     GRID CONFIGURADO                        ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print(f"║  Preço Atual:          ${current_price:>12,.2f}                  ║")
        print(f"║  Limite Inferior:      ${self.stats.grid_lower:>12,.2f}                  ║")
        print(f"║  Limite Superior:      ${self.stats.grid_upper:>12,.2f}                  ║")
        print(f"║  Grids (zonas):        {config.GRID_COUNT:>12}                  ║")
        print(f"║  Espaçamento:          {spacing_pct:>12.4f}%                 ║")
        print(f"║  Capital por grid:     ${capital_per_grid:>12,.2f}                  ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║  PROJEÇÃO DE LUCRO POR CICLO:                              ║")
        print(f"║  Espaçamento:          +{spacing_pct:>11.4f}%                 ║")
        print(f"║  Taxa compra (maker):  -{config.MAKER_FEE * 100:>11.4f}%                 ║")
        print(f"║  Taxa venda (maker):   -{config.MAKER_FEE * 100:>11.4f}%                 ║")
        print(f"║  LUCRO LÍQUIDO:        +{profit_per_cycle:>11.4f}%                 ║")
        print(f"║  LUCRO EM USD:         ${profit_per_cycle_usd:>12.4f}                 ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║  GRIDS DE COMPRA:                                          ║")
        for grid in self.grids:
            print(
                f"║    Grid {grid.index}: "
                f"COMPRA ${grid.buy_price:>10,.2f} → "
                f"VENDA ${grid.sell_price:>10,.2f} | "
                f"Qty: {grid.quantity}      ║"
            )
        print("╚══════════════════════════════════════════════════════════════╝\n")

        # Cancela ordens existentes antes de colocar novas
        self.client.cancel_all_orders()

        # Coloca ordens de COMPRA em cada zona
        orders_placed = 0
        for grid in self.grids:
            result = self.client.place_limit_order(
                side="buy",
                price=grid.buy_price,
                size=grid.quantity,
                client_order_id=self._gen_client_order_id(grid.index, "buy"),
            )
            if result["success"]:
                grid.order_id = result["order_id"]
                grid.status = "active"
                grid.side = "buy"
                orders_placed += 1
            else:
                logger.warning(
                    f"Falha ao colocar ordem grid {grid.index} "
                    f"(buy @ ${grid.buy_price:,.2f}): {result['message']}"
                )

        self.stats.active_buy_orders = orders_placed
        self.stats.active_sell_orders = 0

        logger.info(
            f"Grid ativado: {orders_placed}/{len(self.grids)} ordens de COMPRA colocadas"
        )

        return orders_placed > 0

    # ═══════════════════════════════════════════════════════════════════════
    #  MONITORAMENTO DE ORDENS
    # ═══════════════════════════════════════════════════════════════════════

    def check_filled_orders(self):
        """
        Verifica quais ordens foram executadas (filled).

        Quando uma ordem de COMPRA é filled:
        → Coloca VENDA no sell_price do mesmo grid

        Quando uma ordem de VENDA é filled:
        → Registra lucro + recoloca COMPRA no buy_price do mesmo grid
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

        Ciclo do grid:
        ─────────────────────────────────────────
        COMPRA filled → coloca VENDA no sell_price
        VENDA filled  → registra lucro + coloca COMPRA no buy_price
        ─────────────────────────────────────────
        """
        fill_price = order_status["avg_price"] or (
            grid.buy_price if grid.side == "buy" else grid.sell_price
        )
        fill_qty = order_status["filled"]
        fee = abs(order_status.get("fee", 0))

        if fill_qty <= 0:
            logger.warning(
                f"Grid {grid.index}: ordem marcada como filled mas qty=0. Ignorando."
            )
            return

        logger.info(
            f"{'COMPRA' if grid.side == 'buy' else 'VENDA'} EXECUTADA | "
            f"Grid {grid.index} | Preço: ${fill_price:,.2f} | "
            f"Qty: {fill_qty} | Taxa: ${fee:.4f}"
        )

        grid.order_id = ""

        if grid.side == "buy":
            # ═══ COMPRA EXECUTADA → COLOCA VENDA ═══
            grid.filled_qty = fill_qty
            grid.status = "filled"

            profit_target_pct = ((grid.sell_price / grid.buy_price) - 1) * 100
            logger.info(
                f"Grid {grid.index} | Colocando VENDA @ ${grid.sell_price:,.2f} "
                f"(lucro alvo: {profit_target_pct:.4f}% bruto)"
            )

            result = self.client.place_limit_order(
                side="sell",
                price=grid.sell_price,
                size=fill_qty,
                client_order_id=self._gen_client_order_id(grid.index, "sell"),
            )
            if result["success"]:
                grid.order_id = result["order_id"]
                grid.side = "sell"
                grid.status = "active"
            else:
                logger.error(
                    f"CRÍTICO: Falha ao criar venda para grid {grid.index} "
                    f"@ ${grid.sell_price:,.2f}: {result['message']}. "
                    f"ETH comprado ficará sem ordem de venda!"
                )
                grid.status = "filled"  # Mantém como filled para retry

        elif grid.side == "sell":
            # ═══ VENDA EXECUTADA → REGISTRA LUCRO + RECOLOCA COMPRA ═══
            self._record_trade(
                grid.buy_price, grid.sell_price, fill_qty, grid.index
            )

            logger.info(
                f"Grid {grid.index} | Ciclo completo! "
                f"Recolocando COMPRA @ ${grid.buy_price:,.2f}"
            )

            result = self.client.place_limit_order(
                side="buy",
                price=grid.buy_price,
                size=grid.quantity,
                client_order_id=self._gen_client_order_id(grid.index, "buy"),
            )
            if result["success"]:
                grid.order_id = result["order_id"]
                grid.side = "buy"
                grid.status = "active"
                grid.filled_qty = 0.0
            else:
                logger.error(
                    f"Falha ao recriar compra para grid {grid.index} "
                    f"@ ${grid.buy_price:,.2f}: {result['message']}"
                )
                grid.status = "idle"
                grid.side = "buy"  # Reset para buy para próxima tentativa

    def _retry_failed_orders(self):
        """
        Tenta recolocar ordens que falharam.
        Grids com status 'filled' e side 'buy' precisam de venda.
        Grids com status 'idle' e side 'buy' precisam de compra.
        """
        for grid in self.grids:
            if grid.status == "filled" and grid.side == "buy" and grid.filled_qty > 0:
                # Compra foi executada mas a venda falhou - tentar novamente
                logger.info(
                    f"Retry: colocando VENDA grid {grid.index} "
                    f"@ ${grid.sell_price:,.2f}"
                )
                result = self.client.place_limit_order(
                    side="sell",
                    price=grid.sell_price,
                    size=grid.filled_qty,
                    client_order_id=self._gen_client_order_id(grid.index, "sell"),
                )
                if result["success"]:
                    grid.order_id = result["order_id"]
                    grid.side = "sell"
                    grid.status = "active"

            elif grid.status == "idle" and grid.side == "buy" and not grid.order_id:
                # Grid sem ordem ativa - recolocar compra
                logger.info(
                    f"Retry: colocando COMPRA grid {grid.index} "
                    f"@ ${grid.buy_price:,.2f}"
                )
                result = self.client.place_limit_order(
                    side="buy",
                    price=grid.buy_price,
                    size=grid.quantity,
                    client_order_id=self._gen_client_order_id(grid.index, "buy"),
                )
                if result["success"]:
                    grid.order_id = result["order_id"]
                    grid.status = "active"

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
        Taxa compra     = valor_compra × 0.10% (maker/formador)
        Taxa venda      = valor_venda × 0.10% (maker/formador)
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
            if self.stats.initial_capital > 0
            else 0
        )
        if daily_loss_pct >= config.MAX_DAILY_LOSS_PERCENT:
            logger.warning(
                f"LIMITE DIÁRIO DE PERDA (%) atingido: "
                f"{daily_loss_pct:.2f}% >= {config.MAX_DAILY_LOSS_PERCENT}%"
            )
            return "daily_limit"

        # Trailing Stop
        if config.TRAILING_STOP_ENABLED and self.stats.highest_capital > 0:
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
        if not self.stats.current_price or not self.stats.grid_lower:
            return False

        price = self.stats.current_price
        threshold = config.RECALIBRATE_THRESHOLD / 100

        # Verifica se está muito perto da borda inferior
        if self.stats.grid_lower > 0:
            lower_dist = (price - self.stats.grid_lower) / self.stats.grid_lower
            if lower_dist < threshold:
                return True

        # Verifica se preço subiu muito acima do grid_upper
        # (grid_upper = preço original, se subiu muito, recalibra para acompanhar)
        if self.stats.grid_upper > 0:
            upper_dist = (price - self.stats.grid_upper) / self.stats.grid_upper
            if upper_dist > threshold:
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

        # Vende qualquer ETH remanescente de grids parciais antes de recalibrar
        self._sell_remaining_inventory()

        self.client.cancel_all_orders()
        time.sleep(1)  # Aguarda cancelamentos processarem
        self.setup_grid()

    def _sell_remaining_inventory(self):
        """Vende qualquer ETH que o bot possui de compras anteriores."""
        pair_base = config.PAIR.split("-")[0]
        balance = self.client.get_balance(pair_base)
        inst_info = self.client.get_instrument_info()

        if balance["available"] > 0 and balance["available"] >= inst_info["min_size"]:
            logger.info(
                f"Vendendo {balance['available']} {pair_base} remanescente "
                f"antes de recalibrar"
            )
            result = self.client.place_market_order("sell", balance["available"])
            if result["success"]:
                logger.info(f"Inventário vendido: ordem {result['order_id']}")
            else:
                logger.warning(
                    f"Falha ao vender inventário: {result['message']}"
                )

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
        inst_info = self.client.get_instrument_info()

        if balance["available"] > 0 and balance["available"] >= inst_info["min_size"]:
            print(
                f"  Vendendo {balance['available']} {pair_base} a mercado "
                f"(taxa tomador: {config.TAKER_FEE * 100}%)..."
            )
            result = self.client.place_market_order("sell", balance["available"])
            if result["success"]:
                print(f"  ✓ Posição fechada: ordem {result['order_id']}")
            else:
                print(f"  ✗ Falha ao fechar posição: {result['message']}")
        elif balance["available"] > 0:
            print(
                f"  ⚠ {balance['available']} {pair_base} restante é menor que o "
                f"mínimo ({inst_info['min_size']}). Não é possível vender."
            )
        else:
            print(f"  ✓ Sem posição aberta em {pair_base}")

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
                "range": f"-{config.GRID_RANGE_PERCENT * 2}%",
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
        3. Tenta recolocar ordens que falharam
        4. Recalibra se necessário
        5. Atualiza contadores
        """
        self.running = True
        last_recalibrate_check = 0
        last_retry_check = 0

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

                # 3. Retry de ordens que falharam (a cada 30s)
                now = time.time()
                if now - last_retry_check >= 30:
                    self._retry_failed_orders()
                    last_retry_check = now

                # 4. Recalibra se necessário
                if now - last_recalibrate_check >= config.RECALIBRATE_INTERVAL:
                    if self.check_recalibrate():
                        self.recalibrate()
                    last_recalibrate_check = now

                # 5. Atualiza contadores
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
