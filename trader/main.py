#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║              OKX GRID TRADING BOT - PONTO DE ENTRADA                       ║
║                                                                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  USO:                                                                      ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  python main.py              → Executa o bot com configuração padrão       ║
║  python main.py --test       → Testa conexão sem operar                    ║
║  python main.py --status     → Mostra último relatório de performance      ║
║                                                                            ║
║  ANTES DE EXECUTAR:                                                        ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  1. Copie .env.example para .env                                           ║
║  2. Preencha suas credenciais da OKX no .env                               ║
║  3. Ajuste os parâmetros em config.py                                      ║
║  4. Execute: pip install -r requirements.txt                               ║
║  5. RECOMENDADO: Comece com OKX_DEMO_TRADING=True no .env                  ║
║                                                                            ║
║  TAXAS OKX (Spot - Nível 1):                                               ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  • Maker (limit):  0.08% por ordem                                         ║
║  • Taker (market): 0.10% por ordem                                         ║
║  • Custo por ciclo grid: 0.16% (2x maker)                                  ║
║  • Lucro mínimo por ciclo: espaçamento_grid - 0.16%                        ║
║                                                                            ║
║  RISCOS:                                                                   ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  • Trading de criptomoedas envolve risco de perda total do capital         ║
║  • O bot NÃO garante lucros - mercado pode se mover contra o grid          ║
║  • Sempre comece no modo DEMO antes de usar dinheiro real                   ║
║  • Nunca invista mais do que pode perder                                    ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import sys
from pathlib import Path

import config
from grid_bot import GridBot
from dashboard import Dashboard


def setup_logging():
    """Configura logging para arquivo e terminal."""
    config.LOG_DIR.mkdir(exist_ok=True)
    log_path = config.LOG_DIR / config.LOG_FILE

    # Formato detalhado para arquivo
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # Formato simples para terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    console_handler.setFormatter(
        logging.Formatter("  %(levelname)-8s | %(message)s")
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def test_connection():
    """Testa conexão com a API sem operar."""
    from okx_client import OKXClient

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║              TESTE DE CONEXÃO COM A OKX                     ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    client = OKXClient()
    success = client.test_connection()

    if success:
        # Mostra detalhes adicionais
        ticker = client.get_ticker()
        if ticker:
            print(f"  Dados do Ticker {config.PAIR}:")
            print(f"    Último preço:  ${ticker['last']:>12,.2f}")
            print(f"    Bid (compra):  ${ticker['bid']:>12,.2f}")
            print(f"    Ask (venda):   ${ticker['ask']:>12,.2f}")
            print(f"    Alta 24h:      ${ticker['high_24h']:>12,.2f}")
            print(f"    Baixa 24h:     ${ticker['low_24h']:>12,.2f}")
            print(f"    Volume 24h:    {ticker['vol_24h']:>12,.2f}")

            spread = ticker['ask'] - ticker['bid']
            spread_pct = (spread / ticker['last']) * 100
            print(f"    Spread:        ${spread:>12,.4f} ({spread_pct:.4f}%)")

        # Mostra configuração do grid
        print(f"\n  Configuração do Grid:")
        grid_spacing = (config.GRID_RANGE_PERCENT * 2) / config.GRID_COUNT
        profit_per_cycle = grid_spacing - (config.ROUND_TRIP_FEE * 100)
        capital_per_grid = config.INVESTMENT_USDT / config.GRID_COUNT

        print(f"    Par:                  {config.PAIR}")
        print(f"    Capital:              ${config.INVESTMENT_USDT:,.2f}")
        print(f"    Grids:                {config.GRID_COUNT}")
        print(f"    Range:                ±{config.GRID_RANGE_PERCENT}%")
        print(f"    Espaçamento:          {grid_spacing:.4f}%")
        print(f"    Taxa por ciclo:       {config.ROUND_TRIP_FEE * 100:.4f}%")
        print(f"    Lucro por ciclo:      {profit_per_cycle:.4f}%")
        print(f"    Capital por grid:     ${capital_per_grid:,.2f}")
        print(f"    Lucro/ciclo (USD):    ${capital_per_grid * profit_per_cycle / 100:,.4f}")
        print(f"    Stop Loss:            -{config.STOP_LOSS_PERCENT}%")
        print(f"    Take Profit:          +{config.TAKE_PROFIT_PERCENT}%")
        print(f"    Modo:                 {'DEMO' if config.DEMO_TRADING else 'PRODUCAO'}")

    return success


def show_status():
    """Mostra último relatório de performance."""
    report_path = config.LOG_DIR / config.PERFORMANCE_FILE

    if not report_path.exists():
        print("\n  Nenhum relatório encontrado. Execute o bot primeiro.\n")
        return

    with open(report_path) as f:
        report = json.load(f)

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║              ÚLTIMO RELATÓRIO DE PERFORMANCE                ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    for section, data in report.items():
        print(f"  [{section.upper()}]")
        for key, value in data.items():
            print(f"    {key:.<30} {value}")
        print()


def main():
    """Ponto de entrada principal."""

    # Argumentos de linha de comando
    if "--test" in sys.argv:
        setup_logging()
        test_connection()
        return

    if "--status" in sys.argv:
        show_status()
        return

    # Banner
    print()
    print("  ╔═══════════════════════════════════════════════════════════╗")
    print("  ║                                                         ║")
    print("  ║          OKX GRID TRADING BOT v1.0                      ║")
    print("  ║          Estrategia: Grid Trading (Spot)                ║")
    print("  ║                                                         ║")
    print("  ║   Taxas:   Maker 0.08% | Taker 0.10%                   ║")
    print("  ║   Custo:   0.16% por ciclo (compra+venda)              ║")
    print("  ║                                                         ║")
    print("  ╚═══════════════════════════════════════════════════════════╝")
    print()

    # Setup
    setup_logging()
    logger = logging.getLogger("Main")

    # Inicializa o bot
    bot = GridBot()

    if not bot.initialize():
        logger.error("Falha na inicialização. Verifique o .env e config.py")
        sys.exit(1)

    # Configura o grid
    if not bot.setup_grid():
        logger.error("Falha ao configurar o grid. Verifique saldo e configuração.")
        sys.exit(1)

    # Inicia dashboard
    dashboard = Dashboard(bot)
    dashboard.start()

    # Executa o bot
    try:
        bot.run()
    except Exception as e:
        logger.exception(f"Erro fatal: {e}")
        bot.emergency_close(f"Erro fatal: {e}")
    finally:
        dashboard.stop()
        print("\n  Obrigado por usar o OKX Grid Trading Bot!")
        print(f"  Logs salvos em: {config.LOG_DIR}")
        print(f"  Relatório: {config.LOG_DIR / config.PERFORMANCE_FILE}")
        print()


if __name__ == "__main__":
    main()
