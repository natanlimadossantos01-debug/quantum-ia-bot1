#!/usr/bin/env python3
"""
⚛️ CENTENÁRIO OTC V4 - MERCADO OTC IQ OPTION (MULTI-ATIVOS)
🕯️ Estratégia: EMA 9/21 + RSI 7 + Bandas de Bollinger (20,2)
🎯 Confluência de cruzamento EMA + RSI + rompimento Bollinger
📊 Filtro de volatilidade (ATR 14) + Seleção automática de ativos
🕐 Horário: 6h às 23h (todos os dias)
🔄 Placar diário automático
⚠️ Otimizado para M5 - Expiração 5-10 minutos
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os, random
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# Configurações
INTERVALO_MINIMO = 300       # 5 min entre sinais
USAR_GALE = True
ANTECEDENCIA = 20            # segundos antes da entrada
CONFIANCA_MINIMA = 65        # confiança mínima para OTC

# Volatilidade ATR otimizada para OTC (mais ampla para múltiplos ativos)
ATR_MIN = 0.00003
ATR_MAX = 0.0025

def banner():
    print("⚛️ CENTENÁRIO OTC V4 - Multi-Ativos | Estratégia Profissional")

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

# Ativos OTC da IQ Option (Lista Completa)
ATIVOS = {
    # Pares de Moedas OTC
    "EURUSD-OTC": "EURUSD-OTC",
    "GBPUSD-OTC": "GBPUSD-OTC",
    "USDCHF-OTC": "USDCHF-OTC",
    "EURGBP-OTC": "EURGBP-OTC",
    "USDJPY-OTC": "USDJPY-OTC",
    "AUDUSD-OTC": "AUDUSD-OTC",
    "USDCAD-OTC": "USDCAD-OTC",
    "NZDUSD-OTC": "NZDUSD-OTC",
    "EURJPY-OTC": "EURJPY-OTC",
    "GBPJPY-OTC": "GBPJPY-OTC",
    "AUDJPY-OTC": "AUDJPY-OTC",
    "EURAUD-OTC": "EURAUD-OTC",
    
    # Metais OTC
    "XAUUSD-OTC": "XAUUSD-OTC",  # Ouro
    "XAGUSD-OTC": "XAGUSD-OTC",  # Prata
    
    # Índices OTC
    "SP500-OTC": "SP500-OTC",
    "NASDAQ-OTC": "NASDAQ-OTC",
    "DOWJONES-OTC": "DOWJONES-OTC",
    "DAX-OTC": "DAX-OTC",
    "FTSE-OTC": "FTSE-OTC",
    
    # Criptomoedas OTC
    "BTCUSD-OTC": "BTCUSD-OTC",
    "ETHUSD-OTC": "ETHUSD-OTC",
    "LTCUSD-OTC": "LTCUSD-OTC",
    "BCHUSD-OTC": "BCHUSD-OTC",
    "XRPUSD-OTC": "XRPUSD-OTC",
    
    # Commodities OTC
    "USOIL-OTC": "USOIL-OTC",    # Petróleo WTI
    "UKOIL-OTC": "UKOIL-OTC",    # Petróleo Brent
    "NATGAS-OTC": "NATGAS-OTC",  # Gás Natural
}

class Telegram:
    def __init__(self, t, c):
        self.url = f"https://api.telegram.org/bot{t}"
        self.c = c
    def send(self, txt):
        try: requests.post(f"{self.url}/sendMessage", json={"chat_id": self.c, "text": txt, "parse_mode": "Markdown"}, timeout=10)
        except: pass

def horario_ok():
    """OTC funciona 24/7, mas selecionamos os melhores horários"""
    agora = datetime.now(FUSO_BR)
    hora = agora.hour
    # Melhores horários para OTC
    if 6 <= hora <= 9:    # Sessão asiática - tendências limpas
        return True
    if 11 <= hora <= 13:  # Volatilidade média
        return True
    if 15 <= hora <= 18:  # Melhor para scalping OTC
        return True
    if 20 <= hora <= 23:  # Sessão noturna com cuidado
        return True
    return False

class EstrategiaCentenario:
    """Estratégia Centenário OTC V4 - EMA + RSI + Bollinger Multi-Ativos"""
    
    def ema(self, dados, periodo):
        try:
            if len(dados) < periodo:
                return np.mean(dados) if len(dados) > 0 else 0
            alpha = 2 / (periodo + 1)
            ema = dados[0]
            for i in range(1, len(dados)):
                ema = alpha * dados[i] + (1 - alpha) * ema
            return ema
        except:
            return 0
    
    def rsi(self, precos, periodo=7):
        try:
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
        except:
            return 50
    
    def bollinger_bands(self, precos, periodo=20, desvio=2.0):
        try:
            if len(precos) < periodo:
                return None, None, None
            
            media = np.mean(precos[-periodo:])
            desvio_padrao = np.std(precos[-periodo:])
            
            banda_superior = media + (desvio * desvio_padrao)
            banda_inferior = media - (desvio * desvio_padrao)
            
            return banda_superior, media, banda_inferior
        except:
            return None, None, None
    
    def analisar(self, velas):
        try:
            if len(velas) < 30:
                return None, 0
            
            # Extrai preços de fechamento
            precos = []
            for v in velas:
                if isinstance(v, dict) and 'close' in v:
                    precos.append(v['close'])
            
            if len(precos) < 30:
                return None, 0
            
            precos = np.array(precos)
            
            # Calculando indicadores
            ema9 = self.ema(precos, 9)
            ema21 = self.ema(precos, 21)
            rsi_valor = self.rsi(precos, 7)
            banda_sup, banda_media, banda_inf = self.bollinger_bands(precos, 20, 2.0)
            
            # Verificando cruzamento de EMAs
            ema9_anterior = self.ema(precos[:-1], 9)
            ema21_anterior = self.ema(precos[:-1], 21)
            
            cruzamento_cima = ema9_anterior <= ema21_anterior and ema9 > ema21
            cruzamento_baixo = ema9_anterior >= ema21_anterior and ema9 < ema21
            
            # Preço atual
            preco_atual = precos[-1]
            preco_anterior = precos[-2] if len(precos) > 1 else preco_atual
            
            # Candles
            vela_atual = velas[-1] if isinstance(velas[-1], dict) else None
            if vela_atual and all(k in vela_atual for k in ['close', 'open', 'high', 'low']):
                corpo_atual = abs(vela_atual['close'] - vela_atual['open'])
                pavio_superior = vela_atual['high'] - max(vela_atual['close'], vela_atual['open'])
                pavio_inferior = min(vela_atual['close'], vela_atual['open']) - vela_atual['low']
            else:
                corpo_atual = 0
                pavio_superior = 0
                pavio_inferior = 0
            
            # Pontuação para CALL e PUT
            score_call = 0
            score_put = 0
            
            # 1. Cruzamento de EMAs (peso alto)
            if cruzamento_cima:
                score_call += 35
            elif ema9 > ema21 and ema9_anterior > ema21_anterior:
                score_call += 20
            
            if cruzamento_baixo:
                score_put += 35
            elif ema9 < ema21 and ema9_anterior < ema21_anterior:
                score_put += 20
            
            # 2. RSI (peso médio)
            if rsi_valor > 50 and rsi_valor < 70:
                score_call += 25
            elif rsi_valor >= 70:
                score_call += 15
                score_put += 10
            
            if rsi_valor < 50 and rsi_valor > 30:
                score_put += 25
            elif rsi_valor <= 30:
                score_put += 15
                score_call += 10
            
            # 3. Bandas de Bollinger (peso médio)
            if banda_sup and banda_inf:
                if preco_atual > banda_sup:
                    score_call += 20
                elif preco_atual > banda_media:
                    score_call += 10
                
                if preco_atual < banda_inf:
                    score_put += 20
                elif preco_atual < banda_media:
                    score_put += 10
            
            # 4. Análise de candle (peso baixo)
            if corpo_atual > 0:
                if pavio_superior < corpo_atual * 0.3 and preco_atual > preco_anterior:
                    score_call += 10
                if pavio_inferior < corpo_atual * 0.3 and preco_atual < preco_anterior:
                    score_put += 10
            
            # Decisão final
            if score_call > score_put and score_call >= CONFIANCA_MINIMA:
                confianca = min(score_call, 95)
                return 'CALL', confianca
            elif score_put > score_call and score_put >= CONFIANCA_MINIMA:
                confianca = min(score_put, 95)
                return 'PUT', confianca
            
            return None, 0
            
        except Exception as e:
            print(f"Erro na análise: {e}")
            return None, 0

class BotOTC:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS}
        self.estrategia = EstrategiaCentenario()
        self.iq_api = None
        self.placar = {'w': 0, 'g1': 0, 'l': 0}
        self.ult_sinal = 0
        self.ultimo_dia = datetime.now(FUSO_BR).day
        self.ativos_ativos = []
        self.ultima_atualizacao_ativos = 0
        self.estatisticas_ativos = defaultdict(lambda: {'wins': 0, 'losses': 0})

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
        
        # Atualiza em lotes para não sobrecarregar
        for nome, ativo_id in list(ATIVOS.items())[:15]:  # Primeiros 15 ativos
            for retry in range(2):
                try:
                    if not api.check_connect():
                        api = await self.reconectar_se_necessario()
                        if not api:
                            break
                    c = api.get_candles(ativo_id, 300, 80, time.time())  # M5
                    if c and len(c) > 0:
                        self.velas[nome].clear()
                        for x in c[-80:]:
                            if isinstance(x, dict) and 'close' in x:
                                self.velas[nome].append({
                                    'time': datetime.fromtimestamp(x.get('from',0), FUSO_BR),
                                    'open': float(x['open']), 'high': float(x['max']),
                                    'low': float(x['min']), 'close': float(x['close']),
                                    'volume': int(x.get('volume',0)) if 'volume' in x else 0
                                })
                        break
                    time.sleep(1)
                except Exception as e:
                    if retry == 1:
                        print(f"Erro velas {nome}: {e}")
                    time.sleep(1)

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

    def filtrar_ativos_volateis(self):
        agora = time.time()
        
        # Atualiza a cada 10 minutos
        if agora - self.ultima_atualizacao_ativos < 600:
            return self.ativos_ativos
        
        ativos_filtrados = []
        
        for par, velas in self.velas.items():
            if len(velas) < 30:
                continue
            
            atr = self.calcular_atr(velas, 14)
            if atr is None:
                continue
            
            # Verifica se o ATR está dentro da faixa ideal
            if ATR_MIN <= atr <= ATR_MAX:
                ativos_filtrados.append(par)
        
        self.ativos_ativos = ativos_filtrados
        self.ultima_atualizacao_ativos = agora
        
        print(f"📊 Ativos com volatilidade ideal: {len(ativos_filtrados)}")
        return ativos_filtrados

    def buscar_sinal(self):
        if not horario_ok():
            return None

        # Filtra ativos com boa volatilidade
        ativos_para_analisar = self.filtrar_ativos_volateis()
        
        if not ativos_para_analisar:
            return None

        melhor_sinal = None
        melhor_confianca = 0
        
        # Analisa os ativos filtrados
        for par in ativos_para_analisar:
            velas = self.velas[par]
            if len(velas) < 30:
                continue

            resultado = self.estrategia.analisar(velas)
            if resultado:
                direcao, conf = resultado
                
                # Bônus para ativos com bom histórico (se disponível)
                stats = self.estatisticas_ativos[par]
                total_ops = stats['wins'] + stats['losses']
                if total_ops >= 3:
                    taxa_acerto = stats['wins'] / total_ops
                    if taxa_acerto > 0.6:
                        conf *= 1.1  # Bônus de 10% para ativos consistentes
                
                if conf > melhor_confianca:
                    melhor_confianca = conf
                    melhor_sinal = {'ativo': par, 'direcao': direcao, 'confianca': conf}

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
        hora = horario.strftime('%H:%M')
        return f"""🎯 *SINAL CENTENÁRIO OTC V4*

