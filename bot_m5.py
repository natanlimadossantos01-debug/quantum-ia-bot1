#!/usr/bin/env python3
"""
⚛️ QUANTUM TRIPLE M1 v2 - MULTI-CONFLUÊNCIA (REFATORADO)
🎯 4 Confluências: EMA9/EMA21, RSI Wilder, Força do Candle, Rompimento
💪 Mínimo 3 confirmações
📊 6 Pares OTC + 6 Pares Mercado Aberto (SOMENTE MOEDAS)
⏱️ M1
🔄 Gale 1.5x

MELHORIAS v2:
✅ RSI com suavização de Wilder (igual ao gráfico)
✅ Monitor de resultado por timestamp de FECHAMENTO (confiável)
✅ Validação de payout antes de enviar sinal
✅ Deduplicação de sinal por ativo
✅ Filtro de horário (OTC e Forex)
✅ Confiança calculada com base real (distância EMAs + RSI)
✅ Filtro de ATR mínimo (evita mercado morto)
✅ Tratamento de empate (doji)
✅ Rompimento realista
✅ Logs de erro úteis (sem except: pass cego)
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# ═══════════════════════════════════════════
# ⚙️ CONFIGURAÇÕES
# ═══════════════════════════════════════════
INTERVALO_MINIMO = 300          # segundos entre sinais POR ATIVO
USAR_GALE = True
MULTIPLICADOR_GALE = 1.5
ANTECEDENCIA = 10               # segundos antes da entrada
TIMEFRAME = 60
CONFIANCA_MINIMA = 70
PAYOUT_MINIMO = 80              # % mínimo de payout para operar
ATR_MINIMO_RELATIVO = 0.00002   # ATR mínimo absoluto (mercado morto)
MIN_CONFLUENCIAS = 3


def banner():
    print("⚛️ QUANTUM TRIPLE M1 v2 - Multi-Confluência")


def carregar_config():
    token = os.environ.get('TELEGRAM_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    email = os.environ.get('IQ_EMAIL')
    senha = os.environ.get('IQ_SENHA')

    if token and chat and email and senha:
        banner()
        print("✅ Modo CLOUD detectado!")
        return {"token": token, "chat": chat, "email": email, "senha": senha}

    print("❌ Configure as variáveis de ambiente!")
    sys.exit(1)


cfg = carregar_config()
TOKEN = cfg['token']
CHAT = cfg['chat']
EMAIL = cfg['email']
SENHA = cfg['senha']

from iqoptionapi.stable_api import IQ_Option

# ═══════════════════════════════════════════
# 📊 ATIVOS - SOMENTE MOEDAS (OTC + MERCADO ABERTO)
# ═══════════════════════════════════════════
ATIVOS_OTC = {
    "EURUSD-OTC": "EURUSD-OTC",
    "GBPUSD-OTC": "GBPUSD-OTC",
    "USDJPY-OTC": "USDJPY-OTC",
    "AUDUSD-OTC": "AUDUSD-OTC",
    "USDCAD-OTC": "USDCAD-OTC",
    "EURGBP-OTC": "EURGBP-OTC"
}

ATIVOS_MERCADO = {
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "EURGBP": "EURGBP"
}


class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c

    def send(self, txt):
        try:
            requests.post(
                f"{self.url}/sendMessage",
                json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"},
                timeout=10
            )
        except Exception as e:
            print(f"⚠️ Telegram erro: {e}")


# ═══════════════════════════════════════════
# 📊 INDICADORES
# ═══════════════════════════════════════════
def ema(fechamentos, periodo):
    if len(fechamentos) < periodo:
        return None
    fator = 2 / (periodo + 1)
    valor = float(np.mean(fechamentos[:periodo]))
    for f in fechamentos[periodo:]:
        valor = float(f) * fator + valor * (1 - fator)
    return valor


def calcular_rsi(velas, periodo=14):
    """RSI com suavização de Wilder (igual ao gráfico)."""
    fechamentos = np.array([v["close"] for v in velas], dtype=float)
    if len(fechamentos) <= periodo:
        return 50.0

    deltas = np.diff(fechamentos)
    ganhos = np.where(deltas > 0, deltas, 0.0)
    perdas = np.where(deltas < 0, -deltas, 0.0)

    avg_ganho = ganhos[:periodo].mean()
    avg_perda = perdas[:periodo].mean()

    for i in range(periodo, len(deltas)):
        avg_ganho = (avg_ganho * (periodo - 1) + ganhos[i]) / periodo
        avg_perda = (avg_perda * (periodo - 1) + perdas[i]) / periodo

    if avg_perda == 0:
        return 100.0
    rs = avg_ganho / avg_perda
    return float(100 - (100 / (1 + rs)))


def calcular_atr(velas, periodo=14):
    if len(velas) <= periodo:
        return 0.0

    trs = []
    anteriores = velas[-periodo - 1:-1]
    atuais = velas[-periodo:]

    for anterior, atual in zip(anteriores, atuais):
        tr = max(
            atual["high"] - atual["low"],
            abs(atual["high"] - anterior["close"]),
            abs(atual["low"] - anterior["close"])
        )
        trs.append(tr)

    return float(np.mean(trs))


# ═══════════════════════════════════════════
# 🎯 ESTRATÉGIA
# ═══════════════════════════════════════════
def quantum_triple(velas):
    """Analisa velas e retorna sinal ou None."""
    if len(velas) < 30:
        return None

    fechamentos = [v["close"] for v in velas]
    atual = velas[-1]
    anterior = velas[-2]

    ema_9 = ema(fechamentos, 9)
    ema_21 = ema(fechamentos, 21)
    valor_rsi = calcular_rsi(velas)
    valor_atr = calcular_atr(velas)

    if ema_9 is None or ema_21 is None or valor_atr <= 0:
        return None

    # Filtro de mercado morto
    if valor_atr < ATR_MINIMO_RELATIVO:
        return None

    conf_call = 0
    conf_put = 0

    # 1) Tendência pelas EMAs
    if ema_9 > ema_21:
        conf_call += 1
    elif ema_9 < ema_21:
        conf_put += 1

    # 2) Momentum pelo RSI
    if valor_rsi >= 52:
        conf_call += 1
    elif valor_rsi <= 48:
        conf_put += 1

    # 3) Força do candle (corpo relevante vs ATR)
    corpo = atual["close"] - atual["open"]
    if corpo > 0 and abs(corpo) >= valor_atr * 0.15:
        conf_call += 1
    elif corpo < 0 and abs(corpo) >= valor_atr * 0.15:
        conf_put += 1

    # 4) Rompimento realista (máxima supera máxima anterior / mínima supera mínima)
    if atual["high"] > anterior["high"] and atual["close"] > atual["open"]:
        conf_call += 1
    elif atual["low"] < anterior["low"] and atual["close"] < atual["open"]:
        conf_put += 1

    if conf_call > conf_put:
        direcao = "CALL"
        total = conf_call
    elif conf_put > conf_call:
        direcao = "PUT"
        total = conf_put
    else:
        return None

    if total < MIN_CONFLUENCIAS:
        return None

    # ── Confiança REAL (baseada em forças mensuráveis) ──
    dist_ema = abs(ema_9 - ema_21) / valor_atr
    forca_tendencia = min(1.0, dist_ema / 1.5)

    forca_rsi = abs(valor_rsi - 50) / 50

    confianca = int(
        50
        + total * 8
        + forca_tendencia * 15
        + forca_rsi * 10
    )
    confianca = max(0, min(95, confianca))

    return {
        "direction": direcao,
        "confidence": confianca,
        "confluences": total,
        "rsi": round(valor_rsi, 2),
    }


# ═══════════════════════════════════════════
# 🤖 BOT
# ═══════════════════════════════════════════
class Bot:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)

        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.velas.update({nome: deque(maxlen=100) for nome in ATIVOS_MERCADO})

        self.iq_api = None
        self.placar = {'w': 0, 'g1': 0, 'l': 0, 'e': 0}
        self.ult_sinal = {}          # dict: ativo -> timestamp
        self.sinais = 0
        self.ultimo_dia = datetime.now(FUSO_BR).day
        self._monitorando = set()    # ativos com monitor rodando (evita race)

    # ── Conexão ─────────────────────────────
    def conectar_iq(self):
        try:
            if self.iq_api:
                try:
                    self.iq_api.close()
                except Exception:
                    pass
            self.iq_api = IQ_Option(EMAIL, SENHA)
            check, _ = self.iq_api.connect()
            if check:
                print("✅ Conectado à IQ Option.")
                return self.iq_api
            print("❌ Falha na conexão.")
            return None
        except Exception as e:
            print(f"❌ Erro conexão: {e}")
            return None

    async def reconectar_se_necessario(self):
        if self.iq_api is None or not self.iq_api.check_connect():
            print("🔄 Reconectando...")
            return self.conectar_iq()
        return self.iq_api

    # ── Filtros ─────────────────────────────
    def horario_valido(self, ativo):
        h = datetime.now(FUSO_BR).hour
        if ativo.endswith("-OTC"):
            return 6 <= h <= 23
        else:
            # Forex aberto: Londres + NY (aprox)
            return 5 <= h <= 18

    def payout_ok(self, ativo, minimo=PAYOUT_MINIMO):
        try:
            if not self.iq_api or not self.iq_api.check_connect():
                return True  # em dúvida, deixa passar
            payouts = self.iq_api.get_all_profit()
            # chave sem "-OTC"
            base = ativo.replace("-OTC", "")
            info = payouts.get(base, {}) if payouts else {}
            if not info:
                return True
            melhor = max(info.values()) if info else 0
            return melhor * 100 >= minimo
        except Exception as e:
            print(f"⚠️ payout_ok({ativo}): {e}")
            return True

    # ── Velas ───────────────────────────────
    async def atualizar_velas(self):
        api = await self.reconectar_se_necessario()
        if not api:
            return

        todos = {**ATIVOS_OTC, **ATIVOS_MERCADO}
        for nome, ativo_id in todos.items():
            # Não sobrescreve ativos que estão sendo monitorados (evita race)
            if nome in self._monitorando:
                continue
            try:
                if not api.check_connect():
                    api = await self.reconectar_se_necessario()
                    if not api:
                        break

                c = api.get_candles(ativo_id, TIMEFRAME, 60, time.time())
                if c and len(c) > 0:
                    self.velas[nome].clear()
                    for x in c[-60:]:
                        if isinstance(x, dict):
                            self.velas[nome].append({
                                'time': datetime.fromtimestamp(x.get('from', 0), FUSO_BR),
                                'open': float(x['open']),
                                'high': float(x['max']),
                                'low': float(x['min']),
                                'close': float(x['close']),
                                'volume': int(x.get('volume', 0)),
                            })
            except Exception as e:
                print(f"⚠️ velas {nome}: {type(e).__name__}: {e}")
                continue

    # ── Sinais ──────────────────────────────
    def buscar_sinal(self):
        melhor = None
        melhor_score = 0

        for par, velas in self.velas.items():
            if len(velas) < 30:
                continue

            if not self.horario_valido(par):
                continue

            if not self.payout_ok(par):
                continue

            resultado = quantum_triple(list(velas))
            if not resultado:
                continue

            if resultado['confidence'] < CONFIANCA_MINIMA:
                continue

            score = resultado['confluences'] * 10 + resultado['confidence']
            if score > melhor_score:
                melhor_score = score
                melhor = {
                    'ativo': par,
                    'direcao': resultado['direction'],
                    'confianca': resultado['confidence'],
                    'confluencias': resultado['confluences'],
                    'rsi': resultado['rsi'],
                }

        return melhor

    def calcular_horario_entrada(self):
        agora = datetime.now(FUSO_BR)
        return agora.replace(second=0, microsecond=0) + timedelta(minutes=1)

    def formatar_sinal(self, sinal, horario):
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM TRIPLE M1 ✅
⏲ EXPIRAÇÃO: M1

👉🏼 HORARIO: {horario.strftime('%H:%M')}

🏳ATIVO: {sinal['ativo']} {sinal['direcao']}

📊 Confiança: {sinal['confianca']}%
🎯 Confluências: {sinal['confluencias']}/4
📈 RSI: {sinal['rsi']}

🍀🍀BOA SORTE 🍀🍀"""

    # ── Monitor de resultado ─────────────────
    async def _esperar_fechamento(self, horario_entrada):
        """Espera o candle de entrada fechar + margem."""
        expira = horario_entrada + timedelta(minutes=1)
        while datetime.now(FUSO_BR) < expira + timedelta(seconds=8):
            await asyncio.sleep(1)

    def _buscar_vela_fechada(self, api, ativo, horario_entrada):
        """Busca o candle cujo horário de FECHAMENTO == horário_entrada + 1min."""
        alvo_ts = (horario_entrada + timedelta(minutes=1)).timestamp()
        try:
            candles = api.get_candles(ativo, 60, 5, time.time())
        except Exception as e:
            print(f"⚠️ leitura vela {ativo}: {e}")
            return None

        for c in candles:
            # 'from' é o início da vela; fecha em 'from + 60'
            if abs((c['from'] + 60) - alvo_ts) < 5:
                return c
        return None

    async def monitorar_resultado(self, sinal, horario_entrada):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        self._monitorando.add(ativo)

        try:
            await self._esperar_fechamento(horario_entrada)

            api = await self.reconectar_se_necessario()
            if not api:
                self.tg.send(f"⚠️ Sem conexão para monitorar {ativo}")
                return

            vela = self._buscar_vela_fechada(api, ativo, horario_entrada)
            if vela is None:
                self.tg.send(f"⚠️ Não consegui ler vela de {ativo}")
                return

            # Empate (doji) → reembolso
            if vela['close'] == vela['open']:
                self.placar['e'] += 1
                self.tg.send(f"⚪ EMPATE | {ativo} | reembolso")
                return

            ganhou = (
                vela['close'] > vela['open'] if direcao == 'CALL'
                else vela['close'] < vela['open']
            )

            if ganhou:
                self.placar['w'] += 1
                resultado = "✅ WIN"
            elif USAR_GALE:
                # ── Gale 1 ──
                proxima = horario_entrada + timedelta(minutes=1)
                await self._esperar_fechamento(proxima)

                api = await self.reconectar_se_necessario()
                if not api:
                    self.placar['l'] += 1
                    resultado = "❌ LOSS (sem conexão p/ gale)"
                else:
                    vela_g = self._buscar_vela_fechada(api, ativo, proxima)
                    if vela_g is None:
                        self.placar['l'] += 1
                        resultado = "❌ LOSS (sem leitura gale)"
                    elif vela_g['close'] == vela_g['open']:
                        self.placar['e'] += 1
                        resultado = "⚪ EMPATE GALE"
                    else:
                        ganhou_g = (
                            vela_g['close'] > vela_g['open'] if direcao == 'CALL'
                            else vela_g['close'] < vela_g['open']
                        )
                        if ganhou_g:
                            self.placar['g1'] += 1
                            resultado = "✅ WIN GALE 1"
                        else:
                            self.placar['l'] += 1
                            resultado = "❌ LOSS"
            else:
                self.placar['l'] += 1
                resultado = "❌ LOSS"

            total = self.placar['w'] + self.placar['g1'] + self.placar['l']
            tx = round(
                ((self.placar['w'] + self.placar['g1']) / total) * 100, 1
            ) if total > 0 else 0.0

            emoji_dir = '🟢' if direcao == 'CALL' else '🔴'
            msg = f"""{resultado}
📊 {ativo} | {direcao} {emoji_dir}
📊 Placar: ✅{self.placar['w']}W 🟡{self.placar['g1']}G1 ❌{self.placar['l']}L ⚪{self.placar['e']}E
🎯 Assertividade: {tx}%"""
            self.tg.send(msg)
            print(f"📢 {resultado} | {ativo} | {tx}%")

        finally:
            self._monitorando.discard(ativo)

    # ── Placar diário ───────────────────────
    def verificar_zeramento_diario(self):
        agora = datetime.now(FUSO_BR)
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'g1': 0, 'l': 0, 'e': 0}
            self.tg.send("🔄 *PLACAR ZERADO*")
            print("🔄 Placar zerado.")

    # ── Loop principal ──────────────────────
    async def executar(self):
        banner()
        print("⚛️ Bot QUANTUM TRIPLE M1 v2 iniciando...")

        self.tg.send(f"""🔥 *QUANTUM TRIPLE M1 v2 ATIVADO*
📊 {len(ATIVOS_OTC)} Pares OTC + {len(ATIVOS_MERCADO)} Pares Mercado Aberto
⏱️ M1
🎯 4 Confluências:
   • EMA9 vs EMA21
   • RSI (Wilder 14)
   • Força do Candle
   • Rompimento
💪 Mínimo {MIN_CONFLUENCIAS} confirmações
💵 Payout mínimo: {PAYOUT_MINIMO}%
🔄 Gale 1.5x""")

        if not self.conectar_iq():
            print("❌ Falha conexão!")
            return

        await self.atualizar_velas()

        while True:
            try:
                self.verificar_zeramento_diario()

                agora = datetime.now(FUSO_BR)

                # Heartbeat
                if agora.second == 0:
                    total_velas = sum(len(v) for v in self.velas.values())
                    print(f"💓 {agora.strftime('%H:%M:%S')} | Velas: {total_velas} | Sinais: {self.sinais}")
                    if total_velas == 0:
                        print("🔄 Sem velas! Reconectando...")
                        self.iq_api = None

                # Atualização periódica
                if agora.second in (0, 15, 30, 45):
                    await self.atualizar_velas()

                # Janela de envio
                horario_entrada = self.calcular_horario_entrada()
                horario_envio = horario_entrada - timedelta(seconds=ANTECEDENCIA)
                tempo_ate_envio = (horario_envio - agora).total_seconds()

                if 0 <= tempo_ate_envio <= 15:
                    sinal = self.buscar_sinal()

                    if sinal:
                        ult = self.ult_sinal.get(sinal['ativo'], 0)
                        if time.time() - ult > INTERVALO_MINIMO:
                            if tempo_ate_envio > 0:
                                await asyncio.sleep(tempo_ate_envio)

                            self.ult_sinal[sinal['ativo']] = time.time()
                            self.sinais += 1
                            self.tg.send(self.formatar_sinal(sinal, horario_entrada))
                            print(
                                f"✅ Sinal #{self.sinais}: {sinal['ativo']} | "
                                f"{sinal['direcao']} | {sinal['confianca']}% | "
                                f"{sinal['confluencias']}/4"
                            )
                            asyncio.create_task(
                                self.monitorar_resultado(sinal, horario_entrada)
                            )

                await asyncio.sleep(1)

            except KeyboardInterrupt:
                print("🛑 Encerrado.")
                break
            except Exception as e:
                print(f"Erro no loop: {type(e).__name__}: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(Bot().executar())
