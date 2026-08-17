#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M1 - ESTRATÉGIA SEM GALE (EMA20/EMA50 + RSI)
📊 Pontuação mínima: 8 pontos
🛡️ Sem martingale (entrada única)
🔄 Placar diário automático
"""
import asyncio, time, requests, numpy as np, pandas as pd, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# Configurações
INTERVALO_MINIMO = 600       # 10 min entre sinais
ANTECEDENCIA = 30            # segundos antes da entrada
USAR_GALE = False            # Sem gale (entrada única)

def banner():
    print("⚛️ QUANTUM IA M1 - Estratégia Sem Gale | EMA+RSI")

def carregar_config():
    token = os.environ.get('TELEGRAM_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    if token and chat:
        banner()
        print("✅ Modo CLOUD detectado!")
        return {"token": token, "chat": chat}
    print("❌ Configure TELEGRAM_TOKEN e TELEGRAM_CHAT_ID")
    sys.exit(1)

cfg = carregar_config()
TOKEN, CHAT = cfg['token'], cfg['chat']

ATIVOS_OTC = {
    "EURUSD": "EURUSD-OTC",
    "GBPUSD": "GBPUSD-OTC",
    "EURJPY": "EURJPY-OTC"
}

class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c
    def send(self, txt):
        try: requests.post(f"{self.url}/sendMessage", json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"}, timeout=10)
        except: pass

class EstrategiaSemGale:
    def __init__(self):
        self.ema_rapida = 20
        self.ema_lenta = 50
        self.rsi_periodo = 14
        self.pontuacao_minima = 8

    def calcular_indicadores(self, candles):
        df = pd.DataFrame(candles)
        if len(df) < self.ema_lenta + self.rsi_periodo:
            return None
        df["ema20"] = df["close"].ewm(span=self.ema_rapida, adjust=False).mean()
        df["ema50"] = df["close"].ewm(span=self.ema_lenta, adjust=False).mean()
        delta = df["close"].diff()
        ganhos = delta.clip(lower=0)
        perdas = -delta.clip(upper=0)
        media_ganho = ganhos.ewm(alpha=1/self.rsi_periodo, adjust=False).mean()
        media_perda = perdas.ewm(alpha=1/self.rsi_periodo, adjust=False).mean()
        rs = media_ganho / media_perda
        df["rsi"] = 100 - (100 / (1 + rs))
        return df

    def analisar(self, candles):
        df = self.calcular_indicadores(candles)
        if df is None:
            return None
        atual = df.iloc[-1]
        anterior = df.iloc[-2]
        pontos_call = 0
        pontos_put = 0
        motivos_call = []
        motivos_put = []

        # CALL
        if atual["ema20"] > atual["ema50"]:
            pontos_call += 2
            motivos_call.append("EMA20 acima EMA50")
        if atual["ema20"] > anterior["ema20"]:
            pontos_call += 1
            motivos_call.append("EMA20 inclinada para cima")
        distancia_ema = abs(atual["close"] - atual["ema20"]) / atual["ema20"]
        if distancia_ema <= 0.0015:
            pontos_call += 2
            motivos_call.append("Pullback próximo EMA20")
        if atual["close"] > atual["open"]:
            pontos_call += 2
            motivos_call.append("Candle de confirmação")
        if atual["close"] > atual["ema20"]:
            pontos_call += 2
            motivos_call.append("Fechamento acima EMA20")
        if 50 <= atual["rsi"] <= 70:
            pontos_call += 1
            motivos_call.append(f"RSI favorável ({atual['rsi']:.1f})")

        # PUT
        if atual["ema20"] < atual["ema50"]:
            pontos_put += 2
            motivos_put.append("EMA20 abaixo EMA50")
        if atual["ema20"] < anterior["ema20"]:
            pontos_put += 1
            motivos_put.append("EMA20 inclinada para baixo")
        if distancia_ema <= 0.0015:
            pontos_put += 2
            motivos_put.append("Pullback próximo EMA20")
        if atual["close"] < atual["open"]:
            pontos_put += 2
            motivos_put.append("Candle de confirmação")
        if atual["close"] < atual["ema20"]:
            pontos_put += 2
            motivos_put.append("Fechamento abaixo EMA20")
        if 30 <= atual["rsi"] <= 50:
            pontos_put += 1
            motivos_put.append(f"RSI favorável ({atual['rsi']:.1f})")

        # Filtro mercado esticado
        if atual["rsi"] > 70:
            pontos_call = 0
        if atual["rsi"] < 30:
            pontos_put = 0

        if pontos_call >= self.pontuacao_minima:
            return ('CALL', min(70 + pontos_call * 2, 95), pontos_call, motivos_call)
        if pontos_put >= self.pontuacao_minima:
            return ('PUT', min(70 + pontos_put * 2, 95), pontos_put, motivos_put)
        return None

class BotSemGale:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.estrategia = EstrategiaSemGale()
        self.iq_api = None
        self.placar = {'w': 0, 'l': 0}
        self.ult_sinal = 0
        self.ultimo_dia = datetime.now(FUSO_BR).day

    def conectar_iq(self):
        from iqoptionapi.stable_api import IQ_Option
        email = os.environ.get('IQ_EMAIL')
        senha = os.environ.get('IQ_SENHA')
        if not email or not senha:
            return None
        try:
            if self.iq_api:
                try: self.iq_api.close()
                except: pass
            self.iq_api = IQ_Option(email, senha)
            check, _ = self.iq_api.connect()
            if check:
                print("✅ Conectado à IQ Option.")
                return self.iq_api
            else:
                print("❌ Falha na conexão.")
                return None
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None

    async def reconectar_se_necessario(self):
        if self.iq_api is None or not self.iq_api.check_connect():
            print("🔄 Reconectando...")
            return self.conectar_iq()
        return self.iq_api

    async def atualizar_velas(self):
        api = await self.reconectar_se_necessario()
        if not api:
            return
        for nome, ativo_id in ATIVOS_OTC.items():
            for retry in range(3):
                try:
                    if not api.check_connect():
                        api = await self.reconectar_se_necessario()
                        if not api:
                            break
                    c = api.get_candles(ativo_id, 60, 80, time.time())
                    if c and len(c) > 0:
                        self.velas[nome].clear()
                        for x in c[-80:]:
                            if isinstance(x, dict):
                                self.velas[nome].append({
                                    'time': datetime.fromtimestamp(x.get('from',0), FUSO_BR),
                                    'open': float(x['open']), 'high': float(x['max']),
                                    'low': float(x['min']), 'close': float(x['close']),
                                    'volume': int(x.get('volume',0))
                                })
                        break
                    time.sleep(2)
                except Exception as e:
                    print(f"Erro velas {nome}: {e}")
                    time.sleep(2)
                    if "need reconnect" in str(e):
                        api = await self.reconectar_se_necessario()
                        if not api:
                            break

    def buscar_sinal(self):
        for par, velas in self.velas.items():
            if len(velas) < 70:  # precisa de pelo menos 50+14 velas
                continue
            resultado = self.estrategia.analisar(list(velas))
            if resultado:
                direcao, conf, pontuacao, motivos = resultado
                return {'ativo': par, 'direcao': direcao, 'confianca': conf,
                        'pontuacao': pontuacao, 'motivos': motivos}
        return None

    def calcular_horario_entrada(self):
        agora = datetime.now(FUSO_BR)
        return agora.replace(second=0, microsecond=0) + timedelta(minutes=1)

    def formatar_sinal(self, sinal, horario):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        hora = horario.strftime('%H:%M')
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM IA M1 ✅
⏲ EXPIRAÇÃO: M1

👉🏼 HORARIO: {hora}

🏳ATIVO: {ativo}-OTC {direcao}

🍀🍀BOA SORTE 🍀 🍀"""

    async def monitorar_resultado(self, sinal, horario_entrada):
        ativo = sinal['ativo']
        direcao = sinal['direcao']

        agora = datetime.now(FUSO_BR)
        espera = (horario_entrada + timedelta(minutes=1) - agora).total_seconds()
        if espera > 0:
            await asyncio.sleep(espera)
        await asyncio.sleep(5)
        await self.atualizar_velas()
        velas = self.velas[ativo]

        ganhou = False
        for v in velas:
            if v['time'].replace(second=0, microsecond=0) == horario_entrada.replace(second=0, microsecond=0):
                ganhou = v['close'] > v['open'] if direcao == 'CALL' else v['close'] < v['open']
                break

        if ganhou:
            self.placar['w'] += 1
            resultado = "✅ WIN"
        else:
            self.placar['l'] += 1
            resultado = "❌ LOSS"

        total = self.placar['w'] + self.placar['l']
        tx = round((self.placar['w'] / total) * 100, 1) if total > 0 else 0.0
        msg = f"""{resultado}
📊 {ativo}-OTC | {direcao} {'🟢' if direcao=='CALL' else '🔴'}
📊 Placar: 🟢{self.placar['w']}W 🔴{self.placar['l']}L
🎯 Assertividade: {tx}%"""
        self.tg.send(msg)

    def verificar_zeramento_diario(self):
        agora = datetime.now(FUSO_BR)
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'l': 0}
            self.tg.send("🔄 *PLACAR ZERADO AUTOMATICAMENTE PARA O NOVO DIA*")
            print("🔄 Placar zerado para o novo dia.")

    async def executar(self):
        banner()
        print("⚛️ Bot Sem Gale iniciando...")
        self.tg.send("🔥 *QUANTUM IA M1 ATIVADO*\n📊 Estratégia Sem Gale (EMA20/EMA50 + RSI)\n🛡️ Sem martingale\n🔄 Placar diário automático")
        while True:
            try:
                self.verificar_zeramento_diario()
                await self.atualizar_velas()
                sinal = self.buscar_sinal()
                if sinal and time.time() - self.ult_sinal > INTERVALO_MINIMO:
                    horario_entrada = self.calcular_horario_entrada()
                    horario_envio = horario_entrada - timedelta(seconds=ANTECEDENCIA)
                    agora = datetime.now(FUSO_BR)
                    espera = (horario_envio - agora).total_seconds()
                    if espera > 0:
                        await asyncio.sleep(espera)
                    self.ult_sinal = time.time()
                    msg = self.formatar_sinal(sinal, horario_entrada)
                    self.tg.send(msg)
                    asyncio.create_task(self.monitorar_resultado(sinal, horario_entrada))
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("🛑 Encerrado.")
                break
            except Exception as e:
                print(f"Erro: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    bot = BotSemGale()
    asyncio.run(bot.executar())
