#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M1 - CATÁLOGO INTELIGENTE
🧠 Testa 6 estratégias e usa a melhor automaticamente
📊 12 Pares OTC
⏱️ Timeframe: M1
🔄 Gale 1
📈 Reavaliação a cada 10 sinais
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

INTERVALO_MINIMO = 300
USAR_GALE = True
ANTECEDENCIA = 30
TIMEFRAME = 60
CONFIANCA_MINIMA = 50

def banner():
    print("⚛️ QUANTUM IA M1 - Catálogo Inteligente")

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
# 6 ESTRATÉGIAS DIFERENTES
# ═══════════════════════════════════════════

class TopVIP:
    """3 velas de alta → CALL | 3 velas de baixa → PUT"""
    def analisar(self, velas):
        if len(velas) < 4:
            return None, 0
        ultimas = list(velas)[-3:]
        calls = sum(1 for v in ultimas if v['close'] > v['open'])
        puts = 3 - calls
        if calls == 3:
            return 'CALL', 70
        if puts == 3:
            return 'PUT', 70
        return None, 0

class MHI:
    """Minoria das 3 velas"""
    def analisar(self, velas):
        if len(velas) < 4:
            return None, 0
        ultimas = list(velas)[-3:]
        calls = sum(1 for v in ultimas if v['close'] > v['open'])
        puts = 3 - calls
        if calls == 1:  # Minoria alta
            return 'CALL', 70
        if puts == 1:  # Minoria baixa
            return 'PUT', 70
        return None, 0

class Reversao:
    """3 velas de alta → PUT | 3 velas de baixa → CALL"""
    def analisar(self, velas):
        if len(velas) < 4:
            return None, 0
        ultimas = list(velas)[-3:]
        calls = sum(1 for v in ultimas if v['close'] > v['open'])
        puts = 3 - calls
        if calls == 3:
            return 'PUT', 65
        if puts == 3:
            return 'CALL', 65
        return None, 0

class ForcaExtrema:
    """Vela com corpo > 70% do range"""
    def analisar(self, velas):
        if len(velas) < 2:
            return None, 0
        vela = velas[-1]
        corpo = abs(vela['close'] - vela['open'])
        range_total = vela['high'] - vela['low']
        if range_total == 0:
            return None, 0
        forca = (corpo / range_total) * 100
        if forca > 70:
            if vela['close'] > vela['open']:
                return 'CALL', 70
            else:
                return 'PUT', 70
        return None, 0

class Sequencia:
    """4 velas mesma direção → reversão"""
    def analisar(self, velas):
        if len(velas) < 5:
            return None, 0
        ultimas = list(velas)[-4:]
        calls = sum(1 for v in ultimas if v['close'] > v['open'])
        puts = 4 - calls
        if calls == 4:
            return 'PUT', 65
        if puts == 4:
            return 'CALL', 65
        return None, 0

class VelaConfirmacao:
    """2 velas mesma direção + última forte"""
    def analisar(self, velas):
        if len(velas) < 3:
            return None, 0
        v1 = velas[-2]
        v2 = velas[-1]
        if v1['close'] > v1['open'] and v2['close'] > v2['open']:
            corpo = abs(v2['close'] - v2['open'])
            range_total = v2['high'] - v2['low']
            if range_total > 0 and (corpo / range_total) > 0.5:
                return 'CALL', 65
        if v1['close'] < v1['open'] and v2['close'] < v2['open']:
            corpo = abs(v2['close'] - v2['open'])
            range_total = v2['high'] - v2['low']
            if range_total > 0 and (corpo / range_total) > 0.5:
                return 'PUT', 65
        return None, 0

