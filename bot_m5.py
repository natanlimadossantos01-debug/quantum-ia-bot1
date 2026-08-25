#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M5 - FOREX - ANÁLISE 30s ANTES
🎯 Analisa até 30 segundos antes da entrada
📊 Confiança mínima: 62%
🛡️ Filtro de volatilidade
🔄 Gale 1
✅ Correção: close vs open
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

INTERVALO_MINIMO = 300
USAR_GALE = True
ANTECEDENCIA = 30            # Envia 30 segundos antes
CONFIANCA_MINIMA = 62
TIMEFRAME = 300              # M5

ATR_MIN = 0.00005
ATR_MAX = 0.0050

def banner():
    print("⚛️ QUANTUM IA M5 - Análise 30s Antes")

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

ATIVOS = {
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "EURJPY": "EURJPY",
    "USDJPY": "USDJPY"
}

class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c
    def send(self, txt):
        try: requests.post(f"{self.url}/sendMessage", json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"}, timeout=10)
        except: pass

# 5 Estratégias
class Mortalha:
    def sma(self, d, p):
        try:
            if len(d) >= p: return sum(d[-p:])/p
            return sum(d)/len(d) if d else 0
        except: return 0
    def wma(self, d, p):
        try:
            if len(d) < p: return sum(d)/len(d) if d else 0
            w = np.arange(1, p+1)
            return np.sum(np.array(d[-p:])*w)/np.sum(w)
        except: return 0
    def analisar(self, v):
        try:
            if len(v) < 30: return None, 0
            c = np.array([x['close'] for x in v])
            b1 = np.zeros(len(c))
            for i in range(len(c)):
                if i >= 33: b1[i] = self.sma(c[:i+1], 1) - self.sma(c[:i+1], 34)
            b2 = np.zeros(len(b1))
            for i in range(len(b1)):
                if i >= 3: b2[i] = self.wma(b1[:i+1], 4)
            if b1[-1] > b2[-1] and b1[-2] <= b2[-2]: return 'CALL', min(45+abs(b1[-1]-b2[-1])*10000, 90)
            if b1[-1] < b2[-1] and b1[-2] >= b2[-2]: return 'PUT', min(45+abs(b1[-1]-b2[-1])*10000, 90)
            return None, 0
        except: return None, 0

class Formiga:
    def ema(self, p, pe):
        try:
            if len(p) < pe: return sum(p)/len(p) if p else 0
            return np.mean(p[-pe:])
        except: return 0
    def analisar(self, v):
        try:
            if len(v) < 15: return None, 0
            precos = np.array([x['close'] for x in v])
            ema5 = self.ema(precos, 5); ema10 = self.ema(precos, 10)
            dif = ((ema5-ema10)/ema10)*100 if ema10 > 0 else 0
            sc, sp = 0, 0
            if dif > 0.02: sc += 3
            elif dif > 0.005: sc += 1
            elif dif < -0.02: sp += 3
            elif dif < -0.005: sp += 1
            if sc >= 2 and sc > sp: return 'CALL', min(50+sc*4, 85)
            if sp >= 2 and sp > sc: return 'PUT', min(50+sp*4, 85)
            return None, 0
        except: return None, 0

class Fortaleza:
    def rsi(self, p, pe=7):
        try:
            if len(p) < pe+1: return 50
            d = np.diff(list(p[-pe-1:]))
            g = np.where(d > 0, d, 0); l = np.where(d < 0, -d, 0)
            mg = np.mean(g) if len(g) > 0 else 0
            mp = np.mean(l) if len(l) > 0 else 0
            if mp == 0: return 100
            return 100 - (100/(1+mg/mp))
        except: return 50
    def analisar(self, v):
        try:
            if len(v) < 18: return None, 0
            precos = np.array([x['close'] for x in v])
            rsi_val = self.rsi(precos)
            m = np.mean(precos[-10:]) if len(precos) >= 10 else np.mean(precos)
            s = np.std(precos[-10:]) if len(precos) >= 10 else 0
            bs = m + 2*s; bi = m - 2*s
            sc, sp = 0, 0
            if rsi_val < 30: sc += 3
            elif rsi_val < 40: sc += 2
            if rsi_val > 70: sp += 3
            elif rsi_val > 60: sp += 2
            if precos[-1] <= bi*1.0004: sc += 3
            if precos[-1] >= bs*0.9996: sp += 3
            if sc >= 4 and sc > sp: return 'CALL', min(60+sc*3, 90)
            if sp >= 4 and sp > sc: return 'PUT', min(60+sp*3, 90)
            return None, 0
        except: return None, 0

class RaioNegro:
    def analisar(self, v):
        try:
            if len(v) < 12: return None, 0
            precos = np.array([x['close'] for x in v])
            ema5 = np.mean(precos[-5:])
            ema13 = np.mean(precos[-13:])
            macd = ema5 - ema13
            sinal = macd * 0.5
            mom = precos[-1] - precos[-3] if len(precos) >= 3 else 0
            sc, sp = 0, 0
            if macd > sinal and macd > 0: sc += 3
            elif macd > sinal: sc += 1
            elif macd < sinal and macd < 0: sp += 3
            elif macd < sinal: sp += 1
            if mom > 0.00003: sc += 3
            elif mom > 0: sc += 1
            elif mom < -0.00003: sp += 3
            elif mom < 0: sp += 1
            if sc >= 2 and sc > sp: return 'CALL', min(48+sc*4, 85)
            if sp >= 2 and sp > sc: return 'PUT', min(48+sp*4, 85)
            return None, 0
        except: return None, 0

class Tsunami:
    def analisar(self, v):
        try:
            if len(v) < 12: return None, 0
            precos = [x['close'] for x in v]
            altas = sum(1 for i in range(-min(5,len(v)-1), 0) if precos[i] > precos[i-1])
            sc, sp = 0, 0
            if altas >= 3: sc += 3
            elif altas <= 2: sp += 3
            if sc >= 2 and sc > sp: return 'CALL', min(50+sc*3, 85)
            if sp >= 2 and sp > sc: return 'PUT', min(50+sp*3, 85)
            return None, 0
        except: return None, 0

class Bot:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS}
        self.estrategias = [
            ('💀 Mortalha', Mortalha()),
            ('🐜 Formiga', Formiga()),
            ('🏰 Fortaleza', Fortaleza()),
            ('⚡ Raio Negro', RaioNegro()),
            ('🌊 Tsunami', Tsunami())
        ]
        self.iq_api = None
        self.placar = {'w': 0, 'g1': 0, 'l': 0}
        self.ult_sinal = 0
        self.sinais = 0
        self.ultimo_dia = datetime.now(FUSO_BR).day

    def conectar_iq(self):
        from iqoptionapi.stable_api import IQ_Option
        try:
            if self.iq_api:
                try: self.iq_api.close()
                except: pass
            self.iq_api = IQ_Option(EMAIL, SENHA)
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
        for nome, ativo_id in ATIVOS.items():
            try:
                if not api.check_connect():
                    api = await self.reconectar_se_necessario()
                    if not api:
                        break
                c = api.get_candles(ativo_id, TIMEFRAME, 80, time.time())
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
            except Exception as e:
                print(f"Erro {nome}: {e}")

    def calcular_atr(self, velas, periodo=14):
        if len(velas) < periodo + 1:
            return None
        trs = []
        for i in range(-periodo, 0):
            h = velas[i]['high']
            l = velas[i]['low']
            c_prev = velas[i-1]['close'] if i > -periodo else velas[i]['open']
            tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
            trs.append(tr)
        return np.mean(trs)

    def buscar_sinal(self):
        melhor = None
        melhor_score = 0
        
        for par, velas in self.velas.items():
            if len(velas) < 30:
                continue
            atr = self.calcular_atr(velas, 14)
            if atr is None or atr < ATR_MIN or atr > ATR_MAX:
                continue
            for nome_est, est in self.estrategias:
                resultado = est.analisar(velas)
                if resultado and len(resultado) >= 2:
                    d, c = resultado[0], resultado[1]
                    if d in ('CALL', 'PUT') and c >= CONFIANCA_MINIMA:
                        if c > melhor_score:
                            melhor_score = c
                            melhor = {'ativo': par, 'direcao': d, 'confianca': c, 'estrategia': nome_est}
        
        return melhor

    def calcular_horario_entrada(self):
        agora = datetime.now(FUSO_BR)
        minuto = agora.minute
        resto = minuto % 5
        if resto == 0 and agora.second == 0:
            return agora.replace(second=0, microsecond=0)
        else:
            return agora.replace(second=0, microsecond=0) + timedelta(minutes=5 - resto)

    def formatar_sinal(self, sinal, horario):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        conf = sinal['confianca']
        est = sinal['estrategia']
        hora = horario.strftime('%H:%M')
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM IA M5 ✅
⏲ EXPIRAÇÃO: M5

