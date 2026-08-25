#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M5 - FOREX REAL - CORREÇÃO CORRETA
🧠 Catálogo Inteligente
📊 5 Estratégias
🛡️ Filtro Pavio + Volatilidade
🔄 Reconexão automática
💓 Heartbeat
✅ Correção: close vs open (fechamento real)
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

INTERVALO_MINIMO = 300
USAR_GALE = True
ANTECEDENCIA = 30
CONFIANCA_MINIMA = 62

ATR_MIN = 0.0001
ATR_MAX = 0.0008

def banner():
    print("⚛️ QUANTUM IA M5 - Forex | Correção Correta")

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

class CatalogadorInteligente:
    def __init__(self):
        self.performance = {}
        self.total_operacoes = 0
        
    def registrar(self, estrategia, par, venceu):
        chave = f"{estrategia}|{par}"
        if chave not in self.performance:
            self.performance[chave] = {'wins': 0, 'losses': 0, 'total': 0, 'estrategia': estrategia, 'par': par}
        self.performance[chave]['total'] += 1
        if venceu: self.performance[chave]['wins'] += 1
        else: self.performance[chave]['losses'] += 1
        self.total_operacoes += 1
    
    def get_taxa(self, estrategia, par):
        chave = f"{estrategia}|{par}"
        if chave in self.performance:
            p = self.performance[chave]
            return round((p['wins']/p['total'])*100, 1) if p['total'] > 0 else 0
        return 0

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

class QuantumIA:
    def __init__(self):
        self.estrategias = [
            ('💀 Mortalha', Mortalha()),
            ('🐜 Formiga', Formiga()),
            ('🏰 Fortaleza', Fortaleza()),
            ('⚡ Raio Negro', RaioNegro()),
            ('🌊 Tsunami', Tsunami())
        ]
        self.catalogador = CatalogadorInteligente()

    def _calcular_atr(self, velas, periodo=14):
        if len(velas) < periodo + 1:
            return None
        trs = []
        for i in range(-periodo, 0):
            h = velas[i]['high']
            l = velas[i]['low']
            c_prev = velas[i-1]['close'] if i > -periodo else velas[i]['open']
            tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
            trs.append(tr)
        return np.mean(trs) if trs else None
    
    def _volatilidade_ok(self, velas):
        atr = self._calcular_atr(velas, 14)
        if atr is None:
            return False
        return ATR_MIN <= atr <= ATR_MAX

    def _pavio_ok(self, velas, direcao):
        if len(velas) < 1:
            return True
        va = velas[-1]
        corpo = abs(va['close'] - va['open'])
        if corpo == 0:
            return True
        if direcao == 'CALL':
            pavio_sup = va['high'] - max(va['close'], va['open'])
            return pavio_sup <= corpo * 0.6
        else:
            pavio_inf = min(va['close'], va['open']) - va['low']
            return pavio_inf <= corpo * 0.6

    def obter_sinal(self, velas_dict):
        melhor = None
        melhor_score = 0
        
        for par, velas in velas_dict.items():
            if len(velas) < 30:
                continue
            if not self._volatilidade_ok(velas):
                continue
            for nome_est, est in self.estrategias:
                resultado = est.analisar(velas)
                if resultado and len(resultado) >= 2:
                    d, c = resultado[0], resultado[1]
                    if d in ('CALL', 'PUT') and c >= CONFIANCA_MINIMA:
                        if self._pavio_ok(velas, d):
                            score = c
                            taxa = self.catalogador.get_taxa(nome_est, par)
                            if taxa > 60:
                                score += taxa * 0.3
                            if score > melhor_score:
                                melhor_score = score
                                melhor = {'ativo': par, 'direcao': d, 'confianca': c, 'estrategia': nome_est}
        
        return melhor

class IQAPI:
    def __init__(self, e, s, a):
        self.e = e
        self.s = s
        self.a = a
        self.api = None
        self.velas = {nome: deque(maxlen=100) for nome in a}
        self.ok = False
    
    def conectar(self):
        for t in range(5):
            try:
                if self.api:
                    try: self.api.close()
                    except: pass
                    time.sleep(2)
                self.api = IQ_Option(self.e, self.s)
                ok, _ = self.api.connect()
                if ok:
                    self.ok = True
                    return True
                time.sleep(5*(t+1))
            except:
                time.sleep(5*(t+1))
        self.ok = False
        return False
    
    def obter(self, ativo_id, qtd=80):
        for retry in range(3):
            if not self.ok and not self.conectar():
                return 0
            try:
                c = self.api.get_candles(ativo_id, 300, qtd, time.time())
                if c and len(c) > 0:
                    nome = [k for k, v in self.a.items() if v == ativo_id][0]
                    self.velas[nome].clear()
                    for x in c[-qtd:]:
                        if isinstance(x, dict):
                            try:
                                self.velas[nome].append({
                                    'time': datetime.fromtimestamp(x.get('from',0), FUSO_BR),
                                    'open': float(x['open']), 'high': float(x['max']),
                                    'low': float(x['min']), 'close': float(x['close']),
                                    'volume': int(x.get('volume',0))
                                })
                            except: pass
                    return len(c)
            except:
                self.ok = False
                if retry < 2:
                    time.sleep(3)
                    continue
        return 0
    
    def atualizar(self):
        if not self.ok:
            self.conectar()
        for n, i in self.a.items():
            try:
                self.obter(i)
            except: pass