# ═══════════════════════════════════════════
# CATÁLOGO INTELIGENTE
# ═══════════════════════════════════════════
class Catalogo:
    def __init__(self):
        self.estrategias = {
            'TOP VIP': {'wins': 0, 'losses': 0, 'strategy': TopVIP()},
            'MHI': {'wins': 0, 'losses': 0, 'strategy': MHI()},
            'Reversão': {'wins': 0, 'losses': 0, 'strategy': Reversao()},
            'Força Extrema': {'wins': 0, 'losses': 0, 'strategy': ForcaExtrema()},
            'Sequência': {'wins': 0, 'losses': 0, 'strategy': Sequencia()},
            'Vela Confirmação': {'wins': 0, 'losses': 0, 'strategy': VelaConfirmacao()}
        }
        self.estrategia_atual = 'TOP VIP'
        self.sinais_desde_troca = 0
    
    def registrar(self, nome, ganhou):
        if nome in self.estrategias:
            if ganhou:
                self.estrategias[nome]['wins'] += 1
            else:
                self.estrategias[nome]['losses'] += 1
    
    def get_taxa(self, nome):
        if nome in self.estrategias:
            total = self.estrategias[nome]['wins'] + self.estrategias[nome]['losses']
            if total > 0:
                return (self.estrategias[nome]['wins'] / total) * 100
        return 0
    
    def escolher_melhor(self):
        melhor_nome = None
        melhor_taxa = 0
        for nome, dados in self.estrategias.items():
            total = dados['wins'] + dados['losses']
            if total >= 3:  # Mínimo 3 operações
                taxa = (dados['wins'] / total) * 100
                if taxa > melhor_taxa:
                    melhor_taxa = taxa
                    melhor_nome = nome
        if melhor_nome:
            self.estrategia_atual = melhor_nome
        return self.estrategia_atual
    
    def relatorio(self):
        msg = "📊 *CATÁLOGO INTELIGENTE*\n\n"
        for nome, dados in self.estrategias.items():
            total = dados['wins'] + dados['losses']
            if total > 0:
                taxa = (dados['wins'] / total) * 100
                msg += f"• {nome}: {taxa:.0f}% ({dados['wins']}W/{dados['losses']}L)\n"
        msg += f"\n🎯 *Atual:* {self.estrategia_atual}"
        return msg

class Bot:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.catalogo = Catalogo()
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
            except Exception as e:
                print(f"Erro {nome}: {e}")

    def buscar_sinal(self):
        """Usa apenas a estratégia atual do catálogo"""
        melhor = None
        melhor_score = 0
        
        estrategia = self.catalogo.estrategias[self.catalogo.estrategia_atual]['strategy']
        
        for par, velas in self.velas.items():
            if len(velas) < 4:
                continue
            direcao, conf = estrategia.analisar(velas)
            if direcao and conf > melhor_score:
                melhor_score = conf
                melhor = {'ativo': par, 'direcao': direcao, 'confianca': conf, 'estrategia': self.catalogo.estrategia_atual}
        
        return melhor

    def calcular_horario_entrada(self):
        agora = datetime.now(FUSO_BR)
        return agora.replace(second=0, microsecond=0) + timedelta(minutes=1)

    def formatar_sinal(self, sinal, horario):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        conf = sinal['confianca']
        est = sinal['estrategia']
        hora = horario.strftime('%H:%M')
        
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM IA M1 ✅
⏲ EXPIRAÇÃO: M1

👉🏼 HORARIO: {hora}

🏳ATIVO: {ativo}-OTC {direcao}

📊 Confiança: {conf:.0f}%
🧠 Estratégia: {est}

🍀🍀BOA SORTE 🍀 🍀"""

    async def monitorar_resultado(self, sinal, horario_entrada):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        estrategia_nome = sinal['estrategia']
        
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
        
        # Registra no catálogo
        self.catalogo.registrar(estrategia_nome, ganhou)
        
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
        
        # Reavalia catálogo a cada 5 sinais
        if self.sinais % 5 == 0:
            self.catalogo.escolher_melhor()
        
        total = self.placar['w'] + self.placar['g1'] + self.placar['l']
        tx = round(((self.placar['w'] + self.placar['g1']) / total) * 100, 1) if total > 0 else 0.0
        msg = f"""{resultado}
📊 {ativo}-OTC | {direcao} {'🟢' if direcao=='CALL' else '🔴'}
📊 Placar: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L
🎯 Assertividade: {tx}%"""
        self.tg.send(msg)
        
        # Envia relatório a cada 10 sinais
        if self.sinais % 10 == 0:
            self.tg.send(self.catalogo.relatorio())

    def verificar_zeramento_diario(self):
        agora = datetime.now(FUSO_BR)
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'g1': 0, 'l': 0}
            self.tg.send("🔄 *PLACAR ZERADO*")
            print("🔄 Placar zerado.")

    async def executar(self):
        banner()
        print("⚛️ Bot Catálogo Inteligente iniciando...")
        self.tg.send(f"🔥 *QUANTUM IA CATÁLOGO*\n🧠 6 Estratégias\n📊 {len(ATIVOS_OTC)} Pares OTC\n⏱️ M1\n🔄 Reavaliação automática\n📈 Usa a melhor estratégia")
        
        if not self.conectar_iq():
            print("❌ Falha conexão!")
            return
        
        await self.atualizar_velas()
        
        while True:
            try:
                self.verificar_zeramento_diario()
                
                agora = datetime.now(FUSO_BR)
                if agora.second == 0:
                    total_velas = sum(len(v) for v in self.velas.values())
                    print(f"💓 {agora.strftime('%H:%M:%S')} | Velas: {total_velas} | Sinais: {self.sinais} | 🧠 {self.catalogo.estrategia_atual}")
                    
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
