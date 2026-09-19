#!/usr/bin/env python3
"""
⚛️ QUANTUM TRIPLE M5 v5.0 - MULTI-CONFLUÊNCIA (MACD + Bollinger)
🎯 7 Confluências: EMA9/EMA21, RSI, Candle, Rompimento, S/R, MACD, Bollinger
💪 Mínimo 4/7 confirmações
📊 6 Pares OTC + 6 Pares Mercado Aberto
⏱️ M5 (5 minutos)
🔄 Gale 1.5x

MUDANÇAS v5.0 (sobre v4.5):
✅ MACD (12, 26, 9) — histograma + linha
✅ Bollinger Bands (20, 2) — posição do preço
✅ MIN_CONFLUENCIAS = 4/7 (era 4/5)
"""
import asyncio, time, requests, numpy as np, signal, sys, os
from datetime import datetime, timedelta, timezone
from collections import deque

signal.signal(signal.SIGCHLD, signal.SIG_IGN)

FUSO_BR = timezone(timedelta(hours=-3))


def agora_br():
    return datetime.now(timezone.utc).astimezone(FUSO_BR)


# ═══════════════════════════════════════════
# ⚙️ CONFIGURAÇÕES
# ═══════════════════════════════════════════
TIMEFRAME = 300
INTERVALO_MINIMO = 1200
ANTECEDENCIA = 30
USAR_GALE = True
MULTIPLICADOR_GALE = 1.5
CONFIANCA_MINIMA = 75
PAYOUT_MINIMO = 80
ATR_MINIMO_RELATIVO = 0.0001
MIN_CONFLUENCIAS = 4           # mínimo 4/7
PENALIDADE_SR = -15
RSI_EXAUSTAO_ALTA = 65
RSI_EXAUSTAO_BAIXA = 35
TOLERANCIA_SR_ATR = 0.8
DEBUG_HORARIO = True

# MACD
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger
BB_PERIODO = 20
BB_DESVIO = 2.0


def banner():
    print("⚛️ QUANTUM TRIPLE M5 v5.0 - Multi-Confluência (MACD + Bollinger)")


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
# 📈 MACD
# ═══════════════════════════════════════════
def calcular_macd(velas, fast=12, slow=26, signal_period=9):
    """
    Retorna (macd_line, signal_line, histograma) do último candle.
    """
    if len(velas) < slow + signal_period:
        return None, None, None

    fechamentos = [v["close"] for v in velas]

    # EMA rápida
    ema_fast = ema(fechamentos, fast)
    # EMA lenta
    ema_slow = ema(fechamentos, slow)

    if ema_fast is None or ema_slow is None:
        return None, None, None

    macd_line = ema_fast - ema_slow

    # Para a linha de sinal, precisamos do MACD de várias velas
    macd_series = []
    for i in range(slow, len(fechamentos)):
        sub = fechamentos[:i + 1]
        ef = ema(sub, fast)
        es = ema(sub, slow)
        if ef is not None and es is not None:
            macd_series.append(ef - es)

    if len(macd_series) < signal_period:
        return macd_line, None, None

    signal_line = ema(macd_series, signal_period)
    if signal_line is None:
        return macd_line, None, None

    histograma = macd_line - signal_line

    return macd_line, signal_line, histograma


# ═══════════════════════════════════════════
# 📉 BOLLINGER BANDS
# ═══════════════════════════════════════════
def calcular_bollinger(velas, periodo=20, desvio=2.0):
    """
    Retorna (banda_sup, banda_med, banda_inf) do último candle.
    """
    if len(velas) < periodo:
        return None, None, None

    fechamentos = np.array([v["close"] for v in velas[-periodo:]], dtype=float)
    media = fechamentos.mean()
    std = fechamentos.std()

    banda_sup = media + desvio * std
    banda_inf = media - desvio * std

    return float(banda_sup), float(media), float(banda_inf)


# ═══════════════════════════════════════════
# 📍 SUPORTE / RESISTÊNCIA
# ═══════════════════════════════════════════
def encontrar_suporte_resistencia(velas, lookback=20):
    if len(velas) < lookback + 2:
        return None, None
    recentes = velas[-lookback:-1]
    highs = [v["high"] for v in recentes]
    lows = [v["low"] for v in recentes]
    return min(lows), max(highs)


def proximo_de_nivel(preco, suporte, resistencia, atr, tolerancia_atr=0.8):
    if suporte is None or resistencia is None or atr <= 0:
        return None
    tol = atr * tolerancia_atr
    dist_sup = abs(preco - suporte)
    dist_res = abs(preco - resistencia)
    if dist_sup <= tol and dist_sup < dist_res:
        return "suporte"
    if dist_res <= tol and dist_res < dist_sup:
        return "resistencia"
    return None


