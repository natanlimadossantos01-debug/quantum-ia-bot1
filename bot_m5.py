#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M1 - ESTRATÉGIAS QUADRANTES + BACKTEST + IA
📊 12 Pares OTC
⏱️ M1
🎯 MHI, 2-3, 3 Vizinhos, VITUXO
🧠 Backtest robusto de 30 velas
🔍 IA escolhe o melhor par por estratégia
🔄 Gale 1.5x
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

INTERVALO_MINIMO = 300
USAR_GALE = True
MULTIPLICADOR_GALE = 1.5
ANTECEDENCIA = 10
TIMEFRAME = 60
CONFIANCA_MINIMA = 65

def banner():
    print("⚛️ QUANTUM IA M1 - Quadrantes + IA")

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
# 🕯️ 4 ESTRATÉGIAS DE QUADRANTE
# ═══════════════════════════════════════════

class MHI:
    """MHI: minoria das 3 últimas velas"""
    def analisar(self, velas):
        if len(velas) < 10:
            return None, 0
        
        ultimas = list(velas)[-3:]
        calls = sum(1 for v in ultimas if v['close'] > v['open'])
        puts = 3 - calls
        
        if calls == 1:
            return 'CALL', 72
        if puts == 1:
            return 'PUT', 72
        return None, 0

class Padrao23:
    """2-3: vela -2 e -3 definem direção"""
    def analisar(self, velas):
        if len(velas) < 5:
            return None, 0
        
        vela_2 = velas[-3]
        vela_3 = velas[-4]
        
        # Ambas de alta
        if vela_2['close'] > vela_2['open'] and vela_3['close'] > vela_3['open']:
            return 'CALL', 70
        # Ambas de baixa
        if vela_2['close'] < vela_2['open'] and vela_3['close'] < vela_3['open']:
            return 'PUT', 70
        return None, 0

class TresVizinhos:
    """3 Vizinhos: cor da vela -2"""
    def analisar(self, velas):
        if len(velas) < 5:
            return None, 0
        
        vela = velas[-2]
        if vela['close'] > vela['open']:
            return 'CALL', 70
        if vela['close'] < vela['open']:
            return 'PUT', 70
        return None, 0

class Vituxo:
    """VITUXO 2.0: maioria das 3 primeiras velas do quadrante anterior"""
    def analisar(self, velas):
        if len(velas) < 8:
            return None, 0
        
        velas_ant = list(velas)[-8:-5]
        calls = sum(1 for v in velas_ant if v['close'] > v['open'])
        puts = 3 - calls
        
        if calls > puts:
            return 'CALL', 70
        if puts > calls:
            return 'PUT', 70
        return None, 0

# ═══════════════════════════════════════════
# 🧪 BACKTEST ROBUSTO
# ═══════════════════════════════════════════
class Backtest:
    def __init__(self):
        self.velas_teste = 30  # Testa nas últimas 30 velas
    
    def rodar(self, velas, estrategia):
        """
        Roda backtest da estratégia nas últimas N velas
        Retorna: (wins, losses, taxa_acerto)
        """
        wins = 0
        losses = 0
        
        if len(velas) < self.velas_teste + 5:
            return 0, 0, 0
        
        # Testa nas últimas N velas
        for i in range(len(velas) - self.velas_teste, len(velas) - 1):
            velas_parciais = list(velas)[:i+1]
            
            if len(velas_parciais) < 5:
                continue
            
            # Sinal da estratégia
            resultado = estrategia.analisar(velas_parciais)
            if not resultado:
                continue
            
            direcao, _ = resultado
            vela_entrada = velas[i+1]
            
            # Verifica se acertou
            if direcao == 'CALL':
                if vela_entrada['close'] > vela_entrada['open']:
                    wins += 1
                else:
                    losses += 1
            else:
                if vela_entrada['close'] < vela_entrada['open']:
                    wins += 1
                else:
                    losses += 1
        
        total = wins + losses
        taxa = (wins / total * 100) if total > 0 else 0
        
        return wins, losses, taxa

