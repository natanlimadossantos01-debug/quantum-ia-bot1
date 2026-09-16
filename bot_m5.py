#!/usr/bin/env python3
"""
⚛️ QUANTUM TRIPLE M1 v4 - MULTI-CONFLUÊNCIA (BLINDADO)
🎯 5 Confluências: EMA9/EMA21, RSI Wilder, Força Candle, Rompimento, S/R
💪 Mínimo 3/5 confirmações
📊 6 Pares OTC + 6 Pares Mercado Aberto
⏱️ M1
🔄 Gale 1.5x

REGRAS DE HORÁRIO (forçadas em UTC → BR):
  • Seg-Sex 00:00–15:59 → Mercado Aberto
  • Seg-Sex 16:00–23:59 → OTC
  • Sáb/Dom           → OTC o dia todo
"""
import asyncio, time, requests, numpy as np, signal, sys, os
from datetime import datetime, timedelta, timezone
from collections import deque

signal.signal(signal.SIGCHLD, signal.SIG_IGN)

# ═══════════════════════════════════════════
# 🌎 FUSO HORÁRIO BLINDADO
# ═══════════════════════════════════════════
FUSO_BR = timezone(timedelta(hours=-3))


def agora_br():
    """
    Sempre retorna hora de Brasília, independente do TZ do servidor.
    Converte explicitamente de UTC para evitar bugs em containers.
    """
    return datetime.now(timezone.utc).astimezone(FUSO_BR)


# ═══════════════════════════════════════════
# ⚙️ CONFIGURAÇÕES
# ═══════════════════════════════════════════
INTERVALO_MINIMO = 900
USAR_GALE = True
MULTIPLICADOR_GALE = 1.5
ANTECEDENCIA = 30
TIMEFRAME = 60
CONFIANCA_MINIMA = 70
PAYOUT_MINIMO = 80
ATR_MINIMO_RELATIVO = 0.00002
MIN_CONFLUENCIAS = 4
DEBUG_HORARIO = True   # mostra no console por que cada ativo passa/bloqueia


def banner():
    print("⚛️ QUANTUM TRIPLE M1 v4 - Multi-Confluência (Blindado)")


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
# 📊 ATIVOS
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
# 📍 SUPORTE / RESISTÊNCIA
# ═══════════════════════════════════════════
def encontrar_suporte_resistencia(velas, lookback=20):
    if len(velas) < lookback + 2:
        return None, None
    recentes = velas[-lookback:-1]
    highs = [v["high"] for v in recentes]
    lows = [v["low"] for v in recentes]
    return min(lows), max(highs)


