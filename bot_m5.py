#!/usr/bin/env python3
"""
⚛️ QUANTUM BOT PRO - SINAIS M1 (14 ESTRATÉGIAS)
🕯️ 12 Quadrantes + 5-2-0 + Chinesa 3.0
🛡️ Filtros: Pavio, Tendência, Vela Forte
📨 Envia sinais para Telegram (sem executar trades)
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os, random
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

def banner():
    print("⚛️ QUANTUM BOT PRO - Modo Sinal | 14 Estratégias")

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
    "EURUSD":"EURUSD-OTC",
    "GBPUSD":"GBPUSD-OTC",
    "EURJPY":"EURJPY-OTC"
}

class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c
    def send(self, txt):
        try: requests.post(f"{self.url}/sendMessage", json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"}, timeout=5)
        except: pass

# ------------------------- ESTRATÉGIAS -------------------------
class MHI1:
    def analisar(self, v):
        try:
            if len(v) < 10: return None, 0
            velas = list(v[-6:-3])
            calls = sum(1 for x in velas if x['close'] > x['open'])
            puts = 3 - calls
            if 0 < calls < puts: return 'CALL', 72
            if 0 < puts < calls: return 'PUT', 72
            return None, 0
        except: return None, 0

class MHI2:
    def analisar(self, v):
        try:
            if len(v) < 10: return None, 0
            velas = list(v[-6:-3])
            calls = sum(1 for x in velas if x['close'] > x['open'])
            puts = 3 - calls
            if 0 < calls < puts: return 'CALL', 70
            if 0 < puts < calls: return 'PUT', 70
            return None, 0
        except: return None, 0

class MHI3:
    def analisar(self, v):
        try:
            if len(v) < 10: return None, 0
            velas = list(v[-6:-3])
            calls = sum(1 for x in velas if x['close'] > x['open'])
            puts = 3 - calls
            if 0 < calls < puts: return 'CALL', 68
            if 0 < puts < calls: return 'PUT', 68
            return None, 0
        except: return None, 0

class Vituxo2:
    def analisar(self, v):
        try:
            if len(v) < 10: return None, 0
            velas = list(v[-5:-2])
            calls = sum(1 for x in velas if x['close'] > x['open'])
            puts = 3 - calls
            if calls > puts: return 'CALL', 70
            if puts > calls: return 'PUT', 70
            return None, 0
        except: return None, 0

class C3:
    def analisar(self, v):
        try:
            if len(v) < 7: return None, 0
            ref = v[-6]
            if ref['close'] > ref['open']: return 'CALL', 65
            if ref['close'] < ref['open']: return 'PUT', 65
            return None, 0
        except: return None, 0

class MSF:
    def analisar(self, v):
        try:
            if len(v) < 7: return None, 0
            ref = v[-6]
            if ref['close'] > ref['open']: return 'PUT', 65
            if ref['close'] < ref['open']: return 'CALL', 65
            return None, 0
        except: return None, 0

class MilhaoMaioria:
    def analisar(self, v):
        try:
            if len(v) < 11: return None, 0
            velas = list(v[-11:-6])
            calls = sum(1 for x in velas if x['close'] > x['open'])
            puts = 5 - calls
            if calls > puts: return 'CALL', 72
            if puts > calls: return 'PUT', 72
            return None, 0
        except: return None, 0

class MilhaoMinoria:
    def analisar(self, v):
        try:
            if len(v) < 11: return None, 0
            velas = list(v[-11:-6])
            calls = sum(1 for x in velas if x['close'] > x['open'])
            puts = 5 - calls
            if 0 < calls < puts: return 'CALL', 74
            if 0 < puts < calls: return 'PUT', 74
            return None, 0
        except: return None, 0

class TresVizinhos:
    def analisar(self, v):
        try:
            if len(v) < 5: return None, 0
            ref = v[-2]
            if ref['close'] > ref['open']: return 'CALL', 66
            if ref['close'] < ref['open']: return 'PUT', 66
            return None, 0
        except: return None, 0

class DAKA:
    def analisar(self, v):
        try:
            if len(v) < 10: return None, 0
            ref = v[-4]
            if ref['close'] > ref['open']: return 'CALL', 68
            if ref['close'] < ref['open']: return 'PUT', 68
            return None, 0
        except: return None, 0

class Estrategia23:
    def analisar(self, v):
        try:
            if len(v) < 5: return None, 0
            ref = v[-3]
            if ref['close'] > ref['open']: return 'CALL', 64
            if ref['close'] < ref['open']: return 'PUT', 64
            return None, 0
        except: return None, 0

class R7:
    def analisar(self, v):
        try:
            if len(v) < 14: return None, 0
            ref = v[-14]
            if ref['close'] > ref['open']: return 'CALL', 62
            if ref['close'] < ref['open']: return 'PUT', 62
            return None, 0
        except: return None, 0

class Estrategia520:
    def analisar(self, v):
        try:
            if len(v) < 25: return None, 0
            precos = [x['close'] for x in v]
            mm5 = np.mean(precos[-5:])
            media20 = np.mean(precos[-20:])
            std20 = np.std(precos[-20:])
            bs = media20 + 2*std20
            bi = media20 - 2*std20
            atual = precos[-1]
            if atual > mm5 and atual <= bi*1.002: return 'CALL', 78
            if atual < mm5 and atual >= bs*0.998: return 'PUT', 78
            return None, 0
        except: return None, 0

class Chinesa30:
    def analisar(self, v):
        try:
            if len(v) < 30: return None, 0
            precos = [x['close'] for x in v]
            ma20 = np.mean(precos[-20:])
            suporte = min(x['low'] for x in v[-10:])
            resistencia = max(x['high'] for x in v[-10:])
            atual = precos[-1]
            if atual > ma20 and v[-1]['high'] > resistencia: return 'CALL', 80
            if atual < ma20 and v[-1]['low'] < suporte: return 'PUT', 80
            return None, 0
        except: return None, 0

# ------------------------- FILTROS -------------------------
class FiltroTendencia:
    def __init__(self): self.forca_minima = 0.0002
    def analisar_tendencia(self, velas):
        if len(velas) < 20: return "NEUTRA", 0
        precos = [v['close'] for v in velas]
        ema9 = np.mean(precos[-9:]); ema21 = np.mean(precos[-21:])
        high = [v['high'] for v in velas]; low = [v['low'] for v in velas]
        plus_dm, minus_dm, tr = [], [], []
        for i in range(1, min(14, len(velas))):
            up_move = high[-i] - high[-i-1]
            down_move = low[-i-1] - low[-i]
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
            tr.append(max(high[-i]-low[-i], abs(high[-i]-precos[-i-1]), abs(low[-i]-precos[-i-1])))
        if not tr: return "NEUTRA", 0
        atr = np.mean(tr)
        plus_di = (np.mean(plus_dm)/atr*100) if atr>0 and plus_dm else 0
        minus_di = (np.mean(minus_dm)/atr*100) if atr>0 and minus_dm else 0
        dx = abs(plus_di - minus_di)/(plus_di + minus_di)*100 if (plus_di+minus_di)>0 else 0
        if ema9 > ema21*(1+self.forca_minima) and plus_di > minus_di:
            tendencia = "ALTA FORTE 📈" if dx>25 else "ALTA 📈"
        elif ema9 < ema21*(1-self.forca_minima) and minus_di > plus_di:
            tendencia = "BAIXA FORTE 📉" if dx>25 else "BAIXA 📉"
        else:
            tendencia = "NEUTRA ➡️"; dx = min(dx, 20)
        return tendencia, dx
    def sinal_alinhado(self, direcao, tendencia, forca):
        if "NEUTRA" in tendencia: return True
        if direcao == "CALL":
            return "ALTA" in tendencia or ("BAIXA" in tendencia and forca < 25)
        else:
            return "BAIXA" in tendencia or ("ALTA" in tendencia and forca < 25)

class FiltroPavio:
    @staticmethod
    def ok(velas, direcao):
        if len(velas) < 2: return True
        va, vb = velas[-1], velas[-2]
        corpo_va = abs(va['close'] - va['open'])
        if corpo_va == 0: return False
        if direcao == 'CALL':
            if va['high'] - max(va['close'], va['open']) > corpo_va * 0.4: return False
        else:
            if min(va['close'], va['open']) - va['low'] > corpo_va * 0.4: return False
        corpo_vb = abs(vb['close'] - vb['open'])
        if corpo_vb > 0:
            if direcao == 'CALL':
                if vb['high'] - max(vb['close'], vb['open']) > corpo_vb * 0.5: return False
            else:
                if min(vb['close'], vb['open']) - vb['low'] > corpo_vb * 0.5: return False
        range_total = va['high'] - va['low']
        if range_total > 0 and corpo_va < range_total * 0.3: return False
        return True

class FiltroVelaForte:
    @staticmethod
    def ok(velas):
        if len(velas) < 15: return True
        ranges = [velas[i]['high'] - velas[i]['low'] for i in range(-14, 0)]
        atr = np.mean(ranges)
        ultimo_range = velas[-1]['high'] - velas[-1]['low']
        return ultimo_range <= atr * 2.0

# ------------------------- BOT -------------------------
class BotProSinais:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.estrategias = [
            ('📊 MHI 1', MHI1()), ('📊 MHI 2', MHI2()), ('📊 MHI 3', MHI3()),
            ('📊 VITUXO 2.0', Vituxo2()), ('📊 C3', C3()), ('📊 MSF', MSF()),
            ('📊 Milhão Maioria', MilhaoMaioria()), ('📊 Milhão Minoria', MilhaoMinoria()),
            ('📊 3 Vizinhos', TresVizinhos()), ('📊 DAKA', DAKA()),
            ('📊 23', Estrategia23()), ('📊 R7', R7()),
            ('🔬 5-2-0', Estrategia520()), ('🔬 Chinesa 3.0', Chinesa30())
        ]
        self.filtro_tendencia = FiltroTendencia()
        self.ult_sinal = 0
        self.sinais_enviados = 0
        self.velas_dict = {}  # será preenchido com dados da IQ Option

    async def atualizar_velas(self):
        from iqoptionapi.stable_api import IQ_Option
        email = os.environ.get('IQ_EMAIL')
        senha = os.environ.get('IQ_SENHA')
        if not email or not senha:
            print("❌ Configure IQ_EMAIL e IQ_SENHA")
            return
        try:
            api = IQ_Option(email, senha)
            api.connect()
            for nome, ativo_id in ATIVOS_OTC.items():
                for retry in range(3):
                    try:
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
                    except: time.sleep(2)
            api.close()
        except Exception as e:
            print(f"❌ Erro ao obter velas: {e}")

    def buscar_sinal(self):
        for nome_par, velas in self.velas.items():
            if len(velas) < 30: continue
            tendencia, forca = self.filtro_tendencia.analisar_tendencia(velas)
            for nome_est, est in self.estrategias:
                try:
                    d, c = est.analisar(velas)
                    if d and c >= 65 and FiltroPavio.ok(velas, d) and FiltroVelaForte.ok(velas) and self.filtro_tendencia.sinal_alinhado(d, tendencia, forca):
                        return {'ativo': nome_par, 'direcao': d, 'confianca': c, 'estrategia': nome_est, 'tendencia': tendencia}
                except: pass
        return None

    async def executar(self):
        banner()
        print("⚛️ Bot Pro Sinais iniciando...")
        self.tg.send("🔥 *QUANTUM BOT PRO ATIVADO*\n📊 14 Estratégias | M1\n🛡️ Filtros: Pavio, Tendência, Vela Forte\n⏱️ Sinais a cada 5min")
        while True:
            try:
                await self.atualizar_velas()
                sinal = self.buscar_sinal()
                if sinal and time.time() - self.ult_sinal > 300:
                    self.sinais_enviados += 1
                    self.ult_sinal = time.time()
                    agora = datetime.now(FUSO_BR)
                    he = (agora.replace(second=0, microsecond=0) + timedelta(minutes=1)).strftime('%H:%M')
                    emoji = '🟢' if sinal['direcao']=='CALL' else '🔴'
                    msg = f"""⚛️ SINAL QUANTUM PRO ⚛️

⏰ Horário: {he}
💰 Ativo: {sinal['ativo']}-OTC
📈 Direção: {sinal['direcao']} {emoji}
⌛️ Expiração: M1
📊 Confiança: {sinal['confianca']:.0f}%
🧠 Estratégia: {sinal['estrategia']}
📐 Tendência: {sinal['tendencia']}

⚠️ Entrar somente no horário marcado.
🔄 1 recuperação (Gale 1)!"""
                    self.tg.send(msg)
                    print(f"⚛️ #{self.sinais_enviados} {sinal['ativo']}-OTC {sinal['direcao']} | {sinal['confianca']:.0f}% | {sinal['estrategia']}")
                await asyncio.sleep(30)
            except KeyboardInterrupt:
                print("🛑 Encerrado.")
                break
            except Exception as e:
                print(f"Erro: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    bot = BotProSinais()
    asyncio.run(bot.executar())
