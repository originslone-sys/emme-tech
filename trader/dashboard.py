"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DASHBOARD EM TEMPO REAL - TERMINAL                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Exibe no terminal:                                                        ║
║  • Status do bot e tempo de execução                                       ║
║  • Preço atual e range do grid                                             ║
║  • Lucro/prejuízo em tempo real (bruto, taxas, líquido)                    ║
║  • Estatísticas de trades (win rate, melhor, pior)                         ║
║  • Controle de risco (drawdown, perda diária)                              ║
║  • Ordens ativas (compra/venda)                                            ║
║  • Últimos trades executados                                               ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import threading
import time

import config


class Dashboard:
    """Dashboard em tempo real no terminal."""

    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self._thread = None

    def start(self):
        """Inicia o dashboard em uma thread separada."""
        if not config.SHOW_DASHBOARD:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Para o dashboard."""
        self.running = False

    def _loop(self):
        """Loop de atualização do dashboard."""
        while self.running:
            try:
                self._render()
            except Exception:
                pass
            time.sleep(config.DASHBOARD_REFRESH)

    def _render(self):
        """Renderiza o dashboard no terminal."""
        stats = self.bot.get_stats()

        # Limpa terminal
        os.system("clear" if os.name != "nt" else "cls")

        # Indicadores de cor (usando caracteres ASCII)
        profit_indicator = "+" if stats["net_profit"] >= 0 else "-"
        roi_indicator = "+" if stats["roi"] >= 0 else "-"

        mode_label = "DEMO" if stats["mode"] == "DEMO" else "$$$ LIVE $$$"

        # Header
        print("╔══════════════════════════════════════════════════════════════════╗")
        print(f"║   OKX GRID TRADING BOT   |   {mode_label:^14}   |   {stats['pair']:<10}  ║")
        print("╠══════════════════════════════════════════════════════════════════╣")

        # Status
        status = "EM EXECUCAO" if stats["running"] else "PARADO"
        print(f"║  Status: {status:<16} Tempo: {stats['runtime']:<26}  ║")
        print("╠══════════════════════════════════════════════════════════════════╣")

        # Preço e Grid
        print("║  MERCADO                                                        ║")
        print(f"║  Preco Atual:     ${stats['current_price']:>12,.2f}                          ║")
        print(f"║  Grid Inferior:   ${stats['grid_lower']:>12,.2f}                          ║")
        print(f"║  Grid Superior:   ${stats['grid_upper']:>12,.2f}                          ║")

        # Barra visual de posição do preço no grid
        if stats["grid_upper"] > stats["grid_lower"]:
            position = (stats["current_price"] - stats["grid_lower"]) / (
                stats["grid_upper"] - stats["grid_lower"]
            )
            position = max(0, min(1, position))
            bar_width = 40
            filled = int(position * bar_width)
            bar = "=" * filled + "O" + "-" * (bar_width - filled)
            print(f"║  [{bar}]  ║")
        print("╠══════════════════════════════════════════════════════════════════╣")

        # Capital e Lucro
        print("║  FINANCEIRO                                                     ║")
        print(f"║  Capital Inicial: ${stats['initial_capital']:>12,.2f}                          ║")
        print(f"║  Capital Atual:   ${stats['current_capital']:>12,.2f}                          ║")
        print(f"║  Lucro Bruto:     ${stats['gross_profit']:>+12,.4f}                          ║")
        print(f"║  Total Taxas:     ${stats['total_fees']:>12,.4f}   ({config.MAKER_FEE*100:.2f}% maker)      ║")
        print(f"║  LUCRO LIQUIDO:   ${stats['net_profit']:>+12,.4f}                          ║")
        print(f"║  ROI:             {stats['roi']:>+12.4f}%                          ║")
        print("╠══════════════════════════════════════════════════════════════════╣")

        # Trades
        print("║  TRADES                                                         ║")
        print(f"║  Total:           {stats['total_trades']:>12}                          ║")
        print(f"║  Positivos:       {stats['winning_trades']:>12}                          ║")
        print(f"║  Negativos:       {stats['losing_trades']:>12}                          ║")
        print(f"║  Win Rate:        {stats['win_rate']:>11.2f}%                          ║")
        print(f"║  Melhor Trade:    ${stats['best_trade']:>+12,.4f}                          ║")
        print(f"║  Pior Trade:      ${stats['worst_trade']:>+12,.4f}                          ║")
        print("╠══════════════════════════════════════════════════════════════════╣")

        # Risco
        print("║  RISCO                                                          ║")
        print(f"║  Max Drawdown:    ${stats['max_drawdown']:>12,.4f}  ({stats['max_drawdown_pct']:.2f}%)          ║")
        print(f"║  Perda Diaria:    ${stats['daily_loss']:>12,.4f}  (max: ${config.MAX_DAILY_LOSS_USDT:.2f})     ║")
        print(f"║  Recalibracoes:   {stats['recalibrations']:>12}                          ║")
        print("╠══════════════════════════════════════════════════════════════════╣")

        # Ordens ativas
        print("║  ORDENS ATIVAS                                                  ║")
        print(f"║  Compra:          {stats['active_buys']:>12}                          ║")
        print(f"║  Venda:           {stats['active_sells']:>12}                          ║")
        print(f"║  Total:           {stats['active_buys'] + stats['active_sells']:>12}                          ║")
        print("╠══════════════════════════════════════════════════════════════════╣")

        # Últimos trades
        print("║  ULTIMOS TRADES                                                 ║")
        recent = self.bot.stats.trades_history[-5:] if self.bot.stats.trades_history else []
        if recent:
            for t in reversed(recent):
                ts = t.timestamp[11:19]  # HH:MM:SS
                print(
                    f"║  {ts} | "
                    f"${t.buy_price:>9,.2f} -> ${t.sell_price:>9,.2f} | "
                    f"Liq: ${t.net_profit_usdt:>+8.4f}        ║"
                )
        else:
            print("║  Nenhum trade executado ainda...                                ║")

        print("╠══════════════════════════════════════════════════════════════════╣")
        print("║  Ctrl+C para encerrar o bot com seguranca                       ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