def proximo_de_nivel(preco, suporte, resistencia, atr, tolerancia_atr=0.5):
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
    5 confluências:
      1) EMA9 vs EMA21
      2) RSI Wilder (zona morta 45–55)
      3) Força do candle
      4) Rompimento da vela anterior
      5) Suporte / Resistência
    """
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
    if valor_atr < ATR_MINIMO_RELATIVO:
        return None
    if 45 <= valor_rsi <= 55:
        return None

    conf_call = 0
    conf_put = 0

    if ema_9 > ema_21:
        conf_call += 1
    elif ema_9 < ema_21:
        conf_put += 1

    if valor_rsi > 55:
        conf_call += 1
    elif valor_rsi < 45:
        conf_put += 1

    corpo = atual["close"] - atual["open"]
    if corpo > 0 and abs(corpo) >= valor_atr * 0.15:
        conf_call += 1
    elif corpo < 0 and abs(corpo) >= valor_atr * 0.15:
        conf_put += 1

    if atual["high"] > anterior["high"] and atual["close"] > atual["open"]:
        conf_call += 1
    elif atual["low"] < anterior["low"] and atual["close"] < atual["open"]:
        conf_put += 1

    suporte, resistencia = encontrar_suporte_resistencia(velas, lookback=20)
    zona = proximo_de_nivel(atual["close"], suporte, resistencia, valor_atr, 0.5)
    if zona == "suporte":
        conf_call += 1
    elif zona == "resistencia":
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

    # Confiança recalibrada (distribuição real)
    dist_ema = abs(ema_9 - ema_21) / valor_atr
    forca_tendencia = min(1.0, dist_ema / 1.5)
    forca_rsi = min(1.0, abs(valor_rsi - 50) / 30)
    bonus_sr = 1.0 if zona else 0.0

    confianca = int(
        40
        + total * 7
        + forca_tendencia * 8
        + forca_rsi * 7
        + bonus_sr * 5
    )
    confianca = max(0, min(95, confianca))

    return {
        "direction": direcao,
        "confidence": confianca,
        "confluences": total,
        "rsi": round(valor_rsi, 2),
        "zona": zona or "—",
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
        self.ult_sinal = {}
        self.sinais = 0
        self.ultimo_dia = agora_br().day
        self._monitorando = set()
        self._ultimo_log_horario = 0

    # ── Conexão ──
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

    # ── Filtros ──
    def horario_valido(self, ativo, debug=False):
        """
        Seg-Sex 00:00–15:59 → Mercado Aberto
        Seg-Sex 16:00–23:59 → OTC
        Sáb/Dom            → OTC o dia todo
        """
        agora = agora_br()
        h = agora.hour
        dia_semana = agora.weekday()  # 0=seg ... 6=dom
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
            print(
                f"   🔎 {ativo:14s} [{tipo:6s}] "
                f"h={h:02d} | dia_sem={dia_semana} | ok={ok}"
            )

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

    # ── Velas ──
    async def atualizar_velas(self):
        api = await self.reconectar_se_necessario()
        if not api:
            return

        todos = {**ATIVOS_OTC, **ATIVOS_MERCADO}
        for nome, ativo_id in todos.items():
            if nome in self._monitorando:
                continue
            # ⚠️ Só busca velas de ativos que estão no horário válido
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

    # ── Sinais ──
    def buscar_sinal(self):
        agora = agora_br()
        # Log de horário 1x por minuto
        if time.time() - self._ultimo_log_horario > 60:
            self._ultimo_log_horario = time.time()
            print(
                f"\n🔍 [buscar_sinal] {agora.strftime('%d/%m %H:%M:%S')} "
                f"| dia_semana={agora.weekday()}"
            )

        melhor = None
        melhor_score = 0

        for par, velas in self.velas.items():
            if len(velas) < 30:
                continue

            h_ok = self.horario_valido(par, debug=DEBUG_HORARIO)

            if not h_ok:
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
                    'suporte': resultado['suporte'],
                    'resistencia': resultado['resistencia'],
                }

        return melhor

    def calcular_horario_entrada(self):
        agora = agora_br()
        return agora.replace(second=0, microsecond=0) + timedelta(minutes=1)

    def formatar_sinal(self, sinal, horario):
        zona = sinal.get('zona', '—')
        if zona == "suporte":
            emoji_zona = "🟢 Suporte"
        elif zona == "resistencia":
            emoji_zona = "🔴 Resistência"
        else:
            emoji_zona = "—"

        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM TRIPLE M1 v4 ✅
⏲ EXPIRAÇÃO: M1

👉🏼 HORARIO: {horario.strftime('%H:%M')}

🏳ATIVO: {sinal['ativo']} {sinal['direcao']}

📊 Confiança: {sinal['confianca']}%
🎯 Confluências: {sinal['confluencias']}/5
📈 RSI: {sinal['rsi']}
📍 Zona: {emoji_zona}

🍀🍀BOA SORTE 🍀🍀"""

    # ── Monitor ──
    async def _esperar_fechamento(self, horario_entrada):
        expira = horario_entrada + timedelta(minutes=1)
        while agora_br() < expira + timedelta(seconds=8):
            await asyncio.sleep(1)

    def _buscar_vela_fechada(self, api, ativo, horario_entrada):
        alvo_ts = (horario_entrada + timedelta(minutes=1)).timestamp()
        try:
            candles = api.get_candles(ativo, 60, 5, time.time())
        except Exception as e:
            print(f"⚠️ leitura vela {ativo}: {e}")
            return None

        for c in candles:
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

    def verificar_zeramento_diario(self):
        agora = agora_br()
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'g1': 0, 'l': 0, 'e': 0}
            self.tg.send("🔄 *PLACAR ZERADO*")
            print("🔄 Placar zerado.")

    # ── Loop principal ──
    async def executar(self):
        banner()
        print("⚛️ Bot QUANTUM TRIPLE M1 v4 iniciando...")
        print(f"🕐 Hora BR agora: {agora_br().strftime('%d/%m/%Y %H:%M:%S')} "
              f"(dia_semana={agora_br().weekday()})")

        self.tg.send(f"""🔥 *QUANTUM TRIPLE M1 v4 ATIVADO*
📊 {len(ATIVOS_OTC)} Pares OTC + {len(ATIVOS_MERCADO)} Pares Mercado Aberto
⏱️ M1
🎯 5 Confluências:
   • EMA9 vs EMA21
   • RSI (Wilder 14 + zona morta)
   • Força do Candle
   • Rompimento
   • Suporte/Resistência
💪 Mínimo {MIN_CONFLUENCIAS}/5 confirmações
💵 Payout mínimo: {PAYOUT_MINIMO}%
🕐 *Horários (BR):*
   • Seg-Sex 00:00–15:59 → Mercado Aberto
   • Seg-Sex 16:00–23:59 → OTC
   • Sáb/Dom → OTC o dia todo
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
                    if total_velas == 0:
                        print("🔄 Sem velas! Reconectando...")
                        self.iq_api = None

                if agora.second in (0, 15, 30, 45):
                    await self.atualizar_velas()

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
                                f"{sinal['confluencias']}/5 | zona={sinal['zona']}"
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