👉🏼 HORARIO: {hora}

🏳ATIVO: {ativo} {direcao}

📊 Confiança: {conf:.0f}%
🧠 Estratégia: {est}

🍀🍀BOA SORTE 🍀 🍀"""

    async def monitorar_resultado(self, sinal, horario_entrada):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        
        agora = datetime.now(FUSO_BR)
        espera = (horario_entrada + timedelta(minutes=5) - agora).total_seconds()
        if espera > 0:
            await asyncio.sleep(espera)
        await asyncio.sleep(10)
        await self.atualizar_velas()
        velas = self.velas[ativo]
        
        ganhou = False
        for v in velas:
            if v['time'].replace(second=0, microsecond=0) == horario_entrada.replace(second=0, microsecond=0):
                if direcao == 'CALL':
                    ganhou = v['close'] > v['open']
                else:
                    ganhou = v['close'] < v['open']
                break
        
        if ganhou:
            self.placar['w'] += 1
            resultado = "✅ WIN"
        else:
            if USAR_GALE:
                proxima_vela = horario_entrada + timedelta(minutes=5)
                agora = datetime.now(FUSO_BR)
                espera = (proxima_vela + timedelta(minutes=5) - agora).total_seconds()
                if espera > 0:
                    await asyncio.sleep(espera)
                await asyncio.sleep(10)
                await self.atualizar_velas()
                velas = self.velas[ativo]
                ganhou_gale = False
                for v in velas:
                    if v['time'].replace(second=0, microsecond=0) == proxima_vela.replace(second=0, microsecond=0):
                        if direcao == 'CALL':
                            ganhou_gale = v['close'] > v['open']
                        else:
                            ganhou_gale = v['close'] < v['open']
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
📊 {ativo} | {direcao} {'🟢' if direcao=='CALL' else '🔴'}
📊 Placar: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L
🎯 Assertividade: {tx}%"""
        self.tg.send(msg)

    def verificar_zeramento_diario(self):
        agora = datetime.now(FUSO_BR)
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'g1': 0, 'l': 0}
            self.tg.send("🔄 *PLACAR ZERADO*")
            print("🔄 Placar zerado.")

    async def executar(self):
        banner()
        print("⚛️ Bot M5 Forex iniciando...")
        self.tg.send(f"🔥 *QUANTUM IA M5*\n📊 5 Estratégias\n🎯 Confiança {CONFIANCA_MINIMA}%+\n⏱️ Análise 30s antes\n🔄 Gale 1")
        
        while True:
            try:
                self.verificar_zeramento_diario()
                
                agora = datetime.now(FUSO_BR)
                if agora.second == 0:
                    total_velas = sum(len(v) for v in self.velas.values())
                    print(f"💓 {agora.strftime('%H:%M:%S')} | Velas: {total_velas} | Sinais: {self.sinais}")
                    
                    if total_velas == 0:
                        print("🔄 Sem velas! Reconectando...")
                        self.iq_api = None
                
                # Atualiza velas
                await self.atualizar_velas()
                
                # Calcula horário de entrada
                horario_entrada = self.calcular_horario_entrada()
                horario_envio = horario_entrada - timedelta(seconds=ANTECEDENCIA)
                
                # Verifica se está no momento de analisar (30s antes)
                agora = datetime.now(FUSO_BR)
                tempo_ate_envio = (horario_envio - agora).total_seconds()
                
                # Só analisa quando estiver a 35 segundos ou menos da entrada
                if 0 <= tempo_ate_envio <= 35:
                    sinal = self.buscar_sinal()
                    
                    if sinal and time.time() - self.ult_sinal > INTERVALO_MINIMO:
                        # Aguarda até exatamente 30s antes
                        if tempo_ate_envio > 0:
                            await asyncio.sleep(tempo_ate_envio)
                        
                        self.ult_sinal = time.time()
                        self.sinais += 1
                        msg = self.formatar_sinal(sinal, horario_entrada)
                        self.tg.send(msg)
                        asyncio.create_task(self.monitorar_resultado(sinal, horario_entrada))
                
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                print("🛑 Encerrado.")
                break
            except Exception as e:
                print(f"Erro: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(Bot().run())