# ═══════════════════════════════════════════
# 🎯 ESTRATÉGIA
# ═══════════════════════════════════════════
def quantum_triple(velas):
    """
    7 confluências:
      1) EMA9 vs EMA21
      2) RSI Wilder (zona morta + exaustão)
      3) Força do candle
      4) Rompimento
      5) Suporte / Resistência
      6) MACD (histograma + cruzamento)
      7) Bollinger Bands (posição do preço)
    """
    if len(velas) < 35:
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
    if valor_atr < ATR_MINIMO_RELATIVO:
        return None

    # Zona morta RSI
    if 45 <= valor_rsi <= 55:
        return None
    # Exaustão
    if valor_rsi >= RSI_EXAUSTAO_ALTA:
        return None
    if valor_rsi <= RSI_EXAUSTAO_BAIXA:
        return None

    conf_call = 0
    conf_put = 0

    # ── 1) EMA ──
    if ema_9 > ema_21:
        conf_call += 1
    elif ema_9 < ema_21:
        conf_put += 1

    # ── 2) RSI ──
    if valor_rsi > 55:
        conf_call += 1
    elif valor_rsi < 45:
        conf_put += 1

    # ── 3) Candle ──
    corpo = atual["close"] - atual["open"]
    if corpo > 0 and abs(corpo) >= valor_atr * 0.15:
        conf_call += 1
    elif corpo < 0 and abs(corpo) >= valor_atr * 0.15:
        conf_put += 1

    # ── 4) Rompimento ──
    if atual["high"] > anterior["high"] and atual["close"] > atual["open"]:
        conf_call += 1
    elif atual["low"] < anterior["low"] and atual["close"] < atual["open"]:
        conf_put += 1

    # ── 5) S/R ──
    suporte, resistencia = encontrar_suporte_resistencia(velas, lookback=20)
    zona = proximo_de_nivel(
        atual["close"], suporte, resistencia, valor_atr,
        tolerancia_atr=TOLERANCIA_SR_ATR
    )
    if zona == "suporte":
        conf_call += 1
    elif zona == "resistencia":
        conf_put += 1

    # ── 6) MACD (NOVO) ──
    macd_line, signal_line, histograma = calcular_macd(velas)
    macd_ok = macd_line is not None and signal_line is not None

    if macd_ok:
        # Histograma positivo + MACD acima da signal → CALL
        if histograma > 0 and macd_line > signal_line:
            conf_call += 1
        # Histograma negativo + MACD abaixo da signal → PUT
        elif histograma < 0 and macd_line < signal_line:
            conf_put += 1

    # ── 7) Bollinger Bands (NOVO) ──
    bb_sup, bb_med, bb_inf = calcular_bollinger(velas)

    # Preço na banda inferior → reversão pra cima (CALL)
    # Preço na banda superior → reversão pra baixo (PUT)
    bb_posicao = None
    if bb_sup and bb_inf and bb_sup > bb_inf:
        if atual["close"] <= bb_inf:
            conf_call += 1  # toque na banda inferior
            bb_posicao = "inferior"
        elif atual["close"] >= bb_sup:
            conf_put += 1  # toque na banda superior
            bb_posicao = "superior"
        elif atual["close"] > bb_med:
            conf_call += 1  # acima da média
            bb_posicao = "acima_media"
        elif atual["close"] < bb_med:
            conf_put += 1  # abaixo da média
            bb_posicao = "abaixo_media"

    # ── Decisão ──
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

    # ── Confiança real ──
    dist_ema = abs(ema_9 - ema_21) / valor_atr
    forca_tendencia = min(1.0, dist_ema / 1.5)
    forca_rsi = min(1.0, abs(valor_rsi - 50) / 30)
    bonus_sr = 1.0 if zona else 0.0

    # MACD força
    macd_forca = 0.0
    if macd_ok and valor_atr > 0:
        macd_forca = min(1.0, abs(histograma) / (valor_atr * 0.5))

    # Bollinger posição
    bb_bonus = 0.0
    if bb_posicao in ("inferior", "superior"):
        bb_bonus = 1.0  # toque nas bandas é forte
    elif bb_posicao:
        bb_bonus = 0.5

    penalidade_sr = 0
    if direcao == "CALL" and zona == "resistencia":
        penalidade_sr = PENALIDADE_SR
    elif direcao == "PUT" and zona == "suporte":
        penalidade_sr = PENALIDADE_SR

    confianca = int(
        40
        + total * 6              # 7 confluências → até +42
        + forca_tendencia * 6
        + forca_rsi * 5
        + bonus_sr * 4
        + macd_forca * 4
        + bb_bonus * 3
        + penalidade_sr
    )
    confianca = max(0, min(95, confianca))

    return {
        "direction": direcao,
        "confidence": confianca,
        "confluences": total,
        "rsi": round(valor_rsi, 2),
        "zona": zona or "—",
        "macd": "OK" if macd_ok else "—",
        "bb": bb_posicao or "—",
        "suporte": round(suporte, 5) if suporte else None,
        "resistencia": round(resistencia, 5) if resistencia else None,
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
        self.ult_sinal_global = 0
        self.sinais = 0
        self.ultimo_dia = agora_br().day
        self._monitorando = set()
        self._ultimo_log_horario = 0

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

    def horario_valido(self, ativo, debug=False):
        agora = agora_br()
        h = agora.hour
        dia_semana = agora.weekday()
        fim_de_semana = dia_semana >= 5
        eh_otc = ativo.endswith("-OTC")

        if fim_de_semana:
            ok = eh_otc
        elif eh_otc:
            ok = 16 <= h <= 23
        else:
            ok = 0 <= h < 16

        if debug:
            tipo = "OTC" if eh_otc else "ABERTO"
            print(f"   🔎 {ativo:14s} [{tipo:6s}] h={h:02d} | ok={ok}")

        return ok

    def payout_ok(self, ativo, minimo=PAYOUT_MINIMO):
        try:
            if not self.iq_api or not self.iq_api.check_connect():
                return True
            payouts = self.iq_api.get_all_profit()
            base = ativo.replace("-OTC", "")
            info = payouts.get(base, {}) if payouts else {}
            if not info:
                return True
            melhor = max(info.values()) if info else 0
            return melhor * 100 >= minimo
        except Exception as e:
            print(f"⚠️ payout_ok({ativo}): {e}")
            return True

    async def atualizar_velas(self):
        api = await self.reconectar_se_necessario()
        if not api:
            return

        todos = {**ATIVOS_OTC, **ATIVOS_MERCADO}
        for nome, ativo_id in todos.items():
            if nome in self._monitorando:
                continue
            if not self.horario_valido(nome):
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

    def buscar_sinal(self):
        agora = agora_br()
        if time.time() - self._ultimo_log_horario > 60:
            self._ultimo_log_horario = time.time()
            print(f"\n🔍 [buscar_sinal] {agora.strftime('%d/%m %H:%M:%S')}")

        melhor = None
        melhor_score = 0

        for par, velas in self.velas.items():
            if len(velas) < 35:
                continue
            if not self.horario_valido(par, debug=DEBUG_HORARIO):
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
                    'zona': resultado['zona'],
                    'macd': resultado['macd'],
                    'bb': resultado['bb'],
                    'suporte': resultado['suporte'],
                    'resistencia': resultado['resistencia'],
                }

        return melhor

    def calcular_horario_entrada(self):
        agora = agora_br()
        proximo = ((agora.minute // 5) + 1) * 5
        base = agora.replace(second=0, microsecond=0)
        if proximo >= 60:
            return base.replace(minute=0) + timedelta(hours=1)
        return base.replace(minute=proximo)

    def formatar_sinal(self, sinal, horario):
        zona = sinal.get('zona', '—')
        if zona == "suporte":
            emoji_zona = "🟢 Suporte"
        elif zona == "resistencia":
            emoji_zona = "🔴 Resistência"
        else:
            emoji_zona = "—"

        bb = sinal.get('bb', '—')
        bb_emoji = {
            "inferior": "🔻 Inferior",
            "superior": "🔺 Superior",
            "acima_media": "⬆️ Acima média",
            "abaixo_media": "⬇️ Abaixo média",
            "—": "—"
        }.get(bb, "—")

        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM TRIPLE M5 v5.0 ✅
⏲ EXPIRAÇÃO: M5

👉🏼 HORARIO: {horario.strftime('%H:%M')}

🏳ATIVO: {sinal['ativo']} {sinal['direcao']}

📊 Confiança: {sinal['confianca']}%
🎯 Confluências: {sinal['confluencias']}/7
📈 RSI: {sinal['rsi']}
📍 Zona: {emoji_zona}
📉 Bollinger: {bb_emoji}

🍀🍀BOA SORTE 🍀🍀"""

    async def _esperar_fechamento(self, horario_entrada, minutos=5):
        expira = horario_entrada + timedelta(minutes=minutos)
        while agora_br() < expira + timedelta(seconds=8):
            await asyncio.sleep(1)

    def _buscar_vela_fechada(self, api, ativo, horario_entrada, minutos=5):
        alvo_ts = (horario_entrada + timedelta(minutes=minutos)).timestamp()
        try:
            candles = api.get_candles(ativo, TIMEFRAME, 5, time.time())
        except Exception as e:
            print(f"⚠️ leitura vela {ativo}: {e}")
            return None

        for c in candles:
            if abs((c['from'] + TIMEFRAME) - alvo_ts) < 30:
                return c
        return None

    async def monitorar_resultado(self, sinal, horario_entrada):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        self._monitorando.add(ativo)

        try:
            await self._esperar_fechamento(horario_entrada, minutos=5)

            api = await self.reconectar_se_necessario()
            if not api:
                self.tg.send(f"⚠️ Sem conexão para monitorar {ativo}")
                return

            vela = self._buscar_vela_fechada(api, ativo, horario_entrada, minutos=5)
            if vela is None:
                self.tg.send(f"⚠️ Não consegui ler vela de {ativo}")
                return

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
                proxima = horario_entrada + timedelta(minutes=5)
                await self._esperar_fechamento(proxima, minutos=5)

                api = await self.reconectar_se_necessario()
                if not api:
                    self.placar['l'] += 1
                    resultado = "❌ LOSS (sem conexão p/ gale)"
                else:
                    vela_g = self._buscar_vela_fechada(api, ativo, proxima, minutos=5)
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

    def verificar_zeramento_diario(self):
        agora = agora_br()
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'g1': 0, 'l': 0, 'e': 0}
            self.tg.send(f"🔄 *PLACAR ZERADO* ({agora.strftime('%d/%m/%Y')})")
            print(f"🔄 Placar zerado em {agora.strftime('%d/%m/%Y %H:%M:%S')}")

    async def executar(self):
        banner()
        print("⚛️ Bot QUANTUM TRIPLE M5 v5.0 iniciando...")
        print(f"🕐 Hora BR agora: {agora_br().strftime('%d/%m/%Y %H:%M:%S')}")

        self.tg.send(f"""🔥 *QUANTUM TRIPLE M5 v5.0 ATIVADO*
📊 {len(ATIVOS_OTC)} Pares OTC + {len(ATIVOS_MERCADO)} Pares Mercado Aberto
⏱️ *M5 (5 minutos)*
🎯 *7 Confluências:*
   1. EMA9 vs EMA21
   2. RSI (Wilder + zona morta + exaustão)
   3. Força do Candle
   4. Rompimento
   5. Suporte/Resistência
   6. *MACD (12, 26, 9)*
   7. *Bollinger Bands (20, 2)*
⚠️ RSI exaustão: >= {RSI_EXAUSTAO_ALTA} ou <= {RSI_EXAUSTAO_BAIXA}
⚠️ Penalidade S/R: {PENALIDADE_SR}%
💪 Mínimo *{MIN_CONFLUENCIAS}/7* confirmações
💵 Confiança mínima: *{CONFIANCA_MINIMA}%*
⏱️ *INTERVALO GLOBAL:* {INTERVALO_MINIMO // 60} min
🕐 Seg-Sex: 00-16h Aberto / 16-24h OTC
🕐 Sáb/Dom: OTC o dia todo
🔄 Gale 1.5x""")

        if not self.conectar_iq():
            print("❌ Falha conexão!")
            return

        await self.atualizar_velas()

        while True:
            try:
                self.verificar_zeramento_diario()

                agora = agora_br()

                if agora.second == 0:
                    total_velas = sum(len(v) for v in self.velas.values())
                    print(f"💓 {agora.strftime('%H:%M:%S')} | Velas: {total_velas} | Sinais: {self.sinais}")

                if agora.second in (0, 30):
                    await self.atualizar_velas()

                horario_entrada = self.calcular_horario_entrada()
                horario_envio = horario_entrada - timedelta(seconds=ANTECEDENCIA)
                tempo_ate_envio = (horario_envio - agora).total_seconds()

                if 0 <= tempo_ate_envio <= 15:
                    sinal = self.buscar_sinal()

                    if sinal:
                        if time.time() - self.ult_sinal_global > INTERVALO_MINIMO:
                            if tempo_ate_envio > 0:
                                await asyncio.sleep(tempo_ate_envio)

                            self.ult_sinal_global = time.time()
                            self.sinais += 1
                            self.tg.send(self.formatar_sinal(sinal, horario_entrada))
                            print(
                                f"✅ Sinal #{self.sinais}: {sinal['ativo']} | "
                                f"{sinal['direcao']} | {sinal['confianca']}% | "
                                f"{sinal['confluencias']}/7 | "
                                f"MACD={sinal['macd']} | BB={sinal['bb']}"
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
