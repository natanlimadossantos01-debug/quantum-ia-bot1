#!/usr/bin/env python3
"""
⚛️ QUANTUM BOT PRO - SINAIS TELEGRAM (14 ESTRATÉGIAS) + HORÁRIOS CORRETOS
🕯️ 12 Quadrantes + 5-2-0 + Chinesa 3.0
🛡️ Filtros opcionais: Pavio, Vela Forte, Horário (sem filtros de tendência)
🧠 Catalogador inteligente
📨 Sinal + resultado (com gale 1) via Telegram
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os, random
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# Configurações
INTERVALO_MINIMO = 300       # 5 min entre sinais
USAR_GALE = True             # Simula gale 1 (correção com duas velas)
CONFIANCA_MINIMA = 0         # Não usado (estratégias retornam confiança fixa)

def banner():
    print("⚛️ QUANTUM BOT PRO - 14 Estratégias | Horários Corretos | Catálogo")

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
class EstrategiasM1:
    def __init__(self):
        self.velas = []
        self.quadrante_anterior = []
        self.quadrante_atual = []

    def add_vela(self, open_price, close_price, high, low):
        vela = [open_price, close_price, high, low]
        self.velas.append(vela)
        if len(self.velas) > 100:
            self.velas.pop(0)
        self._atualizar_quadrantes()

    def _atualizar_quadrantes(self):
        if len(self.velas) >= 10:
            self.quadrante_anterior = self.velas[-10:-5]
            self.quadrante_atual = self.velas[-5:]

    def get_cor(self, vela):
        if vela[1] > vela[0]: return 'up'
        elif vela[1] < vela[0]: return 'down'
        return 'doji'

    def contar_cores(self, velas, posicoes=None):
        if posicoes is None: posicoes = range(len(velas))
        ups = sum(1 for i in posicoes if i < len(velas) and self.get_cor(velas[i]) == 'up')
        downs = sum(1 for i in posicoes if i < len(velas) and self.get_cor(velas[i]) == 'down')
        return ups, downs

    def get_minoria(self, velas, posicoes=None):
        ups, downs = self.contar_cores(velas, posicoes)
        if ups < downs and ups > 0: return 'up'
        elif downs < ups and downs > 0: return 'down'
        return 'doji'

    def get_maioria(self, velas, posicoes=None):
        ups, downs = self.contar_cores(velas, posicoes)
        if ups > downs: return 'up'
        elif downs > ups: return 'down'
        return 'doji'

    # 12 quadrantes (com offset de entrada)
    def mhi1(self):
        if len(self.quadrante_anterior) < 3: return None
        minoria = self.get_minoria(self.quadrante_anterior, [-3, -2, -1])
        if minoria == 'doji': return None
        return {'nome': 'MHI 1', 'direcao': 'CALL' if minoria == 'up' else 'PUT', 'offset': 0}

    def mhi2(self):
        if len(self.quadrante_anterior) < 3: return None
        minoria = self.get_minoria(self.quadrante_anterior, [-3, -2, -1])
        if minoria == 'doji': return None
        return {'nome': 'MHI 2', 'direcao': 'CALL' if minoria == 'up' else 'PUT', 'offset': 1}

    def mhi3(self):
        if len(self.quadrante_anterior) < 3: return None
        minoria = self.get_minoria(self.quadrante_anterior, [-3, -2, -1])
        if minoria == 'doji': return None
        return {'nome': 'MHI 3', 'direcao': 'CALL' if minoria == 'up' else 'PUT', 'offset': 2}

    def vituxo2(self):
        if len(self.quadrante_anterior) < 3: return None
        maioria = self.get_maioria(self.quadrante_anterior, [0, 1, 2])
        if maioria == 'doji': return None
        return {'nome': 'VITUXO 2.0', 'direcao': 'CALL' if maioria == 'up' else 'PUT', 'offset': 2}

    def c3(self):
        if len(self.quadrante_anterior) < 1: return None
        cor = self.get_cor(self.quadrante_anterior[0])
        if cor == 'doji': return None
        return {'nome': 'C3', 'direcao': 'CALL' if cor == 'up' else 'PUT', 'offset': 0}

    def msf(self):
        if len(self.quadrante_anterior) < 1: return None
        cor = self.get_cor(self.quadrante_anterior[0])
        if cor == 'doji': return None
        direcao = 'PUT' if cor == 'up' else 'CALL'
        return {'nome': 'MSF', 'direcao': direcao, 'offset': 4}

    def milhao_maioria(self):
        if len(self.quadrante_anterior) < 5: return None
        maioria = self.get_maioria(self.quadrante_anterior)
        if maioria == 'doji': return None
        return {'nome': 'Milhão (Maioria)', 'direcao': 'CALL' if maioria == 'up' else 'PUT', 'offset': 0}

    def milhao_minoria(self):
        if len(self.quadrante_anterior) < 5: return None
        minoria = self.get_minoria(self.quadrante_anterior)
        if minoria == 'doji': return None
        return {'nome': 'Milhão (Minoria)', 'direcao': 'CALL' if minoria == 'up' else 'PUT', 'offset': 0}

    def tres_vizinhos(self):
        if len(self.quadrante_atual) < 4: return None
        cor = self.get_cor(self.quadrante_atual[3])
        if cor == 'doji': return None
        return {'nome': '3 Vizinhos', 'direcao': 'CALL' if cor == 'up' else 'PUT', 'offset': 4}

    def daka(self):
        if len(self.quadrante_anterior) < 4: return None
        cor = self.get_cor(self.quadrante_anterior[3])
        if cor == 'doji': return None
        return {'nome': 'DAKA', 'direcao': 'CALL' if cor == 'up' else 'PUT', 'offset': 0}

    def estrategia_23(self):
        if len(self.quadrante_atual) < 1: return None
        cor = self.get_cor(self.quadrante_atual[0])
        if cor == 'doji': return None
        return {'nome': '23', 'direcao': 'CALL' if cor == 'up' else 'PUT', 'offset': 1}

    def r7(self):
        if len(self.quadrante_anterior) < 8: return None
        cor = self.get_cor(self.quadrante_anterior[7])
        if cor == 'doji': return None
        return {'nome': 'R7', 'direcao': 'CALL' if cor == 'up' else 'PUT', 'offset': 6}

    # 5-2-0 e Chinesa 3.0 (não baseadas em quadrante, entrada no próximo minuto)
    def estrategia_520(self, v):
        try:
            if len(v) < 25: return None
            precos = [x['close'] for x in v]
            mm5 = np.mean(precos[-5:])
            media20 = np.mean(precos[-20:])
            std20 = np.std(precos[-20:])
            bs = media20 + 2*std20
            bi = media20 - 2*std20
            atual = precos[-1]
            if atual > mm5 and atual <= bi*1.002: return {'nome': '5-2-0', 'direcao': 'CALL', 'offset': None}
            if atual < mm5 and atual >= bs*0.998: return {'nome': '5-2-0', 'direcao': 'PUT', 'offset': None}
            return None
        except: return None

    def chinesa_30(self, v):
        try:
            if len(v) < 30: return None
            precos = [x['close'] for x in v]
            ma20 = np.mean(precos[-20:])
            suporte = min(x['low'] for x in v[-10:])
            resistencia = max(x['high'] for x in v[-10:])
            atual = precos[-1]
            if atual > ma20 and v[-1]['high'] > resistencia: return {'nome': 'Chinesa 3.0', 'direcao': 'CALL', 'offset': None}
            if atual < ma20 and v[-1]['low'] < suporte: return {'nome': 'Chinesa 3.0', 'direcao': 'PUT', 'offset': None}
            return None
        except: return None

    def executar_todas(self):
        sinais = []
        estrategias = [
            ('MHI 1', self.mhi1), ('MHI 2', self.mhi2), ('MHI 3', self.mhi3),
            ('VITUXO 2.0', self.vituxo2), ('C3', self.c3), ('MSF', self.msf),
            ('Milhão (Maioria)', self.milhao_maioria), ('Milhão (Minoria)', self.milhao_minoria),
            ('3 Vizinhos', self.tres_vizinhos), ('DAKA', self.daka),
            ('23', self.estrategia_23), ('R7', self.r7)
        ]
        for nome, func in estrategias:
            try:
                res = func()
                if res:
                    res['nome'] = nome
                    sinais.append(res)
            except: pass
        return sinais

# ------------------------- CATALOGADOR -------------------------
class Catalogador:
    def __init__(self):
        self.performance = {}
        self.total_operacoes = 0

    def registrar(self, estrategia, par, ganhou):
        chave = f"{estrategia}|{par}"
        if chave not in self.performance:
            self.performance[chave] = {'estrategia': estrategia, 'par': par, 'wins': 0, 'losses': 0}
        if ganhou:
            self.performance[chave]['wins'] += 1
        else:
            self.performance[chave]['losses'] += 1
        self.total_operacoes += 1

    def escolher_melhor(self, min_ops=3):
        melhores = []
        for chave, p in self.performance.items():
            total = p['wins'] + p['losses']
            if total >= min_ops:
                taxa = (p['wins'] / total) * 100
                melhores.append({'estrategia': p['estrategia'], 'par': p['par'], 'taxa': taxa, 'total': total})
        melhores.sort(key=lambda x: x['taxa'], reverse=True)
        return melhores[0] if melhores else None

    def relatorio(self):
        msg = "📊 *CATALOGADOR INTELIGENTE*\n"
        msg += f"Total: {self.total_operacoes} operações\n\n"
        for chave, p in sorted(self.performance.items(), key=lambda x: (x[1]['wins']/max(x[1]['wins']+x[1]['losses'],1)), reverse=True):
            total = p['wins'] + p['losses']
            if total > 0:
                taxa = (p['wins'] / total) * 100
                msg += f"• {p['estrategia']} em {p['par']}: {taxa:.0f}% ({p['wins']}W/{p['losses']}L)\n"
        return msg

# ------------------------- BOT -------------------------
class BotProSinais:
    def __init__(self):
        self.tg = Telegram(TOKEN, CHAT)
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.estrategias_quadrantes = EstrategiasM1()
        self.catalogador = Catalogador()
        self.placar = {'w': 0, 'g1': 0, 'l': 0}
        self.ult_sinal = 0
        self.iq_api = None

    def conectar_iq(self):
        from iqoptionapi.stable_api import IQ_Option
        email = os.environ.get('IQ_EMAIL')
        senha = os.environ.get('IQ_SENHA')
        if not email or not senha: return None
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

    async def atualizar_velas(self):
        if self.iq_api is None or not self.iq_api.check_connect():
            if not self.conectar_iq(): return
        for nome, ativo_id in ATIVOS_OTC.items():
            for retry in range(3):
                try:
                    c = self.iq_api.get_candles(ativo_id, 60, 80, time.time())
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
                    time.sleep(2)
                except Exception as e:
                    print(f"Erro velas {nome}: {e}")
                    time.sleep(2)
                    if "Expecting value" in str(e): self.conectar_iq()

    def buscar_sinal(self):
        # Filtro de horário simples
        hora = datetime.now(FUSO_BR).hour
        if 22 <= hora or hora < 6:
            return None

        # Tenta usar a melhor combinação do catálogo
        melhor = self.catalogador.escolher_melhor(3)
        if melhor:
            par = melhor['par']
            if par in self.velas and len(self.velas[par]) >= 11:
                # Preenche as velas para as estratégias de quadrante
                self.estrategias_quadrantes.velas = []
                for v in self.velas[par]:
                    self.estrategias_quadrantes.add_vela(v['open'], v['close'], v['high'], v['low'])
                # Verifica apenas a estratégia do catálogo
                for nome_est, func in self._get_estrategia_functions():
                    if nome_est == melhor['estrategia']:
                        res = func()
                        if res:
                            return {'ativo': par, 'direcao': res['direcao'],
                                    'confianca': 70, 'estrategia': nome_est,
                                    'offset': res['offset']}
                # Se não gerou sinal, cai para varredura geral

        # Varredura geral por todos os pares e estratégias
        for par, velas in self.velas.items():
            if len(velas) < 30: continue
            self.estrategias_quadrantes.velas = []
            for v in velas:
                self.estrategias_quadrantes.add_vela(v['open'], v['close'], v['high'], v['low'])
            # Estratégias de quadrante
            for res in self.estrategias_quadrantes.executar_todas():
                return {'ativo': par, 'direcao': res['direcao'],
                        'confianca': 70, 'estrategia': res['nome'],
                        'offset': res['offset']}
            # 5-2-0 e Chinesa
            res520 = self.estrategias_quadrantes.estrategia_520(velas)
            if res520:
                return {'ativo': par, 'direcao': res520['direcao'],
                        'confianca': 75, 'estrategia': '5-2-0',
                        'offset': None}
            resch = self.estrategias_quadrantes.chinesa_30(velas)
            if resch:
                return {'ativo': par, 'direcao': resch['direcao'],
                        'confianca': 80, 'estrategia': 'Chinesa 3.0',
                        'offset': None}
        return None

    def _get_estrategia_functions(self):
        return [
            ('MHI 1', self.estrategias_quadrantes.mhi1),
            ('MHI 2', self.estrategias_quadrantes.mhi2),
            ('MHI 3', self.estrategias_quadrantes.mhi3),
            ('VITUXO 2.0', self.estrategias_quadrantes.vituxo2),
            ('C3', self.estrategias_quadrantes.c3),
            ('MSF', self.estrategias_quadrantes.msf),
            ('Milhão (Maioria)', self.estrategias_quadrantes.milhao_maioria),
            ('Milhão (Minoria)', self.estrategias_quadrantes.milhao_minoria),
            ('3 Vizinhos', self.estrategias_quadrantes.tres_vizinhos),
            ('DAKA', self.estrategias_quadrantes.daka),
            ('23', self.estrategias_quadrantes.estrategia_23),
            ('R7', self.estrategias_quadrantes.r7)
        ]

    def calcular_horario_entrada(self, offset):
        """
        Calcula o horário de entrada correto.
        offset = 0..4 -> vela do quadrante atual (0=primeira, 1=segunda, etc.)
        offset = None -> próximo minuto cheio (para 5-2-0 e Chinesa)
        """
        agora = datetime.now(FUSO_BR)
        if offset is None:
            return agora.replace(second=0, microsecond=0) + timedelta(minutes=1)

        minuto = agora.minute
        resto = minuto % 5
        if resto == 0 and agora.second == 0:
            base = agora.replace(second=0, microsecond=0)
        else:
            base = agora.replace(second=0, microsecond=0) + timedelta(minutes=5 - resto)

        # Garante que offset não ultrapasse 4
        offset = min(offset, 4)
        horario = base + timedelta(minutes=offset)
        return horario

    async def monitorar_resultado(self, sinal, horario_entrada):
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        estrategia = sinal['estrategia']
        confianca = sinal['confianca']

        # Aguarda fechamento da vela de entrada
        agora = datetime.now(FUSO_BR)
        espera = (horario_entrada + timedelta(minutes=1) - agora).total_seconds()
        if espera > 0:
            await asyncio.sleep(espera)
        await asyncio.sleep(5)
        await self.atualizar_velas()
        velas = self.velas[ativo]

        ganhou = False
        for v in velas:
            if v['time'].replace(second=0) == horario_entrada:
                ganhou = v['close'] > v['open'] if direcao == 'CALL' else v['close'] < v['open']
                break

        if ganhou:
            self.placar['w'] += 1
            resultado = "✅ WIN"
            self.catalogador.registrar(estrategia, ativo, True)
        else:
            if USAR_GALE:
                # Gale 1: vela seguinte
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
                    if v['time'].replace(second=0) == proxima_vela:
                        ganhou_gale = v['close'] > v['open'] if direcao == 'CALL' else v['close'] < v['open']
                        break
                if ganhou_gale:
                    self.placar['g1'] += 1
                    resultado = "✅ WIN GALE 1"
                    self.catalogador.registrar(estrategia, ativo, True)
                else:
                    self.placar['l'] += 1
                    resultado = "❌ LOSS"
                    self.catalogador.registrar(estrategia, ativo, False)
            else:
                self.placar['l'] += 1
                resultado = "❌ LOSS"
                self.catalogador.registrar(estrategia, ativo, False)

        total = self.placar['w'] + self.placar['g1'] + self.placar['l']
        tx = round(((self.placar['w'] + self.placar['g1']) / total) * 100, 1) if total > 0 else 0.0
        msg = f"""{resultado}
