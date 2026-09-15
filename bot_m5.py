#!/usr/bin/env python3
"""
⚛️ QUANTUM TRIPLE M1 - MULTI-CONFLUÊNCIA
🎯 4 Confluências: EMA9/EMA21, RSI, Força do Candle, Rompimento
💪 Mínimo 3 confirmações
📊 6 Pares OTC + 6 Pares Mercado Aberto (SOMENTE MOEDAS)
⏱️ M1
🔄 Gale 1.5x
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
    print("⚛️ QUANTUM TRIPLE M1 - Multi-Confluência")

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

# ═══════════════════════════════════════════
# 📊 ATIVOS - SOMENTE MOEDAS (OTC + MERCADO ABERTO)
# ═══════════════════════════════════════════

# 6 Pares OTC (apenas forex)
ATIVOS_OTC = {
    "EURUSD-OTC": "EURUSD-OTC",
    "GBPUSD-OTC": "GBPUSD-OTC",
    "USDJPY-OTC": "USDJPY-OTC",
    "AUDUSD-OTC": "AUDUSD-OTC",
    "USDCAD-OTC": "USDCAD-OTC",
    "EURGBP-OTC": "EURGBP-OTC"
}

# 6 Pares de Mercado Aberto (apenas forex)
ATIVOS_MERCADO = {
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "EURGBP": "EURGBP"
}

class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c
    def send(self, txt):
        try: requests.post(f"{self.url}/sendMessage", json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"}, timeout=10)
        except: pass

# ═══════════════════════════════════════════
# 📊 FUNÇÕES DE INDICADORES
# ═══════════════════════════════════════════

def ema(fechamentos, periodo):
    if len(fechamentos) < periodo:
        return None

    fator = 2 / (periodo + 1)
    valor = float(np.mean(fechamentos[:periodo]))

    for fechamento in fechamentos[periodo:]:
        valor = float(fechamento) * fator + valor * (1 - fator)

    return valor


def calcular_rsi(velas, periodo=14):
    fechamentos = np.array(
        [vela["close"] for vela in velas],
        dtype=float
    )

    if len(fechamentos) <= periodo:
        return 50.0

    variacoes = np.diff(fechamentos[-periodo - 1:])
    ganhos = np.mean(np.maximum(variacoes, 0))
    perdas = np.mean(np.maximum(-variacoes, 0))

    if perdas == 0:
        return 100.0

    return float(100 - (100 / (1 + ganhos / perdas)))


def calcular_atr(velas, periodo=14):
    if len(velas) <= periodo:
        return 0.0

    true_ranges = []

    anteriores = velas[-periodo - 1:-1]
    atuais = velas[-periodo:]

    for anterior, atual in zip(anteriores, atuais):
        true_range = max(
            atual["high"] - atual["low"],
            abs(atual["high"] - anterior["close"]),
            abs(atual["low"] - anterior["close"])
        )

        true_ranges.append(true_range)

    return float(np.mean(true_ranges))


# ═══════════════════════════════════════════
# 🎯 ESTRATÉGIA QUANTUM TRIPLE
# ═══════════════════════════════════════════

def quantum_triple(velas):
    """
    Analisa a vela atual e gera sinal para a próxima vela M1.
    
    Retorno:
    {
        "direction": "CALL" ou "PUT",
        "confidence": porcentagem,
        "confluences": quantidade,
        "rsi": valor do RSI
    }
    
    Retorna None quando não existe sinal válido.
    """

    if len(velas) < 30:
        return None

    fechamentos = [vela["close"] for vela in velas]

    atual = velas[-1]
    anterior = velas[-2]

    ema_9 = ema(fechamentos, 9)
    ema_21 = ema(fechamentos, 21)
    valor_rsi = calcular_rsi(velas)
    valor_atr = calcular_atr(velas)

    if ema_9 is None or ema_21 is None or valor_atr <= 0:
        return None

    confluencias_call = 0
    confluencias_put = 0

    # Confluência 1 — tendência pelas médias
    if ema_9 > ema_21:
        confluencias_call += 1
    elif ema_9 < ema_21:
        confluencias_put += 1

    # Confluência 2 — momentum pelo RSI
    if valor_rsi >= 52:
        confluencias_call += 1
    elif valor_rsi <= 48:
        confluencias_put += 1

    # Confluência 3 — força do candle
    corpo = atual["close"] - atual["open"]

    if corpo > 0 and abs(corpo) >= valor_atr * 0.15:
        confluencias_call += 1
    elif corpo < 0 and abs(corpo) >= valor_atr * 0.15:
        confluencias_put += 1

    # Confluência 4 — rompimento da vela anterior
    if atual["close"] > anterior["high"]:
        confluencias_call += 1
    elif atual["close"] < anterior["low"]:
        confluencias_put += 1

    if confluencias_call > confluencias_put:
        direcao = "CALL"
        total_confluencias = confluencias_call
    elif confluencias_put > confluencias_call:
        direcao = "PUT"
        total_confluencias = confluencias_put
    else:
        return None

    # Mínimo de 3 confirmações
    if total_confluencias < 3:
        return None

    confianca = min(
        95,
        60 + (total_confluencias * 7)
    )

    return {
        "direction": direcao,
        "confidence": confianca,
        "confluences": total_confluencias,
        "rsi": round(valor_rsi, 2)
    }


# ═══════════════════════════════════════════
# BOT
# ═══════════════════════════════════════════
class Bot:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        # Inicializa velas para OTC e Mercado Aberto
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.velas.update({nome: deque(maxlen=100) for nome in ATIVOS_MERCADO})
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
        
        # Combina todos os ativos para atualização
        todos_ativos = {**ATIVOS_OTC, **ATIVOS_MERCADO}
        
        for nome, ativo_id in todos_ativos.items():
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
            except Exception:
                # Ignora silenciosamente ativos indisponíveis (ex: OTC fora do horário)
                continue

    def buscar_sinal(self):
        """
        Busca sinais usando a função quantum_triple
        Escolhe o sinal com maior número de confluências
        Analisa OTC + Mercado Aberto simultaneamente
        """
        melhor = None
        melhor_score = 0
        
        for par, velas in self.velas.items():
            if len(velas) < 30:
                continue
            
            velas_list = list(velas)
            resultado = quantum_triple(velas_list)
            
            if not resultado:
                continue
            
            if resultado['confidence'] >= CONFIANCA_MINIMA:
                score = resultado['confluences'] * 10 + resultado['confidence']
                
                if score > melhor_score:
                    melhor_score = score
                    melhor = {
                        'ativo': par,
                        'direcao': resultado['direction'],
                        'confianca': resultado['confidence'],
                        'confluencias': resultado['confluences'],
                        'rsi': resultado['rsi']
                    }
        
        return melhor

    def calcular_horario_entrada(self):
        agora = datetime.now(FUSO_BR)
        return agora.replace(second=0, microsecond=0) + timedelta(minutes=1)

    def formatar_sinal(self, sinal, horario):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        conf = sinal['confianca']
        confs = sinal.get('confluencias', 0)
        rsi = sinal.get('rsi', 0)
        hora = horario.strftime('%H:%M')
        
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM TRIPLE M1 ✅
⏲ EXPIRAÇÃO: M1

👉🏼 HORARIO: {hora}

🏳ATIVO: {ativo} {direcao}

📊 Confiança: {conf:.0f}%
🎯 Confluências: {confs}/4
📈 RSI: {rsi}

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
        print("⚛️ Bot QUANTUM TRIPLE M1 iniciando...")
        total_ativos = len(ATIVOS_OTC) + len(ATIVOS_MERCADO)
        self.tg.send(f"""🔥 *QUANTUM TRIPLE M1 ATIVADO*
📊 {len(ATIVOS_OTC)} Pares OTC + {len(ATIVOS_MERCADO)} Pares Mercado Aberto
⏱️ M1
🎯 4 Confluências:
   • EMA9 vs EMA21
   • RSI (14)
   • Força do Candle
   • Rompimento
💪 Mínimo 3 confirmações
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
                        print(f"✅ Sinal #{self.sinais}: {sinal['ativo']} | {sinal['direcao']} | {sinal['confianca']:.0f}% | {sinal['confluencias']}/4")
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