# ═══════════════════════════════════════════
# 🧠 IA - ESCOLHE MELHOR PAR POR ESTRATÉGIA
# ═══════════════════════════════════════════
class IA:
    def __init__(self):
        self.melhores_pares = {}  # {estrategia: par}
        self.ultima_avaliacao = 0
        self.intervalo_avaliacao = 600  # 10 min
    
    def avaliar(self, velas_dict, estrategias, backtest):
        """
        Avalia todas as combinações e escolhe o melhor par para cada estratégia
        """
        agora = time.time()
        if agora - self.ultima_avaliacao < self.intervalo_avaliacao:
            return self.melhores_pares
        
        self.ultima_avaliacao = agora
        
        print("\n🧠 IA: Avaliando melhor par por estratégia...")
        
        for nome_est, est in estrategias:
            melhor_par = None
            melhor_taxa = 0
            
            for par, velas in velas_dict.items():
                if len(velas) < 40:
                    continue
                
                wins, losses, taxa = backtest.rodar(velas, est)
                
                if taxa > melhor_taxa and (wins + losses) >= 5:
                    melhor_taxa = taxa
                    melhor_par = par
            
            if melhor_par:
                self.melhores_pares[nome_est] = {'par': melhor_par, 'taxa': melhor_taxa}
                print(f"   ✅ {nome_est}: {melhor_par} ({melhor_taxa:.0f}%)")
            else:
                print(f"   ❌ {nome_est}: sem dados suficientes")
        
        return self.melhores_pares
    
    def get_par(self, estrategia):
        info = self.melhores_pares.get(estrategia)
        if info:
            return info['par'], info['taxa']
        return None, 0

# ═══════════════════════════════════════════
# BOT
# ═══════════════════════════════════════════
class Bot:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        
        # 4 Estratégias
        self.estrategias = [
            ('📊 MHI', MHI()),
            ('📊 2-3', Padrao23()),
            ('📊 3 Vizinhos', TresVizinhos()),
            ('📊 VITUXO', Vituxo())
        ]
        
        self.backtest = Backtest()
        self.ia = IA()
        
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
        """
        IA escolhe o melhor par para cada estratégia
        Só envia sinal se a estratégia estiver no seu melhor par
        """
        # IA avalia melhor par por estratégia
        self.ia.avaliar(self.velas, self.estrategias, self.backtest)
        
        melhor_sinal = None
        melhor_score = 0
        
        for nome_est, est in self.estrategias:
            # IA diz qual o melhor par para essa estratégia
            melhor_par, taxa_bt = self.ia.get_par(nome_est)
            
            if not melhor_par or taxa_bt < 65:
                continue  # Pula se taxa do backtest for baixa
            
            if melhor_par not in self.velas:
                continue
            
            velas = self.velas[melhor_par]
            if len(velas) < 30:
                continue
            
            # Verifica se a estratégia dá sinal AGORA nesse par
            resultado = est.analisar(velas)
            if not resultado:
                continue
            
            direcao, conf = resultado
            
            if conf >= CONFIANCA_MINIMA:
                # Score baseado na taxa do backtest
                score = taxa_bt + conf * 0.3
                
                if score > melhor_score:
                    melhor_score = score
                    melhor_sinal = {
                        'ativo': melhor_par,
                        'direcao': direcao,
                        'confianca': conf,
                        'estrategia': nome_est,
                        'taxa_bt': taxa_bt
                    }
        
        return melhor_sinal

    def calcular_horario_entrada(self):
        agora = datetime.now(FUSO_BR)
        return agora.replace(second=0, microsecond=0) + timedelta(minutes=1)

    def formatar_sinal(self, sinal, horario):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        conf = sinal['confianca']
        est = sinal['estrategia']
        taxa_bt = sinal.get('taxa_bt', 0)
        hora = horario.strftime('%H:%M')
        
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM IA M1 ✅
⏲ EXPIRAÇÃO: M1

👉🏼 HORARIO: {hora}

🏳ATIVO: {ativo}-OTC {direcao}

📊 Confiança: {conf:.0f}%
🧠 Estratégia: {est}
🔬 Backtest: {taxa_bt:.0f}% ✅

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
        print("⚛️ Bot QUANTUM IA M1 iniciando...")
        self.tg.send(f"""🔥 *QUANTUM IA M1 ATIVADO*
📊 {len(ATIVOS_OTC)} Pares OTC
⏱️ M1
🧠 4 Estratégias: MHI, 2-3, 3 Vizinhos, VITUXO
🔬 Backtest robusto (30 velas)
🤖 IA escolhe o melhor par por estratégia
🔄 Gale 1.5x""")
        
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
                    print(f"💓 {agora.strftime('%H:%M:%S')} | Velas: {total_velas} | Sinais: {self.sinais}")
                    
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
                        print(f"✅ Sinal: {sinal['ativo']} | {sinal['estrategia']} | BT: {sinal['taxa_bt']:.0f}%")
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
