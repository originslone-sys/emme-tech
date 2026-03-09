"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     OKX API CLIENT - WRAPPER COMPLETO                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Cliente para a API REST da OKX com:                                       ║
║  • Autenticação HMAC-SHA256                                                ║
║  • Rate limiting automático                                                ║
║  • Retry com backoff exponencial                                           ║
║  • Logging detalhado de todas as operações                                 ║
║  • Suporte a Demo Trading (testnet)                                        ║
║                                                                            ║
║  Endpoints utilizados:                                                     ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  GET  /api/v5/market/ticker        → Preço atual do par                    ║
║  GET  /api/v5/account/balance      → Saldo da conta                        ║
║  POST /api/v5/trade/order          → Criar ordem                           ║
║  POST /api/v5/trade/cancel-order   → Cancelar ordem                        ║
║  GET  /api/v5/trade/orders-pending → Ordens abertas                        ║
║  GET  /api/v5/trade/order          → Status de uma ordem                   ║
║  GET  /api/v5/public/instruments   → Info do par (precisão, mínimos)       ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hmac
import hashlib
import base64
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

import config

logger = logging.getLogger("OKXClient")


class OKXClient:
    """
    Cliente para a API REST v5 da OKX.

    Todas as ordens do bot são LIMIT (maker) para pagar a menor taxa possível.
    Taxa maker OKX: 0.08% | Taxa taker: 0.10%
    """

    BASE_URL = "https://www.okx.com"

    def __init__(self):
        self.api_key = config.API_KEY
        self.secret_key = config.SECRET_KEY
        self.passphrase = config.PASSPHRASE
        self.demo = config.DEMO_TRADING

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "OK-ACCESS-KEY": self.api_key,
        })

        # Flag de demo trading
        if self.demo:
            self.session.headers["x-simulated-trading"] = "1"
            logger.info("Modo DEMO ativado - operações simuladas")

        # Cache de informações do instrumento
        self._instrument_cache = {}

        # Contadores para rate limiting
        self._request_count = 0
        self._request_window_start = time.time()

    # ═══════════════════════════════════════════════════════════════════════
    #  AUTENTICAÇÃO
    # ═══════════════════════════════════════════════════════════════════════

    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """
        Gera assinatura HMAC-SHA256 para autenticação na API.

        Formato: BASE64(HMAC-SHA256(secret, timestamp + method + path + body))
        """
        message = timestamp + method.upper() + path + body
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        )
        return base64.b64encode(signature.digest()).decode("utf-8")

    def _get_timestamp(self) -> str:
        """Retorna timestamp ISO 8601 UTC para a API."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _rate_limit(self):
        """
        Rate limiting: máximo 20 requests por segundo (limite OKX).
        Pausa automaticamente se exceder o limite.
        """
        now = time.time()
        if now - self._request_window_start >= 1.0:
            self._request_count = 0
            self._request_window_start = now

        self._request_count += 1
        if self._request_count > 18:  # margem de segurança
            sleep_time = 1.0 - (now - self._request_window_start)
            if sleep_time > 0:
                logger.debug(f"Rate limit: aguardando {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self._request_count = 0
                self._request_window_start = time.time()

    # ═══════════════════════════════════════════════════════════════════════
    #  REQUESTS
    # ═══════════════════════════════════════════════════════════════════════

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
        max_retries: int = 3,
    ) -> dict:
        """
        Executa request autenticado com retry e backoff exponencial.

        Returns:
            dict com a resposta da API. Campo 'code' == '0' indica sucesso.
        """
        self._rate_limit()

        url = self.BASE_URL + path

        # Query string para GET
        if method == "GET" and params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            path_with_query = path + "?" + query if query else path
            url = self.BASE_URL + path_with_query
        else:
            path_with_query = path

        body_str = json.dumps(body) if body else ""

        for attempt in range(max_retries):
            try:
                timestamp = self._get_timestamp()
                sign = self._sign(timestamp, method, path_with_query, body_str)

                headers = {
                    "OK-ACCESS-SIGN": sign,
                    "OK-ACCESS-TIMESTAMP": timestamp,
                    "OK-ACCESS-PASSPHRASE": self.passphrase,
                }

                if method == "GET":
                    resp = self.session.get(url, headers=headers, timeout=10)
                else:
                    resp = self.session.post(
                        url, headers=headers, data=body_str, timeout=10
                    )

                data = resp.json()

                if data.get("code") != "0":
                    error_msg = data.get("msg", "Erro desconhecido")
                    logger.error(
                        f"API Error [{data.get('code')}]: {error_msg} "
                        f"| {method} {path}"
                    )

                return data

            except requests.exceptions.RequestException as e:
                wait = 2 ** (attempt + 1)
                logger.warning(
                    f"Request falhou (tentativa {attempt + 1}/{max_retries}): {e} "
                    f"| Retry em {wait}s"
                )
                if attempt < max_retries - 1:
                    time.sleep(wait)

        logger.error(f"Request falhou após {max_retries} tentativas: {method} {path}")
        return {"code": "-1", "msg": "Max retries exceeded", "data": []}

    # ═══════════════════════════════════════════════════════════════════════
    #  MARKET DATA
    # ═══════════════════════════════════════════════════════════════════════

    def get_ticker(self, pair: str = None) -> dict:
        """
        Obtém preço atual e dados do ticker.

        Returns:
            {
                'last': float,     # Último preço
                'bid': float,      # Melhor oferta de compra
                'ask': float,      # Melhor oferta de venda
                'high_24h': float, # Máxima 24h
                'low_24h': float,  # Mínima 24h
                'vol_24h': float,  # Volume 24h
            }
        """
        pair = pair or config.PAIR
        data = self._request("GET", "/api/v5/market/ticker", {"instId": pair})

        if data["code"] == "0" and data["data"]:
            t = data["data"][0]
            return {
                "last": float(t["last"]),
                "bid": float(t["bidPx"]),
                "ask": float(t["askPx"]),
                "high_24h": float(t["high24h"]),
                "low_24h": float(t["low24h"]),
                "vol_24h": float(t["vol24h"]),
                "timestamp": t["ts"],
            }
        return {}

    def get_instrument_info(self, pair: str = None) -> dict:
        """
        Obtém informações do instrumento (precisão, tamanhos mínimos).
        Resultado é cacheado para evitar requests desnecessários.

        Returns:
            {
                'tick_size': float,   # Menor incremento de preço
                'lot_size': float,    # Menor incremento de quantidade
                'min_size': float,    # Quantidade mínima por ordem
                'price_precision': int,
                'qty_precision': int,
            }
        """
        pair = pair or config.PAIR

        if pair in self._instrument_cache:
            return self._instrument_cache[pair]

        data = self._request(
            "GET",
            "/api/v5/public/instruments",
            {"instType": "SPOT", "instId": pair},
        )

        if data["code"] == "0" and data["data"]:
            info = data["data"][0]
            tick_size = float(info["tickSz"])
            lot_size = float(info["lotSz"])

            result = {
                "tick_size": tick_size,
                "lot_size": lot_size,
                "min_size": float(info["minSz"]),
                "price_precision": len(str(tick_size).rstrip("0").split(".")[-1]),
                "qty_precision": len(str(lot_size).rstrip("0").split(".")[-1]),
            }
            self._instrument_cache[pair] = result
            logger.info(
                f"Instrumento {pair}: tick={tick_size}, lot={lot_size}, "
                f"min={result['min_size']}"
            )
            return result

        return {
            "tick_size": 0.01,
            "lot_size": 0.000001,
            "min_size": 0.001,
            "price_precision": config.PRICE_PRECISION,
            "qty_precision": config.QTY_PRECISION,
        }

    # ═══════════════════════════════════════════════════════════════════════
    #  ACCOUNT
    # ═══════════════════════════════════════════════════════════════════════

    def get_balance(self, currency: str = "USDT") -> dict:
        """
        Obtém saldo da conta para uma moeda específica.

        Returns:
            {
                'available': float,  # Saldo disponível para trade
                'frozen': float,     # Saldo em ordens abertas
                'total': float,      # Saldo total
            }
        """
        data = self._request("GET", "/api/v5/account/balance", {"ccy": currency})

        if data["code"] == "0" and data["data"]:
            details = data["data"][0].get("details", [])
            for d in details:
                if d["ccy"] == currency:
                    return {
                        "available": float(d.get("availBal", 0)),
                        "frozen": float(d.get("frozenBal", 0)),
                        "total": float(d.get("cashBal", 0)),
                    }

        return {"available": 0.0, "frozen": 0.0, "total": 0.0}

    # ═══════════════════════════════════════════════════════════════════════
    #  TRADING
    # ═══════════════════════════════════════════════════════════════════════

    def place_limit_order(
        self,
        side: str,
        price: float,
        size: float,
        pair: str = None,
        client_order_id: str = None,
    ) -> dict:
        """
        Coloca ordem LIMIT (maker) - taxa de 0.08%.

        Args:
            side: 'buy' ou 'sell'
            price: Preço da ordem
            size: Quantidade em moeda base (ex: ETH)
            pair: Par de negociação (default: config.PAIR)
            client_order_id: ID customizado para rastrear a ordem

        Returns:
            {
                'order_id': str,         # ID da ordem na OKX
                'client_order_id': str,  # ID customizado
                'success': bool,
                'message': str,
            }
        """
        pair = pair or config.PAIR
        info = self.get_instrument_info(pair)

        # Arredonda preço e quantidade conforme precisão do instrumento
        price = round(price, info["price_precision"])
        size = round(size, info["qty_precision"])

        # Valida tamanho mínimo
        if size < info["min_size"]:
            logger.warning(
                f"Ordem ignorada: size {size} < min {info['min_size']} para {pair}"
            )
            return {
                "order_id": "",
                "client_order_id": client_order_id or "",
                "success": False,
                "message": f"Tamanho mínimo não atingido: {size} < {info['min_size']}",
            }

        body = {
            "instId": pair,
            "tdMode": "cash",      # Spot trading (sem margem)
            "side": side,
            "ordType": "limit",    # SEMPRE limit para pagar maker fee (0.08%)
            "px": str(price),
            "sz": str(size),
        }

        if client_order_id:
            body["clOrdId"] = client_order_id

        # Cálculo de taxa estimada para logging
        order_value_usdt = price * size
        estimated_fee = order_value_usdt * config.MAKER_FEE

        logger.info(
            f"Ordem {side.upper()} | {pair} | "
            f"Preço: ${price:,.2f} | Qty: {size} | "
            f"Valor: ${order_value_usdt:,.2f} | "
            f"Taxa estimada: ${estimated_fee:,.4f} ({config.MAKER_FEE * 100}%)"
        )

        data = self._request("POST", "/api/v5/trade/order", body=body)

        if data["code"] == "0" and data["data"]:
            order = data["data"][0]
            order_id = order.get("ordId", "")
            logger.info(f"Ordem criada com sucesso: {order_id}")
            return {
                "order_id": order_id,
                "client_order_id": order.get("clOrdId", ""),
                "success": True,
                "message": "OK",
            }

        error_msg = data.get("msg", "")
        if data.get("data"):
            error_msg = data["data"][0].get("sMsg", error_msg)
        logger.error(f"Falha ao criar ordem: {error_msg}")
        return {
            "order_id": "",
            "client_order_id": client_order_id or "",
            "success": False,
            "message": error_msg,
        }

    def place_market_order(self, side: str, size: float, pair: str = None) -> dict:
        """
        Ordem MARKET (taker) - taxa de 0.10%.
        Usada APENAS em emergências (stop loss, take profit).

        Args:
            side: 'buy' ou 'sell'
            size: Quantidade em moeda base
        """
        pair = pair or config.PAIR
        info = self.get_instrument_info(pair)
        size = round(size, info["qty_precision"])

        body = {
            "instId": pair,
            "tdMode": "cash",
            "side": side,
            "ordType": "market",
            "sz": str(size),
        }

        logger.warning(
            f"ORDEM MARKET (emergência) | {side.upper()} {size} {pair} | "
            f"Taxa: {config.TAKER_FEE * 100}%"
        )

        data = self._request("POST", "/api/v5/trade/order", body=body)

        if data["code"] == "0" and data["data"]:
            return {
                "order_id": data["data"][0].get("ordId", ""),
                "success": True,
                "message": "OK",
            }

        return {"order_id": "", "success": False, "message": data.get("msg", "")}

    def cancel_order(self, order_id: str, pair: str = None) -> bool:
        """Cancela uma ordem específica."""
        pair = pair or config.PAIR
        data = self._request(
            "POST",
            "/api/v5/trade/cancel-order",
            body={"instId": pair, "ordId": order_id},
        )
        success = data["code"] == "0"
        if success:
            logger.info(f"Ordem cancelada: {order_id}")
        else:
            logger.error(f"Falha ao cancelar ordem {order_id}: {data.get('msg')}")
        return success

    def cancel_all_orders(self, pair: str = None) -> int:
        """
        Cancela TODAS as ordens abertas para o par.
        Retorna quantidade de ordens canceladas.
        """
        pair = pair or config.PAIR
        pending = self.get_pending_orders(pair)
        cancelled = 0

        for order in pending:
            if self.cancel_order(order["order_id"], pair):
                cancelled += 1

        logger.info(f"Total de ordens canceladas: {cancelled}/{len(pending)}")
        return cancelled

    def get_pending_orders(self, pair: str = None) -> list:
        """
        Lista todas as ordens abertas (pendentes).

        Returns:
            Lista de dicts com info de cada ordem:
            [{'order_id', 'side', 'price', 'size', 'filled', 'status', 'created'}]
        """
        pair = pair or config.PAIR
        data = self._request(
            "GET", "/api/v5/trade/orders-pending", {"instId": pair, "instType": "SPOT"}
        )

        orders = []
        if data["code"] == "0" and data["data"]:
            for o in data["data"]:
                orders.append({
                    "order_id": o["ordId"],
                    "client_order_id": o.get("clOrdId", ""),
                    "side": o["side"],
                    "price": float(o["px"]),
                    "size": float(o["sz"]),
                    "filled": float(o.get("accFillSz", 0)),
                    "status": o["state"],
                    "created": o.get("cTime", ""),
                })

        return orders

    def get_order_status(self, order_id: str, pair: str = None) -> dict:
        """Verifica status de uma ordem específica."""
        pair = pair or config.PAIR
        data = self._request(
            "GET",
            "/api/v5/trade/order",
            {"instId": pair, "ordId": order_id},
        )

        if data["code"] == "0" and data["data"]:
            o = data["data"][0]
            return {
                "order_id": o["ordId"],
                "side": o["side"],
                "price": float(o["px"]),
                "size": float(o["sz"]),
                "filled": float(o.get("accFillSz", 0)),
                "avg_price": float(o["avgPx"]) if o.get("avgPx") else 0,
                "fee": float(o.get("fee", 0)),
                "status": o["state"],  # live, partially_filled, filled, canceled
            }

        return {}

    # ═══════════════════════════════════════════════════════════════════════
    #  UTILITÁRIOS
    # ═══════════════════════════════════════════════════════════════════════

    def test_connection(self) -> bool:
        """Testa conexão com a API e valida credenciais."""
        print("\n  Testando conexão com OKX...")

        # Teste 1: API pública (não precisa auth)
        ticker = self.get_ticker()
        if not ticker:
            print("  ✗ Falha ao acessar API pública")
            return False
        print(f"  ✓ API pública OK | {config.PAIR}: ${ticker['last']:,.2f}")

        # Teste 2: API privada (precisa auth)
        balance = self.get_balance()
        if balance["total"] == 0 and balance["available"] == 0:
            print("  ⚠ Saldo USDT: $0.00 (conta vazia ou credenciais inválidas)")
        else:
            print(
                f"  ✓ API privada OK | Saldo USDT: "
                f"${balance['available']:,.2f} disponível / "
                f"${balance['total']:,.2f} total"
            )

        # Teste 3: Info do instrumento
        info = self.get_instrument_info()
        if info:
            print(
                f"  ✓ Instrumento OK | "
                f"Tick: {info['tick_size']} | "
                f"Lot: {info['lot_size']} | "
                f"Min: {info['min_size']}"
            )

        print("  Conexão estabelecida com sucesso!\n")
        return True
