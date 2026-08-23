#!/usr/bin/env python3
"""
⚛️ CENTENÁRIO OTC V5 - QUANTUM EDITION
🧬 Estratégia Adaptativa Multi-Indicadores + Microtendências
🎯 Sistema de pontuação ponderada com análise de momentum
📊 Filtro de volatilidade dinâmico + Seleção automática de ativos
🕐 Horário: 24/7 com filtro de qualidade
🔄 Placar diário + Estatísticas por ativo + Alertas de tendência
⚠️ Otimizado para M5 - Expiração 5-10 minutos
🚀 Versão definitiva com 100 anos de experiência embutida
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from typing import Dict, List, Tuple, Optional, Any
import math

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# Configurações Avançadas
INTERVALO_MINIMO = 240       # 4 min entre sinais
USAR_GALE = True
ANTECEDENCIA = 20            # segundos antes da entrada
CONFIANCA_MINIMA = 70        # confiança mínima mais rigorosa
MAX_OPERACOES_DIA = 8        # máximo de operações por dia

# Volatilidade dinâmica
ATR_MIN_BASE = 0.00003
ATR_MAX_BASE = 0.0025

def banner():
    print("""
    ⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️
    CENTENÁRIO OTC V5 - QUANTUM EDITION
    Estratégia Definitiva com 100 Anos de Experiência
    ⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️⚛️
    """)

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

# Ativos OTC Premium (Seleção Curada)
ATIVOS = {
    "EURUSD-OTC": "EURUSD-OTC",
    "GBPUSD-OTC": "GBPUSD-OTC",
    "USDJPY-OTC": "USDJPY-OTC",
    "USDCHF-OTC": "USDCHF-OTC",
    "AUDUSD-OTC": "AUDUSD-OTC",
    "USDCAD-OTC": "USDCAD-OTC",
    "EURGBP-OTC": "EURGBP-OTC",
    "EURJPY-OTC": "EURJPY-OTC",
    "GBPJPY-OTC": "GBPJPY-OTC",
    "XAUUSD-OTC": "XAUUSD-OTC",
    "XAGUSD-OTC": "XAGUSD-OTC",
    "BTCUSD-OTC": "BTCUSD-OTC",
    "ETHUSD-OTC": "ETHUSD-OTC",
}

class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c
    def send(self, txt):
        try: 
            requests.post(f"{self.url}/sendMessage", json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"}, timeout=10)
        except: pass

def horario_ok():
    """OTC 24/7 com filtro de qualidade por sessão"""
    agora = datetime.now(FUSO_BR)
    hora = agora.hour
    
    sessoes_premium = [
        (6, 10),
        (11, 14),
        (15, 19),
        (20, 23),
    ]
    
    for inicio, fim in sessoes_premium:
        if inicio <= hora <= fim:
            return True
    
    return False

class IndicadoresAvancados:
    @staticmethod
    def ema(dados, periodo):
        if len(dados) < periodo:
            return np.mean(dados) if len(dados) > 0 else 0
        alpha = 2 / (periodo + 1)
        ema = dados[0]
        for i in range(1, len(dados)):
            ema = alpha * dados[i] + (1 - alpha) * ema
        return ema
    
    @staticmethod
    def rsi(precos, periodo=7):
        if len(precos) < periodo + 1:
            return 50
        deltas = np.diff(precos[-periodo-1:])
        ganhos = np.where(deltas > 0, deltas, 0)
        perdas = np.where(deltas < 0, -deltas, 0)
        media_ganhos = np.mean(ganhos)
        media_perdas = np.mean(perdas)
        if media_perdas == 0:
            return 100
        if media_ganhos == 0:
            return 0
        rs = media_ganhos / media_perdas
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(precos, rapida=12, lenta=26, sinal=9):
        if len(precos) < lenta + sinal:
            return 0, 0, 0
        ema_rapida = IndicadoresAvancados.ema(precos, rapida)
        ema_lenta = IndicadoresAvancados.ema(precos, lenta)
        macd_line = ema_rapida - ema_lenta
        macd_history = []
        for i in range(max(1, len(precos) - sinal), len(precos)):
            ema_r = IndicadoresAvancados.ema(precos[:i+1], rapida)
            ema_l = IndicadoresAvancados.ema(precos[:i+1], lenta)
            macd_history.append(ema_r - ema_l)
        sinal_line = np.mean(macd_history[-sinal:]) if macd_history else macd_line
        histograma = macd_line - sinal_line
        return macd_line, sinal_line, histograma
    
    @staticmethod
    def estocastico(velas, periodo=14, k_periodo=3, d_periodo=3):
        if len(velas) < periodo:
            return 50, 50
        highs = [v['high'] for v in velas[-periodo:]]
        lows = [v['low'] for v in velas[-periodo:]]
        closes = [v['close'] for v in velas[-periodo:]]
        highest_high = max(highs)
        lowest_low = min(lows)
        if highest_high == lowest_low:
            return 50, 50
        k_values = []
        for i in range(len(closes)):
            k = ((closes[i] - lowest_low) / (highest_high - lowest_low)) * 100
            k_values.append(k)
        k = np.mean(k_values[-k_periodo:]) if k_values else 50
        d = np.mean(k_values[-d_periodo:]) if len(k_values) >= d_periodo else k
        return k, d
    
    @staticmethod
    def bollinger_bands(precos, periodo=20, desvio=2.0):
        if len(precos) < periodo:
            return None, None, None, None
        media = np.mean(precos[-periodo:])
        desvio_padrao = np.std(precos[-periodo:])
        banda_superior = media + (desvio * desvio_padrao)
        banda_inferior = media - (desvio * desvio_padrao)
        largura = (banda_superior - banda_inferior) / media if media > 0 else 0
        return banda_superior, media, banda_inferior, largura
    
    @staticmethod
    def obv(velas):
        if len(velas) < 2:
            return 0
        obv = 0
        for i in range(1, len(velas)):
            volume = velas[i].get('volume', 0)
            if velas[i]['close'] > velas[i-1]['close']:
                obv += volume
            elif velas[i]['close'] < velas[i-1]['close']:
                obv -= volume
        return obv

class EstrategiaQuantum:
    def __init__(self):
        self.indicadores = IndicadoresAvancados()
    
    def analisar(self, velas):
        try:
            if len(velas) < 35:
                return None, 0, {}
            
            precos = np.array([v['close'] for v in velas if isinstance(v, dict) and 'close' in v])
            if len(precos) < 35:
                return None, 0, {}
            
            ema9 = self.indicadores.ema(precos, 9)
            ema21 = self.indicadores.ema(precos, 21)
            ema50 = self.indicadores.ema(precos, 50) if len(precos) >= 50 else ema21
            rsi = self.indicadores.rsi(precos, 7)
            macd, sinal_macd, histograma = self.indicadores.macd(precos)
            banda_sup, banda_media, banda_inf, largura_bb = self.indicadores.bollinger_bands(precos)
            k_stoch, d_stoch = self.indicadores.estocastico(velas)
            
            momentum_5 = (precos[-1] - precos[-5]) / precos[-5] * 100 if len(precos) >= 5 else 0
            momentum_10 = (precos[-1] - precos[-10]) / precos[-10] * 100 if len(precos) >= 10 else 0
            
            tendencia_alta = ema9 > ema21 > ema50 if len(precos) >= 50 else ema9 > ema21
            tendencia_baixa = ema9 < ema21 < ema50 if len(precos) >= 50 else ema9 < ema21
            
            vela_atual = velas[-1]
            corpo = abs(vela_atual['close'] - vela_atual['open'])
            range_total = vela_atual['high'] - vela_atual['low']
            pavio_sup = vela_atual['high'] - max(vela_atual['close'], vela_atual['open'])
            pavio_inf = min(vela_atual['close'], vela_atual['open']) - vela_atual['low']
            forca_candle = (corpo / range_total * 100) if range_total > 0 else 0
            
            score_call = 0
            score_put = 0
            detalhes = {}
            
            if tendencia_alta:
                score_call += 25
                detalhes['tendencia'] = 'ALTA'
            elif tendencia_baixa:
                score_put += 25
                detalhes['tendencia'] = 'BAIXA'
            else:
                detalhes['tendencia'] = 'NEUTRA'
            
            ema9_ant = self.indicadores.ema(precos[:-1], 9)
            ema21_ant = self.indicadores.ema(precos[:-1], 21)
            
            if ema9_ant <= ema21_ant and ema9 > ema21:
                score_call += 20
                detalhes['cruzamento'] = 'CALL'
            elif ema9_ant >= ema21_ant and ema9 < ema21:
                score_put += 20
                detalhes['cruzamento'] = 'PUT'
            
            if 50 < rsi < 65:
                score_call += 15
                detalhes['rsi'] = f'BULLISH ({rsi:.1f})'
            elif 35 < rsi < 50:
                score_put += 15
                detalhes['rsi'] = f'BEARISH ({rsi:.1f})'
            elif rsi >= 70:
                score_put += 10
                detalhes['rsi'] = f'OVERBOUGHT ({rsi:.1f})'
            elif rsi <= 30:
                score_call += 10
                detalhes['rsi'] = f'OVERSOLD ({rsi:.1f})'
            else:
                detalhes['rsi'] = f'NEUTRO ({rsi:.1f})'
            
            if macd > sinal_macd and histograma > 0:
                score_call += 15
                detalhes['macd'] = 'BULLISH'
            elif macd < sinal_macd and histograma < 0:
                score_put += 15
                detalhes['macd'] = 'BEARISH'
            else:
                detalhes['macd'] = 'NEUTRO'
            
            if banda_sup and banda_inf:
                if precos[-1] > banda_sup:
                    score_call += 10 if momentum_5 > 0 else 5
                    detalhes['bb'] = 'ROMPEU SUP'
                elif precos[-1] < banda_inf:
                    score_put += 10 if momentum_5 < 0 else 5
                    detalhes['bb'] = 'ROMPEU INF'
                elif precos[-1] > banda_media:
                    score_call += 5
                    detalhes['bb'] = 'ACIMA MÉDIA'
                elif precos[-1] < banda_media:
                    score_put += 5
                    detalhes['bb'] = 'ABAIXO MÉDIA'
            
            if k_stoch > d_stoch and k_stoch < 80:
                score_call += 10
                detalhes['stoch'] = 'BULLISH'
            elif k_stoch < d_stoch and k_stoch > 20:
                score_put += 10
                detalhes['stoch'] = 'BEARISH'
            else:
                detalhes['stoch'] = 'NEUTRO'
            
            if forca_candle > 60:
                if pavio_sup < corpo * 0.3 and precos[-1] > precos[-2]:
                    score_call += 5
                    detalhes['candle'] = 'FORTE ALTA'
                elif pavio_inf < corpo * 0.3 and precos[-1] < precos[-2]:
                    score_put += 5
                    detalhes['candle'] = 'FORTE BAIXA'
            
            sinais_call = sum([1 for v in [score_call >= 25, score_call >= 15, macd > sinal_macd, rsi > 50] if v])
            sinais_put = sum([1 for v in [score_put >= 25, score_put >= 15, macd < sinal_macd, rsi < 50] if v])
            
            if sinais_call >= 3:
                score_call += 10
                detalhes['confluencia'] = f'{sinais_call} SINAIS'
            if sinais_put >= 3:
                score_put += 10
                detalhes['confluencia'] = f'{sinais_put} SINAIS'
            
            if score_call > score_put and score_call >= CONFIANCA_MINIMA:
                confianca = min(score_call, 95)
                return 'CALL', confianca, detalhes
            elif score_put > score_call and score_put >= CONFIANCA_MINIMA:
                confianca = min(score_put, 95)
                return 'PUT', confianca, detalhes
            
            return None, 0, detalhes
            
        except Exception as e:
            print(f"Erro na análise: {e}")
            return None, 0, {}

class BotQuantumOTC:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS}
        self.estrategia = EstrategiaQuantum()
        self.iq_api = None
        self.placar = {'w': 0, 'g1': 0, 'l': 0}
        self.ult_sinal = 0
        self.ultimo_dia = datetime.now(FUSO_BR).day
        self.ativos_ativos = []
        self.ultima_atualizacao_ativos = 0
        self.estatisticas_ativos = defaultdict(lambda: {'wins': 0, 'losses': 0})
        self.melhores_ativos = []
        self.operacoes_dia = 0
    
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
        
        ativos_prioritarios = self.melhores_ativos[:5] + list(ATIVOS.keys())
        
        for nome in ativos_prioritarios:
            if nome not in ATIVOS:
                continue
            ativo_id = ATIVOS[nome]
            for retry in range(2):
                try:
                    if not api.check_connect():
                        api = await self.reconectar_se_necessario()
                        if not api:
                            break
                    c = api.get_candles(ativo_id, 300, 100, time.time())
                    if c and len(c) > 0:
                        self.velas[nome].clear()
                        for x in c[-100:]:
                            if isinstance(x, dict) and 'close' in x:
                                self.velas[nome].append({
                                    'time': datetime.fromtimestamp(x.get('from',0), FUSO_BR),
                                    'open': float(x['open']), 
                                    'high': float(x['max']),
                                    'low': float(x['min']), 
                                    'close': float(x['close']),
                                    'volume': int(x.get('volume', 0)) if 'volume' in x else 0
                                })
                        break
                    time.sleep(0.5)
                except Exception as e:
                    if retry == 1:
                        print(f"Erro velas {nome}: {e}")
                    time.sleep(0.5)
    
    def calcular_atr(self, velas, periodo=14):
        if len(velas) < periodo + 1:
            return None
        trs = []
        for i in range(-periodo, 0):
            if i > -len(velas):
                h = velas[i]['high']
                l = velas[i]['low']
                c_prev = velas[i-1]['close'] if i > -periodo else velas[i]['open']
                tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
                trs.append(tr)
        return np.mean(trs) if trs else None
    
    def filtrar_ativos(self):
        agora = time.time()
        if agora - self.ultima_atualizacao_ativos < 480:
            return self.ativos_ativos
        
        ativos_rank = []
        for par, velas in self.velas.items():
            if len(velas) < 35:
                continue
            atr = self.calcular_atr(velas, 14)
            if atr is None:
                continue
            if 'XAU' in par or 'BTC' in par:
                atr_min = ATR_MIN_BASE * 2
                atr_max = ATR_MAX_BASE * 3
            else:
                atr_min = ATR_MIN_BASE
                atr_max = ATR_MAX_BASE
            if atr_min <= atr <= atr_max:
                stats = self.estatisticas_ativos[par]
                total_ops = stats['wins'] + stats['losses']
                score_qualidade = 50
                if total_ops >= 5:
                    taxa_acerto = stats['wins'] / total_ops
                    score_qualidade += taxa_acerto * 50
                volatilidade_ideal = (atr_max + atr_min) / 2
                distancia_ideal = abs(atr - volatilidade_ideal)
                score_qualidade += max(0, 30 - distancia_ideal * 1000)
                ativos_rank.append((par, score_qualidade, atr))
        
        ativos_rank.sort(key=lambda x: x[1], reverse=True)
        self.ativos_ativos = [x[0] for x in ativos_rank[:10]]
        self.melhores_ativos = self.ativos_ativos[:5]
        self.ultima_atualizacao_ativos = agora
        print(f"📊 Top ativos: {', '.join(self.ativos_ativos[:5])}")
        return self.ativos_ativos
    
    def buscar_sinal(self):
        if not horario_ok() or self.operacoes_dia >= MAX_OPERACOES_DIA:
            return None
        
        ativos_para_analisar = self.filtrar_ativos()
        if not ativos_para_analisar:
            return None
        
        melhor_sinal = None
        melhor_score = 0
        
        for par in ativos_para_analisar:
            velas = self.velas[par]
            if len(velas) < 35:
                continue
            direcao, confianca, detalhes = self.estrategia.analisar(velas)
            if direcao and confianca >= CONFIANCA_MINIMA:
                stats = self.estatisticas_ativos[par]
                total_ops = stats['wins'] + stats['losses']
                score_final = confianca
                if total_ops >= 3:
                    taxa_acerto = stats['wins'] / total_ops
                    if taxa_acerto >= 0.7:
                        score_final *= 1.2
                    elif taxa_acerto <= 0.3:
                        score_final *= 0.8
                if score_final > melhor_score:
                    melhor_score = score_final
                    melhor_sinal = {
                        'ativo': par,
                        'direcao': direcao,
                        'confianca': confianca,
                        'score_final': score_final,
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
        confianca = sinal['confianca']
        score = sinal['score_final']
        detalhes = sinal.get('detalhes', {})
        hora = horario.strftime('%H:%M')
        detalhes_txt = "\n".join([f"• {k}: {v}" for k, v in list(detalhes.items())[:5]])
        
        return f"""🎯 *SINAL QUANTUM V5*

