#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M1 - CONSENSO FORTE E FILTROS AVANÇADOS
🕯️ Estratégias: MHI 1, MHI 2, VITUXO 2.0, Milhão Minoria, C3
🎯 Consenso de 3+ estratégias + tendência SMA20 + filtro de pavio
🛡️ Horário: 8h às 12h
🔄 Placar diário automático
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# Configurações
INTERVALO_MINIMO = 300       # 5 min entre sinais
USAR_GALE = True
ANTECEDENCIA = 30            # segundos antes da entrada
CONFIANCA_MINIMA = 70        # confiança mínima das estratégias

def banner():
    print("⚛️ QUANTUM IA M1 - Consenso Forte | Placar Diário")

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

# Estratégias
class MHI1:
    offset = 0
    def analisar(self, velas):
        if len(velas) < 10: return None
        q = list(velas)[-6:-3]
        calls = sum(1 for v in q if v['close'] > v['open'])
        puts = 3 - calls
        if calls == 1: return ('CALL', 70)
        elif puts == 1: return ('PUT', 70)
        return None

class MHI2:
    offset = 1
    def analisar(self, velas):
        if len(velas) < 10: return None
        q = list(velas)[-6:-3]
        calls = sum(1 for v in q if v['close'] > v['open'])
        puts = 3 - calls
        if calls == 1: return ('CALL', 68)
        elif puts == 1: return ('PUT', 68)
        return None

class Vituxo2:
    offset = 2
    def analisar(self, velas):
        if len(velas) < 10: return None
        q = list(velas)[-6:-3]
        calls = sum(1 for v in q if v['close'] > v['open'])
        puts = 3 - calls
        if calls > puts: return ('CALL', 70)
        elif puts > calls: return ('PUT', 70)
        return None

class MilhaoMinoria:
    offset = 0
    def analisar(self, velas):
        if len(velas) < 11: return None
        q = list(velas)[-11:-6]
        calls = sum(1 for v in q if v['close'] > v['open'])
        puts = 5 - calls
        if 0 < calls < puts: return ('CALL', 72)
        elif 0 < puts < calls: return ('PUT', 72)
        return None

class C3:
    offset = 0
    def analisar(self, velas):
        if len(velas) < 7: return None
        ref = velas[-6]
        if ref['close'] > ref['open']: return ('CALL', 65)
        elif ref['close'] < ref['open']: return ('PUT', 65)
        return None

# Bot
class BotM1:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.estrategias = [
            ('MHI 1', MHI1()),
            ('MHI 2', MHI2()),
            ('VITUXO 2.0', Vituxo2()),
            ('Milhão Minoria', MilhaoMinoria()),
            ('C3', C3())
        ]
        self.iq_api = None
        self.placar = {'w': 0, 'g1': 0, 'l': 0}
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

    def buscar_sinal_consenso(self):
        hora = datetime.now(FUSO_BR).hour
        if hora < 8 or hora > 12:
            return None

        for par, velas in self.velas.items():
            if len(velas) < 30:
                continue

            # Tendência SMA20
            precos = [v['close'] for v in velas]
            sma20 = sum(precos[-20:]) / 20
            atual = precos[-1]

            votos_call = []
            votos_put = []
            for nome_est, est in self.estrategias:
                resultado = est.analisar(velas)
                if resultado:
                    direcao, conf = resultado
                    if conf >= CONFIANCA_MINIMA:
                        if direcao == 'CALL':
                            votos_call.append(conf)
                        else:
                            votos_put.append(conf)

            # Exige consenso de pelo menos 3 estratégias
            if len(votos_call) >= 3 and atual > sma20:
                conf_media = sum(votos_call) / len(votos_call)
                vela = velas[-1]
                corpo = abs(vela['close'] - vela['open'])
                if corpo > 0:
                    pavio_sup = vela['high'] - max(vela['close'], vela['open'])
                    if pavio_sup > corpo * 0.4:
                        continue
                return {'ativo': par, 'direcao': 'CALL', 'confianca': conf_media}

            if len(votos_put) >= 3 and atual < sma20:
                conf_media = sum(votos_put) / len(votos_put)
                vela = velas[-1]
                corpo = abs(vela['close'] - vela['open'])
                if corpo > 0:
                    pavio_inf = min(vela['close'], vela['open']) - vela['low']
                    if pavio_inf > corpo * 0.4:
                        continue
                return {'ativo': par, 'direcao': 'PUT', 'confianca': conf_media}
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
            if USAR_GALE:
                proxima_vela = horario_entrada + timedelta(minutes=1)
                agora = datetime.now(FUSO_BR)
                espera = (proxima_vela + timedelta(minutes=1) - agora).total_seconds()
                if espera > 0:
                    await asyncio.sleep(espera)
                await asyncio.sleep(5)
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

    def verificar_zeramento_diario(self):
        agora = datetime.now(FUSO_BR)
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'g1': 0, 'l': 0}
            self.tg.send("🔄 *PLACAR ZERADO AUTOMATICAMENTE PARA O NOVO DIA*")
            print("🔄 Placar zerado para o novo dia.")

    async def executar(self):
        banner()
        print("⚛️ Bot M1 com consenso forte iniciando...")
        self.tg.send("🔥 *QUANTUM IA M1 ATIVADO*\n📊 Consenso de 3+ estratégias\n🛡️ Filtros: horário, pavio, tendência\n🔄 Placar diário automático")
        while True:
            try:
                self.verificar_zeramento_diario()
                await self.atualizar_velas()
                sinal = self.buscar_sinal_consenso()
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
    bot = BotM1()
    asyncio.run(bot.executar())
