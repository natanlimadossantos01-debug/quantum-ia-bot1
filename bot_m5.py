#!/usr/bin/env python3
"""
⚛️ QUANTUM PRO M1 - LÓGICA AVANÇADA
🧠 Multi-Timeframe (M1 + M5)
📊 Volatilidade Adaptativa
🔍 Análise de 5 velas
⏰ Bloqueio de horários ruins
💪 Vela Forte + Momentum
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

INTERVALO_MINIMO = 300
USAR_GALE = True
MULTIPLICADOR_GALE = 1.5
ANTECEDENCIA = 10
TIMEFRAME = 60
CONFIANCA_MINIMA = 70

def banner():
    print("⚛️ QUANTUM PRO M1 - Lógica Avançada")

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
    "EURUSD": "EURUSD-OTC",
    "GBPUSD": "GBPUSD-OTC",
    "EURJPY": "EURJPY-OTC",
    "USDJPY": "USDJPY-OTC",
    "AUDUSD": "AUDUSD-OTC",
    "EURGBP": "EURGBP-OTC",
    "USDCHF": "USDCHF-OTC",
    "USDCAD": "USDCAD-OTC",
    "NZDUSD": "NZDUSD-OTC",
    "AUDCAD": "AUDCAD-OTC",
    "GBPJPY": "GBPJPY-OTC",
    "EURAUD": "EURAUD-OTC"
}

class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c
    def send(self, txt):
        try: requests.post(f"{self.url}/sendMessage", json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"}, timeout=10)
        except: pass

# ═══════════════════════════════════════════
# 🚫 HORÁRIOS RUINS (baseado em experiência)
# ═══════════════════════════════════════════
def horario_bom():
    """
    Bloqueia horários conhecidos como ruins para OTC
    - 03:00 às 05:00 (baixa liquidez)
    - 12:00 às 13:00 (almoço)
    - 19:00 às 20:00 (transição)
    """
    agora = datetime.now(FUSO_BR)
    hora = agora.hour
    
    # Horários ruins
    if 3 <= hora < 5:
        return False
    if 12 <= hora < 13:
        return False
    if 19 <= hora < 20:
        return False
    
    return True

# ═══════════════════════════════════════════
# 📊 ANÁLISE DE VOLATILIDADE ADAPTATIVA
# ═══════════════════════════════════════════
def calcular_atr(velas, periodo=14):
    if len(velas) < periodo + 1:
        return 0
    trs = []
    for i in range(-periodo, 0):
        h = velas[i]['high']
        l = velas[i]['low']
        c_prev = velas[i-1]['close'] if i > -periodo else velas[i]['open']
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    return np.mean(trs)

def volatilidade_ok(velas):
    """Volatilidade adaptativa - ajusta conforme o par"""
    atr = calcular_atr(velas, 14)
    if atr == 0:
        return False
    
    # Média das últimas 20 velas
    ranges = [v['high'] - v['low'] for v in velas[-20:]]
    range_medio = np.mean(ranges)
    
    # ATR deve estar entre 0.5x e 2.5x do range médio
    if atr < range_medio * 0.5:
        return False  # Muito parado
    if atr > range_medio * 2.5:
        return False  # Muito volátil
    
    return True

# ═══════════════════════════════════════════
# 🛡️ ANTI-PAVIO
# ═══════════════════════════════════════════
def tem_pavio_excessivo(vela):
    corpo = abs(vela['close'] - vela['open'])
    range_total = vela['high'] - vela['low']
    
    if range_total == 0:
        return True
    
    pavio_sup = vela['high'] - max(vela['close'], vela['open'])
    pavio_inf = min(vela['close'], vela['open']) - vela['low']
    
    pct_pavio_sup = pavio_sup / range_total
    pct_pavio_inf = pavio_inf / range_total
    pct_pavio_total = (pavio_sup + pavio_inf) / range_total
    
    if pct_pavio_sup > 0.35:
        return True
    if pct_pavio_inf > 0.35:
        return True
    if pct_pavio_total > 0.60:
        return True
    
    return False

# ═══════════════════════════════════════════
# 🔍 ANÁLISE DE 5 VELAS + MOMENTUM
# ═══════════════════════════════════════════
class QuantumPro:
    """
    Lógica Avançada:
    1. Análise de 5 velas (não 3)
    2. Confirmação de momentum
    3. Alinhamento multi-timeframe
    4. Força da vela atual
    """
    def analisar(self, velas):
        if len(velas) < 30:
            return None, 0
        
        vela = velas[-1]
        
        # 🛡️ FILTRO 1: Anti-pavio
        if tem_pavio_excessivo(vela):
            return None, 0
        
        # 💪 FILTRO 2: Vela forte
        corpo = abs(vela['close'] - vela['open'])
        range_total = vela['high'] - vela['low']
        
        if range_total == 0:
            return None, 0
        
        forca = (corpo / range_total) * 100
        if forca < 50:
            return None, 0
        
        # 📊 FILTRO 3: Volatilidade
        if not volatilidade_ok(velas):
            return None, 0
        
        # 📈 FILTRO 4: Tendência (SMA20)
        precos = [v['close'] for v in velas]
        sma20 = sum(precos[-20:]) / 20
        atual = precos[-1]
        
        # 🔍 FILTRO 5: Análise de 5 velas
        ultimas_5 = list(velas)[-5:]
        calls_5 = sum(1 for v in ultimas_5 if v['close'] > v['open'])
        puts_5 = 5 - calls_5
        
        # 🔍 FILTRO 6: Análise de 3 velas
        ultimas_3 = list(velas)[-3:]
        calls_3 = sum(1 for v in ultimas_3 if v['close'] > v['open'])
        puts_3 = 3 - calls_3
        
        # 📊 FILTRO 7: Momentum (aceleração)
        momentum = precos[-1] - precos[-3]
        momentum_anterior = precos[-2] - precos[-4]
        acelerando_alta = momentum > 0 and momentum > momentum_anterior
        acelerando_baixa = momentum < 0 and momentum < momentum_anterior
        
        # 🎯 SINAIS FORTES (4+ confluências)
        
        # CALL muito forte: 4+ velas altas + tendência alta + vela forte + momentum
        if calls_5 >= 4 and calls_3 >= 3 and atual > sma20 and vela['close'] > vela['open'] and acelerando_alta:
            conf = 80 + forca * 0.1
            return 'CALL', min(conf, 90)
        
        # PUT muito forte: 4+ velas baixas + tendência baixa + vela forte + momentum
        if puts_5 >= 4 and puts_3 >= 3 and atual < sma20 and vela['close'] < vela['open'] and acelerando_baixa:
            conf = 80 + forca * 0.1
            return 'PUT', min(conf, 90)
        
        # CALL forte: 3 velas altas + tendência alta + vela forte
        if calls_5 >= 3 and calls_3 == 3 and atual > sma20 and vela['close'] > vela['open']:
            conf = 72 + forca * 0.1
            return 'CALL', min(conf, 85)
        
        # PUT forte: 3 velas baixas + tendência baixa + vela forte
        if puts_5 >= 3 and puts_3 == 3 and atual < sma20 and vela['close'] < vela['open']:
            conf = 72 + forca * 0.1
            return 'PUT', min(conf, 85)
        
        return None, 0

class Bot:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.velas_m5 = {nome: deque(maxlen=50) for nome in ATIVOS_OTC}  # Multi-timeframe
        self.estrategia = QuantumPro()
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
        for nome, ativo_id in ATIVOS_OTC.items():
            try:
                if not api.check_connect():
                    api = await self.reconectar_se_necessario()
                    if not api:
                        break
                
                # 📊 M1 (principal)
                c = api.get_candles(ativo_id, TIMEFRAME, 60, time.time())
                if c and len(c) > 0:
                    self.velas[nome].clear()
                    for x in c[-60:]:
                        if isinstance(x, dict):
                            self.velas[nome].append({
                                'time': datetime.fromtimestamp(x.get('from',0), FUSO_BR),
                                'open': float(x['open']), 'high': float(x['max']),
                                'low': float(x['min']), 'close': float(x['close']),
                                'volume': int(x.get('volume',0))
                            })
                
                # 📊 M5 (confirmação)
                c5 = api.get_candles(ativo_id, 300, 30, time.time())
                if c5 and len(c5) > 0:
                    self.velas_m5[nome].clear()
                    for x in c5[-30:]:
                        if isinstance(x, dict):
                            self.velas_m5[nome].append({
                                'time': datetime.fromtimestamp(x.get('from',0), FUSO_BR),
                                'open': float(x['open']), 'high': float(x['max']),
                                'low': float(x['min']), 'close': float(x['close']),
                                'volume': int(x.get('volume',0))
                            })
            except Exception as e:
                print(f"Erro {nome}: {e}")

    def confirmar_m5(self, par, direcao):
        """Confirma se o M5 está alinhado com o sinal do M1"""
        velas_m5 = self.velas_m5[par]
        if len(velas_m5) < 3:
            return True  # Sem dados suficientes, aceita
        
        # Últimas 3 velas M5
        ultimas = list(velas_m5)[-3:]
        calls = sum(1 for v in ultimas if v['close'] > v['open'])
        puts = 3 - calls
        
        if direcao == 'CALL':
            return calls >= 2  # Maioria alta no M5
        else:
            return puts >= 2  # Maioria baixa no M5

    def buscar_sinal(self):
        melhor = None
        melhor_score = 0
        
        for par, velas in self.velas.items():
            if len(velas) < 30:
                continue
            
            direcao, conf = self.estrategia.analisar(velas)
            if direcao and conf >= CONFIANCA_MINIMA:
                # 🎯 CONFIRMAÇÃO MULTI-TIMEFRAME
                if not self.confirmar_m5(par, direcao):
                    continue  # M5 não confirma, pula
                
                if conf > melhor_score:
                    melhor_score = conf
                    melhor = {'ativo': par, 'direcao': direcao, 'confianca': conf}
        
        return melhor

    def calcular_horario_entrada(self):
        agora = datetime.now(FUSO_BR)
        return agora.replace(second=0, microsecond=0) + timedelta(minutes=1)

    def formatar_sinal(self, sinal, horario):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        conf = sinal['confianca']
        hora = horario.strftime('%H:%M')
        
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM PRO M1 ✅
⏲ EXPIRAÇÃO: M1

👉🏼 HORARIO: {hora}

🏳ATIVO: {ativo}-OTC {direcao}

📊 Confiança: {conf:.0f}%
🧠 Estratégia: QUANTUM PRO
🎯 Multi-Timeframe ✅

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
📊 {ativo}-OTC | {direcao} {'🟢' if direcao=='CALL' else '🔴'}
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
        print("⚛️ Bot QUANTUM PRO M1 iniciando...")
        self.tg.send(f"🔥 *QUANTUM PRO M1 ATIVADO*\n📊 {len(ATIVOS_OTC)} Pares OTC\n⏱️ M1 + M5\n🎯 Multi-Timeframe\n📊 Volatilidade Adaptativa\n🛡️ Anti-Pavio\n⏰ Bloqueio de Horários\n🔄 Gale 1.5x")
        
        if not self.conectar_iq():
            print("❌ Falha conexão!")
            return
        
        await self.atualizar_velas()
        
        while True:
            try:
                self.verificar_zeramento_diario()
                
                agora = datetime.now(FUSO_BR)
                
                # ⏰ VERIFICA HORÁRIO
                if not horario_bom():
                    if agora.second == 0:
                        print(f"⏰ Horário ruim ({agora.strftime('%H:%M')}). Aguardando...")
                    await asyncio.sleep(30)
                    continue
                
                if agora.second == 0:
                    total_velas = sum(len(v) for v in self.velas.values())
                    print(f"💓 {agora.strftime('%H:%M:%S')} | Velas M1: {total_velas} | Sinais: {self.sinais}")
                    
                    if total_velas == 0:
                        print("🔄 Sem velas! Reconectando...")
                        self.iq_api = None
                
                if agora.second in [0, 15, 30, 45]:
                    await self.atualizar_velas()
                
                horario_entrada = self.calcular_horario_entrada()
                horario_envio = horario_entrada - timedelta(seconds=ANTECEDENCIA)
                tempo_ate_envio = (horario_envio - agora).total_seconds()
                
                if 0 <= tempo_ate_envio <= 15:
                    sinal = self.buscar_sinal()
                    
                    if sinal and time.time() - self.ult_sinal > INTERVALO_MINIMO:
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
    asyncio.run(Bot().executar())