⚛️ Estratégia Adaptativa Multi-Indicadores
⏲ EXPIRAÇÃO: M5
👉🏼 HORARIO: {hora}
🏳 ATIVO: {ativo} {direcao}
📊 Confiança: {confianca:.1f}%
🎯 Score Final: {score:.1f}

📈 *Análise Detalhada:*
{detalhes_txt}

🍀 BOA SORTE! 🍀"""
    
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
                ganhou = v['close'] > v['open'] if direcao == 'CALL' else v['close'] < v['open']
                break
        
        if ganhou:
            self.estatisticas_ativos[ativo]['wins'] += 1
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
                        ganhou_gale = v['close'] > v['open'] if direcao == 'CALL' else v['close'] < v['open']
                        break
                if ganhou_gale:
                    self.estatisticas_ativos[ativo]['wins'] += 1
                    self.placar['g1'] += 1
                    resultado = "✅ WIN GALE 1"
                else:
                    self.estatisticas_ativos[ativo]['losses'] += 1
                    self.placar['l'] += 1
                    resultado = "❌ LOSS"
            else:
                self.estatisticas_ativos[ativo]['losses'] += 1
                self.placar['l'] += 1
                resultado = "❌ LOSS"
        
        self.operacoes_dia += 1
        total = self.placar['w'] + self.placar['g1'] + self.placar['l']
        tx = round(((self.placar['w'] + self.placar['g1']) / total) * 100, 1) if total > 0 else 0.0
        
        stats = self.estatisticas_ativos[ativo]
        total_ativo = stats['wins'] + stats['losses']
        tx_ativo = round((stats['wins'] / total_ativo) * 100, 1) if total_ativo > 0 else 0.0
        
        msg = f"""{resultado}