class Bot:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.m = QuantumIA()
        self.iq = IQAPI(EMAIL, SENHA, ATIVOS)
        self.placar = {'w': 0, 'g1': 0, 'l': 0}
        self.op = False
        self.ult = 0
        self.sinais = 0
        self.ultimo_dia = datetime.now(FUSO_BR).day

    def calcular_horario_entrada(self):
        agora = datetime.now(FUSO_BR)
        minuto = agora.minute
        resto = minuto % 5
        if resto == 0 and agora.second == 0:
            return agora.replace(second=0, microsecond=0)
        else:
            return agora.replace(second=0, microsecond=0) + timedelta(minutes=5 - resto)

    def fmt_sinal(self, s):
        horario = self.calcular_horario_entrada()
        he = horario.strftime('%H:%M')
        e = "🟢" if s['direcao'] == 'CALL' else "🔴"
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM IA M5 ✅
⏲ EXPIRAÇÃO: M5

👉🏼 HORARIO: {he}

🏳ATIVO: {s['ativo']} {s['direcao']}

📊 Confiança: {s['confianca']:.0f}%
🧠 Estratégia: {s['estrategia']}

🍀🍀BOA SORTE 🍀 🍀"""

    def fmt_corr(self, r, s):
        total = self.placar['w'] + self.placar['g1'] + self.placar['l']
        tx = round(((self.placar['w'] + self.placar['g1']) / total) * 100, 1) if total > 0 else 0
        return f"""{r}
📊 {s['ativo']} | {s['direcao']}
📊 Placar: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L
🎯 Assertividade: {tx}%"""

    async def corrigir(self, sinal):
        at = sinal['ativo']
        d = sinal['direcao']
        estrategia = sinal['estrategia']
        
        try:
            horario_entrada = self.calcular_horario_entrada()
            
            # Aguarda o fechamento da vela M5
            agora = datetime.now(FUSO_BR)
            espera = (horario_entrada + timedelta(minutes=5) - agora).total_seconds()
            if espera > 0:
                await asyncio.sleep(espera)
            await asyncio.sleep(10)
            
            self.iq.atualizar()
            velas = self.iq.velas[at]
            
            # ✅ CORREÇÃO: verifica close vs open
            ganhou = False
            for vela in velas:
                if vela['time'].replace(second=0, microsecond=0) == horario_entrada.replace(second=0, microsecond=0):
                    if d == 'CALL':
                        ganhou = vela['close'] > vela['open']
                    else:
                        ganhou = vela['close'] < vela['open']
                    break
            
            if ganhou:
                self.placar['w'] += 1
                self.m.catalogador.registrar(estrategia, at, True)
                self.tg.send(self.fmt_corr("✅ WIN", sinal))
                self.op = False
                return
            
            # Gale 1
            proxima_vela = horario_entrada + timedelta(minutes=5)
            agora = datetime.now(FUSO_BR)
            espera = (proxima_vela + timedelta(minutes=5) - agora).total_seconds()
            if espera > 0:
                await asyncio.sleep(espera)
            await asyncio.sleep(10)
            
            self.iq.atualizar()
            velas = self.iq.velas[at]
            
            ganhou_gale = False
            for vela in velas:
                if vela['time'].replace(second=0, microsecond=0) == proxima_vela.replace(second=0, microsecond=0):
                    if d == 'CALL':
                        ganhou_gale = vela['close'] > vela['open']
                    else:
                        ganhou_gale = vela['close'] < vela['open']
                    break
            
            if ganhou_gale:
                self.placar['g1'] += 1
                self.m.catalogador.registrar(estrategia, at, True)
                self.tg.send(self.fmt_corr("✅ WIN GALE 1", sinal))
                self.op = False
                return
            
            self.placar['l'] += 1
            self.m.catalogador.registrar(estrategia, at, False)
            self.tg.send(self.fmt_corr("❌ LOSS", sinal))
            self.op = False
            
        except Exception as e:
            print(f"Erro correção: {e}")
            self.op = False

    async def run(self):
        banner()
        print("⚛️ Bot M5 Forex iniciando...")
        self.tg.send(f"🔥 *QUANTUM IA M5*\n📊 5 Estratégias\n🎯 Confiança {CONFIANCA_MINIMA}%+\n✅ Correção: close vs open\n🔄 Gale 1")
        
        if not self.iq.conectar():
            print("❌ Falha conexão!")
            return
        
        self.iq.atualizar()
        
        while True:
            try:
                agora = datetime.now(FUSO_BR)
                
                if agora.second == 0:
                    total_velas = sum(len(v) for v in self.iq.velas.values())
                    print(f"💓 {agora.strftime('%H:%M:%S')} | Velas: {total_velas} | Sinais: {self.sinais}")
                    
                    if total_velas == 0:
                        print("🔄 Sem velas! Reconectando...")
                        self.iq.ok = False
                
                if agora.second in [0, 30]:
                    self.iq.atualizar()
                
                if not self.op:
                    sinal = self.m.obter_sinal(self.iq.velas)
                    if sinal and time.time() - self.ult > INTERVALO_MINIMO:
                        self.op = True
                        self.sinais += 1
                        self.ult = time.time()
                        self.tg.send(self.fmt_sinal(sinal))
                        asyncio.create_task(self.corrigir(sinal))
                
                await asyncio.sleep(3)
                
            except KeyboardInterrupt:
                print("🛑 Encerrado.")
                break
            except Exception as e:
                print(f"❌ {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(Bot().run())
