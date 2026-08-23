#!/usr/bin/env python3
"""
⚛️ ICT SILVER BULLET - FOREX REAL
📊 Estratégia: Liquidez + Pullback + Rejeição
📡 Fonte de dados: Yahoo Finance (grátis, sem login)
🎯 6 Pares Forex
🔄 Gale 1 normal
🕐 Horário: 06h-22h (Brasil)
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path
import yfinance as yf

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# Configurações
INTERVALO_MINIMO = 600       # 10 min entre sinais
USAR_GALE = True
ANTECEDENCIA = 30
SCORE_MINIMO = 70

def banner():
    print("⚛️ ICT SILVER BULLET - Forex Real (06h-22h)")

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

# 6 Pares Forex
ATIVOS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "USDCAD=X",
    "EURJPY": "EURJPY=X"
}

class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c
    def send(self, txt):
        try: requests.post(f"{self.url}/sendMessage", json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"}, timeout=10)
        except: pass

class ICTSilverBullet:
    def __init__(self):
        # Horário expandido: 06h - 22h
        self.horario_inicio = 6
        self.horario_fim = 22
    
    def horario_ok(self):
        agora = datetime.now(FUSO_BR)
        hora = agora.hour
        dia = agora.weekday()
        
        # Apenas segunda a sexta
        if dia >= 5:
            return False
        
        # Horário expandido
        if self.horario_inicio <= hora < self.horario_fim:
            return True
        
        return False
    
    def analisar(self, velas):
        if len(velas) < 25:
            return None, 0, {}
        
        if not self.horario_ok():
            return None, 0, {}
        
        precos = [v['close'] for v in velas]
        ema20 = np.mean(precos[-20:])
        atual = precos[-1]
        
        max_5 = max(v['high'] for v in velas[-5:])
        min_5 = min(v['low'] for v in velas[-5:])
        
        vela = velas[-1]
        corpo = abs(vela['close'] - vela['open'])
        pavio_sup = vela['high'] - max(vela['close'], vela['open'])
        pavio_inf = min(vela['close'], vela['open']) - vela['low']
        
        detalhes = {}
        
        # CALL
        if atual > ema20 and vela['low'] <= min_5 * 1.001:
            if pavio_inf >= corpo * 1.5:
                detalhes['setup'] = 'SILVER BULLET CALL'
                detalhes['tendencia'] = 'ALTA'
                detalhes['zona'] = 'SUPORTE'
                detalhes['rejeicao'] = 'PAVIO INFERIOR'
                return 'CALL', 80, detalhes
        
        # PUT
        if atual < ema20 and vela['high'] >= max_5 * 0.999:
            if pavio_sup >= corpo * 1.5:
                detalhes['setup'] = 'SILVER BULLET PUT'
                detalhes['tendencia'] = 'BAIXA'
                detalhes['zona'] = 'RESISTÊNCIA'
                detalhes['rejeicao'] = 'PAVIO SUPERIOR'
                return 'PUT', 80, detalhes
        
        return None, 0, detalhes

class BotICT:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS}
        self.estrategia = ICTSilverBullet()
        self.placar = {'w': 0, 'g1': 0, 'l': 0}
        self.ult_sinal = 0
        self.ultimo_dia = datetime.now(FUSO_BR).day
    
    def atualizar_velas(self):
        """Busca velas do Yahoo Finance (M5)"""
        for nome, symbol in ATIVOS.items():
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="1d", interval="5m")
                
                if df is not None and len(df) > 0:
                    self.velas[nome].clear()
                    for index, row in df.iterrows():
                        self.velas[nome].append({
                            'time': index.to_pydatetime().astimezone(FUSO_BR),
                            'open': float(row['Open']),
                            'high': float(row['High']),
                            'low': float(row['Low']),
                            'close': float(row['Close']),
                            'volume': int(row['Volume']) if 'Volume' in row else 0
                        })
                    print(f"✅ {nome}: {len(df)} velas carregadas")
                else:
                    print(f"⚠️ {nome}: sem dados")
            except Exception as e:
                print(f"❌ Erro {nome}: {e}")
        
        print()
    
    def buscar_sinal(self):
        melhor_sinal = None
        melhor_score = 0
        
        for par, velas in self.velas.items():
            if len(velas) < 25:
                continue
            direcao, confianca, detalhes = self.estrategia.analisar(velas)
            if direcao and confianca >= SCORE_MINIMO:
                if confianca > melhor_score:
                    melhor_score = confianca
                    melhor_sinal = {
                        'ativo': par,
                        'direcao': direcao,
                        'confianca': confianca,
                        'detalhes': detalhes
                    }
        
        return melhor_sinal
    
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
        detalhes = sinal.get('detalhes', {})
        hora = horario.strftime('%H:%M')
        detalhes_txt = "\n".join([f"• {k}: {v}" for k, v in detalhes.items()])
        
        return f"""🚨SINAL AO VIVO🚨

✳️ ICT SILVER BULLET ✅
⏲ EXPIRAÇÃO: M5

👉🏼 HORARIO: {hora}

🏳ATIVO: {ativo} {direcao}

📊 Confiança: {conf:.0f}%

📈 Setup:
{detalhes_txt}

🍀🍀BOA SORTE 🍀 🍀"""
    
    async def monitorar_resultado(self, sinal, horario_entrada):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        
        agora = datetime.now(FUSO_BR)
        espera = (horario_entrada + timedelta(minutes=5) - agora).total_seconds()
        if espera > 0:
            await asyncio.sleep(espera)
        await asyncio.sleep(30)
        
        self.atualizar_velas()
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
                proxima_vela = horario_entrada + timedelta(minutes=5)
                agora = datetime.now(FUSO_BR)
                espera = (proxima_vela + timedelta(minutes=5) - agora).total_seconds()
                if espera > 0:
                    await asyncio.sleep(espera)
                await asyncio.sleep(30)
                self.atualizar_velas()
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
        print("⚛️ Bot ICT Silver Bullet iniciando...")
        print("📡 Fonte: Yahoo Finance")
        print(f"📊 Pares: {', '.join(ATIVOS.keys())}")
        print("🕐 Horário: 06h - 22h")
        
        self.tg.send("""🔥 *ICT SILVER BULLET ATIVADO*

📊 Estratégia: Liquidez + Pullback + Rejeição
📡 Fonte: Yahoo Finance (sem login)
🎯 6 Pares Forex
🔄 Gale 1
🕐 Horário: 06h - 22h (Brasil)""")
        
        while True:
            try:
                self.verificar_zeramento_diario()
                self.atualizar_velas()
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
                
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                print("🛑 Encerrado.")
                break
            except Exception as e:
                print(f"Erro: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    bot = BotICT()
    asyncio.run(bot.executar())
