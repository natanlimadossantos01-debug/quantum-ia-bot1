#!/usr/bin/env python3
"""
⚛️ QUANTUM IA TRADER - OTC TREND ALIGNMENT (M5)
📊 Estratégia: Maioria/Minoria + Tendência SMA20 + Filtro de Pavio
📨 Sinal enviado 30 segundos antes da entrada
🛡️ Apenas 3 pares OTC
🔄 Com gale 1
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# Configurações
TIMEFRAME = "M5"
INTERVALO_MINIMO = 300       # 5 min entre sinais
USAR_GALE = True
ANTECEDENCIA = 30            # segundos antes da entrada

def banner():
    print(f"⚛️ QUANTUM IA TRADER ({TIMEFRAME}) - OTC Trend Alignment")

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

# Apenas 3 pares OTC
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

class OTCTrendAlignment:
    def __init__(self, timeframe='M5'):
        self.timeframe = timeframe

    def _sma(self, valores, periodo):
        if len(valores) < periodo:
            return sum(valores) / len(valores) if valores else 0
        return sum(valores[-periodo:]) / periodo

    def analisar(self, velas):
        if len(velas) < 25:
            return None

        precos = [v['close'] for v in velas]
        sma20 = self._sma(precos, 20)
        atual = precos[-1]

        # Conta velas de alta/baixa nas últimas 5 velas
        ultimas_5 = list(velas)[-5:]
        calls = sum(1 for v in ultimas_5 if v['close'] > v['open'])
        puts = 5 - calls

        # Última vela
        vela = velas[-1]
        corpo = abs(vela['close'] - vela['open'])
        if corpo == 0:
            return None

        pavio_sup = vela['high'] - max(vela['close'], vela['open'])
        pavio_inf = min(vela['close'], vela['open']) - vela['low']

        # Horário
        hora = datetime.now(FUSO_BR).hour
        if hora < 8 or hora > 17:
            return None

        # CALL: minoria de alta (2 altas, 3 baixas) + tendência de alta + sem pavio sup grande
        if calls == 2 and puts == 3 and atual > sma20:
            if pavio_sup <= corpo * 0.5:
                return ('CALL', 74)

        # PUT: minoria de baixa (2 baixas, 3 altas) + tendência de baixa + sem pavio inf grande
        if puts == 2 and calls == 3 and atual < sma20:
            if pavio_inf <= corpo * 0.5:
                return ('PUT', 74)

        return None

class BotPowerTrend:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.estrategia = OTCTrendAlignment(TIMEFRAME)
        self.iq_api = None
        self.placar = {'w': 0, 'g1': 0, 'l': 0}
        self.ult_sinal = 0

    def conectar_iq(self):
        from iqoptionapi.stable_api import IQ_Option
        email = os.environ.get('IQ_EMAIL')
        senha = os.environ.get('IQ_SENHA')
        if not email or not senha:
            print("❌ Configure IQ_EMAIL e IQ_SENHA")
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
        timeframe_seg = 300 if TIMEFRAME == "M5" else 900
        for nome, ativo_id in ATIVOS_OTC.items():
            sucesso = False
            for retry in range(3):
                try:
                    if not api.check_connect():
                        api = await self.reconectar_se_necessario()
                        if not api:
                            break
                    c = api.get_candles(ativo_id, timeframe_seg, 80, time.time())
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
                        sucesso = True
                        break
                    time.sleep(2)
                except Exception as e:
                    print(f"Erro velas {nome}: {e}")
                    time.sleep(2)
                    if "need reconnect" in str(e):
                        api = await self.reconectar_se_necessario()
                        if not api:
                            break
            if not sucesso:
                print(f"⚠️ Falha ao atualizar velas de {nome}.")

    def buscar_sinal(self):
        for par, velas in self.velas.items():
            if len(velas) < 25:
                continue
            resultado = self.estrategia.analisar(velas)
            if resultado:
                direcao, conf = resultado
                return {'ativo': par, 'direcao': direcao, 'confianca': conf, 'velas': velas}
        return None

    def calcular_horario_entrada(self):
        agora = datetime.now(FUSO_BR)
        if TIMEFRAME == "M5":
            minuto = agora.minute
            resto = minuto % 5
            if resto == 0 and agora.second == 0:
                return agora.replace(second=0, microsecond=0)
            else:
                return agora.replace(second=0, microsecond=0) + timedelta(minutes=5 - resto)
        else:  # M15
            minuto = agora.minute
            resto = minuto % 15
            if resto == 0 and agora.second == 0:
                return agora.replace(second=0, microsecond=0)
            else:
                return agora.replace(second=0, microsecond=0) + timedelta(minutes=15 - resto)

    def formatar_sinal(self, sinal, horario):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        hora = horario.strftime('%H:%M')
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM IA TRADER ✅
⏲ EXPIRAÇÃO: {TIMEFRAME}

👉🏼 HORARIO: {hora}

🏳ATIVO: {ativo}-OTC {direcao}

🍀🍀BOA SORTE 🍀 🍀"""

    async def monitorar_resultado(self, sinal, horario_entrada):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        timeframe_seg = 300 if TIMEFRAME == "M5" else 900

        agora = datetime.now(FUSO_BR)
        espera = (horario_entrada + timedelta(seconds=timeframe_seg - 5) - agora).total_seconds()
        if espera > 0:
            await asyncio.sleep(espera)
        await asyncio.sleep(10)
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
            if USAR_GALE:
                proxima_vela = horario_entrada + timedelta(seconds=timeframe_seg)
                agora = datetime.now(FUSO_BR)
                espera = (proxima_vela + timedelta(seconds=timeframe_seg - 5) - agora).total_seconds()
                if espera > 0:
                    await asyncio.sleep(espera)
                await asyncio.sleep(10)
                await self.atualizar_velas()
                velas = self.velas[ativo]
                ganhou_gale = False
                for v in velas:
                    if v['time'].replace(second=0, microsecond=0) == proxima_vela.replace(second=0, microsecond=0):
                        ganhou_gale = v['close'] > v['open'] if direcao == 'CALL' else v['close'] < v['open']
                        break
                if ganhou_gale:
                    self.placar['g1'] += 1
                    resultado = "✅ WIN GALE 1"
                else:
                    self.placar['l'] += 1
                    resultado = "❌ LOSS"
            else:
                self.placar['l'] += 1
                resultado = "❌ LOSS"

        total = self.placar['w'] + self.placar['g1'] + self.placar['l']
        tx = round(((self.placar['w'] + self.placar['g1']) / total) * 100, 1) if total > 0 else 0.0
        msg = f"""{resultado}
📊 {ativo}-OTC | {direcao} {'🟢' if direcao=='CALL' else '🔴'}
📊 Placar: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L
🎯 Assertividade: {tx}%"""
        self.tg.send(msg)

    async def executar(self):
        banner()
        print(f"⚛️ Bot OTC Trend Alignment ({TIMEFRAME}) iniciando...")
        self.tg.send(f"🔥 *QUANTUM IA TRADER ({TIMEFRAME}) ATIVADO*\n📊 Estratégia: OTC Trend Alignment\n🔄 Gale 1\n📌 Apenas 3 pares OTC\n⏰ Sinal {ANTECEDENCIA}s antes")
        while True:
            try:
                await self.atualizar_velas()
                sinal = self.buscar_sinal()
                if sinal and time.time() - self.ult_sinal > INTERVALO_MINIMO:
                    horario_entrada = self.calcular_horario_entrada()
                    horario_envio = horario_entrada - timedelta(seconds=ANTECEDENCIA)

                    agora = datetime.now(FUSO_BR)
                    espera = (horario_envio - agora).total_seconds()
                    if espera > 0:
                        print(f"⏳ Aguardando {espera:.0f}s para enviar sinal...")
                        await asyncio.sleep(espera)

                    self.ult_sinal = time.time()
                    msg = self.formatar_sinal(sinal, horario_entrada)
                    self.tg.send(msg)
                    print(f"⚛️ {sinal['ativo']}-OTC {sinal['direcao']} | Confiança: {sinal['confianca']:.0f}%")
                    asyncio.create_task(self.monitorar_resultado(sinal, horario_entrada))
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("🛑 Encerrado.")
                break
            except Exception as e:
                print(f"Erro: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    bot = BotPowerTrend()
    asyncio.run(bot.executar())