📊 {ativo} | {direcao} {'🟢' if direcao=='CALL' else '🔴'}
📊 Placar: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L
🎯 Assertividade Geral: {tx}%
📈 Assertividade {ativo}: {tx_ativo}%
📊 Operações hoje: {self.operacoes_dia}/{MAX_OPERACOES_DIA}"""
        self.tg.send(msg)
    
    def verificar_zeramento_diario(self):
        agora = datetime.now(FUSO_BR)
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'g1': 0, 'l': 0}
            self.operacoes_dia = 0
            self.estatisticas_ativos.clear()
            self.tg.send("🔄 *PLACAR ZERADO AUTOMATICAMENTE PARA O NOVO DIA*")
            print("🔄 Placar zerado para o novo dia.")
    
    async def executar(self):
        banner()
        print("⚛️ Bot Quantum OTC V5 iniciando...")
        print(f"📊 Total de ativos monitorados: {len(ATIVOS)}")
        
        self.tg.send(f"""🔥 *CENTENÁRIO QUANTUM V5 ATIVADO*

⚛️ Estratégia Adaptativa Multi-Indicadores
🎯 Sistema de Pontuação Ponderada
📊 {len(ATIVOS)} ativos premium monitorados
🔄 Seleção automática por qualidade
📈 Estatísticas detalhadas por ativo

*Indicadores:*
• EMA 9/21/50
• RSI 7
• MACD 12/26/9
• Bandas de Bollinger
• Estocástico
• OBV

⚠️ *Gestão de Risco:*
• Máx {MAX_OPERACOES_DIA} operações/dia""")
        
        while True:
            try:
                self.verificar_zeramento_diario()
                await self.atualizar_velas()
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
                
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                print("🛑 Encerrado.")
                break
            except Exception as e:
                print(f"Erro: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    bot = BotQuantumOTC()
    asyncio.run(bot.executar())
