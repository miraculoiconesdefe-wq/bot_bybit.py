# ==========================================================
# bot_bybit.py
# Bot de DCA + Rebalanceamento para Bybit (Spot)
# ==========================================================
#
# ANTES DE RODAR:
# 1. Substitua API_KEY e API_SECRET pelas suas chaves da Bybit
#    (criadas com permissão "Leitura e gravação" + SPOT > Trade)
# 2. Ajuste APORTE_USD para o valor em dólares do aporte mensal
# 3. Ajuste CARTEIRA se quiser mudar os percentuais alvo
# 4. Rode primeiro com APORTE_USD baixo (ex: 5) para testar
# ==========================================================

API_KEY    = "06pgxn0TvygSN86oIy"
API_SECRET = "oQbVzupOlc3W6JooKMK8uYm8GoHv10UvtCpo"

# Valor em USDT por ciclo (~R$ 500 / cotação do dólar)
APORTE_USD = 95

# Desvio máximo antes de rebalancear (5% = 0.05)
DESVIO_MAX = 0.05

# Carteira alvo - os percentuais devem somar 1.0 (100%)
CARTEIRA = {
    "BTCUSDT":  0.40,
    "ETHUSDT":  0.25,
    "STXUSDT":  0.15,
    "MNTUSDT":  0.10,
    "LINKUSDT": 0.10,
}

# Modo de simulação: True = não executa ordens reais, só mostra o que faria
MODO_SIMULACAO = True

# ==========================================================
# NÃO PRECISA MEXER ABAIXO DESTA LINHA
# ==========================================================

from pybit.unified_trading import HTTP
from datetime import datetime

session = HTTP(api_key=API_KEY, api_secret=API_SECRET)


def get_preco(symbol):
    r = session.get_tickers(category="spot", symbol=symbol)
    return float(r["result"]["list"][0]["lastPrice"])


def get_saldos():
    """Retorna dict {symbol: valor_em_usdt} para cada moeda da carteira."""
    r = session.get_wallet_balance(accountType="UNIFIED")
    coin_balances = {c["coin"]: float(c["walletBalance"]) for c in r["result"]["list"][0]["coin"]}

    saldos_usdt = {}
    for symbol in CARTEIRA:
        coin = symbol.replace("USDT", "")
        qty = coin_balances.get(coin, 0.0)
        preco = get_preco(symbol)
        saldos_usdt[symbol] = qty * preco
    return saldos_usdt


def executar():
    print(f"\n[{datetime.now():%d/%m/%Y %H:%M}] Iniciando ciclo DCA + Rebalanceamento")
    print(f"Modo: {'SIMULAÇÃO (nenhuma ordem real será enviada)' if MODO_SIMULACAO else 'REAL'}")

    precos = {s: get_preco(s) for s in CARTEIRA}
    saldos = get_saldos()
    total_atual = sum(saldos.values())
    total_pos_aporte = total_atual + APORTE_USD

    print(f"\nPatrimônio atual: ${total_atual:.2f}")
    print(f"Aporte deste ciclo: ${APORTE_USD:.2f}")
    print("-" * 50)

    for symbol, alvo_pct in CARTEIRA.items():
        valor_atual = saldos.get(symbol, 0.0)
        pct_atual = valor_atual / total_pos_aporte if total_pos_aporte > 0 else 0
        desvio = pct_atual - alvo_pct

        # Compra base proporcional ao alvo
        compra = APORTE_USD * alvo_pct

        # Se o ativo está abaixo do alvo (desvio negativo) além do threshold,
        # direciona parte extra do aporte para corrigir
        if desvio < -DESVIO_MAX:
            compra += APORTE_USD * abs(desvio)

        qty = round(compra / precos[symbol], 6)

        print(
            f"{symbol:10s} | atual: {pct_atual*100:5.1f}% | alvo: {alvo_pct*100:5.1f}% "
            f"| desvio: {desvio*100:+5.1f}% | compra: ${compra:6.2f} ({qty} unid.)"
        )

        if qty <= 0:
            continue

        if MODO_SIMULACAO:
            print(f"   -> [SIMULAÇÃO] ordem NÃO enviada")
        else:
            session.place_order(
                category="spot",
                symbol=symbol,
                side="Buy",
                orderType="Market",
                qty=str(qty),
            )
            print(f"   -> Ordem enviada com sucesso")

    print("-" * 50)
    print("Ciclo concluído.\n")


if __name__ == "__main__":
    executar()
