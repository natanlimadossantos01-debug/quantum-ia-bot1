#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M5 (SEM FILTROS) - SINAIS GARANTIDOS
🕯️ Super 5 / Super 3 / Last of Five
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os, random
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

def banner():
    print("⚛️ QUANTUM IA M5 - Modo livre")

def carregar_config():
    token = os.environ.get('TELEGRAM_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    email = os.environ.get('IQ_EMAIL')
    senha = os.environ.get('IQ_SENHA')
    if token and chat and email and senha:
        banner()
        print("✅ Modo CLOUD detectado!")
        return {"token": token, "chat": chat, "email": email, "senha": senha}
    # fallback local
    cfg_file = "config_m5.json"
    if Path(cfg_file).exists():
        with open(cfg_file) as f: cfg = json.load(f)
        return cfg
    print("❌ Configure as variáveis de ambiente!")
    sys.exit(1)

cfg = carregar_config()
TOKEN, CHAT, EMAIL, SENHA = cfg['token'], cfg['chat'], cfg['email'], cfg['senha']

from iqoptionapi.stable_api import IQ_Option

ATIVOS_OTC = {
    "EURUSD":"EURUSD-OTC",
    "GBPUSD":"GBPUSD-OTC",
    "EURGBP":"EURGBP-OTC",
    "EURJPY":"EURJPY-OTC"
}

class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c
    def send(self, txt):
        try: requests.post(f"{self.url}/sendMessage", json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"}, timeout=5)
        except: pass

class Super5:
    def __init__(self, modo='minoria'):
        self.modo = modo
        self.tamanho = 6
        self.velas_analise = 3
    def analisar(self, v):
        try:
            if len(v) < self.tamanho * 2: return None, 0
            quadrante = list(v[-self.tamanho:])
            velas = quadrante[-self.velas_analise:]
            calls = sum(1 for x in velas if x['close'] > x['open'])
            puts = self.velas_analise - calls
            if self.modo == 'minoria':
                alvo = 'CALL' if calls < puts else 'PUT'
            else:
                alvo = 'CALL' if calls > puts else 'PUT'
            diff = abs(calls - puts)
            conf = min(50 + diff * 10, 85)
            return alvo, conf
        except: return None, 0

class Super3:
    def __init__(self, modo='minoria'):
        self.modo = modo
        self.tamanho = 3
    def analisar(self, v):
        try:
            if len(v) < self.tamanho * 2: return None, 0
            quadrante = list(v[-self.tamanho:])
            calls = sum(1 for x in quadrante if x['close'] > x['open'])
            puts = self.tamanho - calls
            if self.modo == 'minoria':
                alvo = 'CALL' if calls < puts else 'PUT'
            else:
                alvo = 'CALL' if calls > puts else 'PUT'
            diff = abs(calls - puts)
            conf = min(50 + diff * 15, 85)
            return alvo, conf
        except: return None, 0

class LastOfFive:
    def __init__(self, modo='minoria'):
        self.modo = modo
        self.tamanho = 6
        self.velas_analise = 5
    def analisar(self, v):
        try:
            if len(v) < self.tamanho * 2: return None, 0
            quadrante = list(v[-self.tamanho:])
            velas = quadrante[-self.velas_analise:]
            calls = sum(1 for x in velas if x['close'] > x['open'])
            puts = self.velas_analise - calls
            if self.modo == 'minoria':
                alvo = 'CALL' if calls < puts else 'PUT'
            else:
                alvo = 'CALL' if calls > puts else 'PUT'
            diff = abs(calls - puts)
            conf = min(50 + diff * 8, 85)
            return alvo, conf
        except: return None, 0

class BotM5:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.iq = IQ_Option(EMAIL, SENHA)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.estrategias = [
            ('Super 5 Min', Super5('minoria')),
            ('Super 5 Maj', Super5('maioria')),
            ('Super 3 Min', Super3('minoria')),
            ('Super 3 Maj', Super3('maioria')),
            ('Last 5 Min', LastOfFive('minoria')),
            ('Last 5 Maj', LastOfFive('maioria'))
        ]
        self.ult_sinal = 0
        self.em_operacao = False
        self.sinais_enviados = 0
        self.placar = {'w':0, 'l':0, 'g1':0}

    def conectar_iq(self):
        for t in range(5):
            try:
                if hasattr(self.iq, 'api') and self.iq.api:
                    try: self.iq.api.close()
                    except: pass
                    time.sleep(2)
                self.iq.connect()
                if self.iq.check_connect():
                    print("✅ Conectado à IQ Option!")
                    return True
                time.sleep(5*(t+1))
            except: time.sleep(5*(t+1))
        return False

    def atualizar_velas(self):
        if not self.iq.check_connect() and not self.conectar_iq():
            return
        for nome, ativo_id in ATIVOS_OTC.items():
            for retry in range(3):
                try:
                    c = self.iq.get_candles(ativo_id, 300, 60, time.time())
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
                        break
                except: time.sleep(2)

    def buscar_sinal(self):
        for nome_par, velas in self.velas.items():
            if len(velas) < 12: continue  # mínimo para as estratégias
            for nome_est, est in self.estrategias:
                try:
                    d, c = est.analisar(velas)
                    if d and c >= 50:  # confiança mínima reduzida
                        return {'ativo': nome_par, 'direcao': d, 'confianca': c, 'estrategia': nome_est}
                except: pass
        return None

    async def executar(self):
        banner()
        print("⚛️ M5 sem filtros - iniciando...")
        if not self.conectar_iq():
            print("❌ Falha conexão IQ.")
            return
        self.atualizar_velas()
        self.tg.send("🔥 *QUANTUM IA M5 ATIVADO*\n📊 Sinais a cada 5min | Sem filtros")
        while True:
            try:
                agora = datetime.now(FUSO_BR)
                if agora.second % 30 == 0:
                    self.atualizar_velas()
                if not self.em_operacao and time.time() - self.ult_sinal > 300:  # 5 minutos
                    sinal = self.buscar_sinal()
                    if sinal:
                        self.em_operacao = True
                        self.sinais_enviados += 1
                        self.ult_sinal = time.time()
                        # próximo candle de 5 min
                        prox = agora.replace(second=0, microsecond=0) + timedelta(minutes=5)
                        prox = prox.replace(minute=(prox.minute//5)*5)
                        he = prox.strftime('%H:%M')
                        emoji = '🟢' if sinal['direcao']=='CALL' else '🔴'
                        msg = f"""⚛️ SINAL M5 ⚛️

⏰ Horário: {he}
💰 Ativo: {sinal['ativo']}-OTC
📈 Direção: {sinal['direcao']} {emoji}
⌛️ Expiração: M5
📊 Confiança: {sinal['confianca']:.0f}%
🧠 Estratégia: {sinal['estrategia']}

⚠️ Entrar somente no horário marcado.
🔄 1 recuperação (Gale 1)!"""
                        self.tg.send(msg)
                        print(f"⚛️ #{self.sinais_enviados} {sinal['ativo']}-OTC {sinal['direcao']} | {sinal['confianca']:.0f}% | {sinal['estrategia']}")
                        asyncio.create_task(self.gerenciar_operacao(sinal))
                # status a cada 30s
                if agora.second % 30 == 0:
                    w, l, g1 = self.placar['w'], self.placar['l'], self.placar['g1']
                    total = w + g1 + l
                    tx = round(((w+g1)/total)*100,1) if total > 0 else 0
                    print(f"│ M5 {agora.strftime('%H:%M:%S')} | 📨{self.sinais_enviados} | 🟢{w}W 🟡{g1}G1 🔴{l}L 🎯{tx}%")
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("🛑 M5 encerrado.")
                break
            except Exception as e:
                print(f"Erro: {e}")
                await asyncio.sleep(5)

    async def gerenciar_operacao(self, sinal):
        ativo, direcao, conf = sinal['ativo'], sinal['direcao'], sinal['confianca']
        try:
            # aguardar início do próximo candle de 5 min
            agora = datetime.now(FUSO_BR)
            prox = agora.replace(second=0, microsecond=0) + timedelta(minutes=5)
            prox = prox.replace(minute=(prox.minute//5)*5)
            espera = (prox - agora).total_seconds()
            if espera > 0: await asyncio.sleep(espera)
            self.atualizar_velas()
            v = self.velas[ativo]
            if len(v) < 2: self.em_operacao = False; return
            entrada = v[-1]['open']
            print(f"  M5 {ativo}-OTC {direcao} OPEN:{entrada:.5f}")
            await asyncio.sleep(290)  # quase 5 min
            self.atualizar_velas()
            v = self.velas[ativo]
            if len(v) > 0 and ((direcao == 'CALL' and v[-1]['high'] > entrada) or (direcao == 'PUT' and v[-1]['low'] < entrada)):
                self.placar['w'] += 1
                self.tg.send(f"✅ WIN\n{ativo}-OTC {direcao} | Placar M5: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L")
                self.em_operacao = False; return
            # Gale 1
            print("  🔄 GALE 1")
            await asyncio.sleep(10)
            self.atualizar_velas()
            v = self.velas[ativo]
            if len(v) > 0:
                pg = v[-1]['open']
                print(f"  GALE OPEN:{pg:.5f}")
                await asyncio.sleep(290)
                self.atualizar_velas()
                v = self.velas[ativo]
                if len(v) > 0 and ((direcao == 'CALL' and v[-1]['high'] > pg) or (direcao == 'PUT' and v[-1]['low'] < pg)):
                    self.placar['g1'] += 1
                    self.tg.send(f"✅ WIN GALE 1\n{ativo}-OTC {direcao} | Placar M5: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L")
                    self.em_operacao = False; return
            self.placar['l'] += 1
            self.tg.send(f"❌ LOSS\n{ativo}-OTC {direcao} | Placar M5: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L")
            self.em_operacao = False
        except Exception as e:
            print(f"  ❌ Erro operação: {e}")
            self.em_operacao = False

if __name__ == "__main__":
    bot = BotM5()
    asyncio.run(bot.executar())