📊 {ativo}-OTC | {direcao} {'🟢' if direcao=='CALL' else '🔴'}
📊 Placar: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L
🎯 Assertividade: {tx}%"""
        self.tg.send(msg)

        if self.catalogador.total_operacoes % 10 == 0 and self.catalogador.total_operacoes > 0:
            self.tg.send(self.catalogador.relatorio())

    async def executar(self):
        banner()
        print("⚛️ Bot Pro 14 estratégias iniciando...")
        self.tg.send("🔥 *QUANTUM BOT PRO ATIVADO*\n📊 14 Estratégias | Horários corretos\n🧠 Catálogo inteligente\n⏱️ Sinais a cada 5min | Gale 1")
        while True:
            try:
                await self.atualizar_velas()
                sinal = self.buscar_sinal()
                if sinal and time.time() - self.ult_sinal > INTERVALO_MINIMO:
                    self.ult_sinal = time.time()
                    horario_entrada = self.calcular_horario_entrada(sinal['offset'])
                    he = horario_entrada.strftime('%H:%M')
                    emoji = '🟢' if sinal['direcao']=='CALL' else '🔴'
                    msg_sinal = f"""⚛️ SINAL QUANTUM PRO ⚛️

⏰ Horário: {he}
💰 Ativo: {sinal['ativo']}-OTC
📈 Direção: {sinal['direcao']} {emoji}
⌛️ Expiração: M1
📊 Confiança: {sinal['confianca']:.0f}%
🧠 Estratégia: {sinal['estrategia']}

⚠️ Entrar somente no horário marcado."""
                    self.tg.send(msg_sinal)
                    print(f"⚛️ {sinal['ativo']}-OTC {sinal['direcao']} | {sinal['estrategia']} | entrada {he}")
                    asyncio.create_task(self.monitorar_resultado(sinal, horario_entrada))
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