⚛️ Estratégia: EMA 9/21 + RSI 7 + Bollinger
⏲ EXPIRAÇÃO: M5
👉🏼 HORARIO: {hora}
🏳 ATIVO: {ativo} {direcao}
📊 Confiança: {confianca:.1f}%

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

        # Atualiza estatísticas do ativo
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
            self.estatisticas_ativos.clear()
            self.tg.send("🔄 *PLACAR ZERADO AUTOMATICAMENTE PARA O NOVO DIA*")
            print("🔄 Placar zerado para o novo dia.")

    async def executar(self):
        banner()
        print("⚛️ Bot Centenário OTC V4 iniciando...")
        print(f"📊 Total de ativos monitorados: {len(ATIVOS)}")
        
        self.tg.send(f"""🔥 *CENTENÁRIO OTC V4 ATIVADO*

⚛️ Estratégia: EMA 9/21 + RSI 7 + Bollinger Bands
🎯 Mercado OTC (24/7)
📊 {len(ATIVOS)} ativos monitorados
🔄 Seleção automática por volatilidade
📈 Estatísticas por ativo

⚠️ *Gestão de Risco:*
• Máx 2% por operação
• Meta diária: 5-10%
• Máx 5 operações/dia""")
        
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
    bot = BotOTC()
    asyncio.run(bot.executar())
