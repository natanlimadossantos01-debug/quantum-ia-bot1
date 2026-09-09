#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M1 - CATÁLOGO INTELIGENTE PRO v3.0
🚂 Otimizado para Railway
🔄 Auto-Recuperação Inteligente
📊 12 Pares OTC
⏱️ Timeframe: M1
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
import pickle, logging, yaml
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from pathlib import Path
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# Configurações padrão
INTERVALO_MINIMO = 300
USAR_GALE = True
ANTECEDENCIA = 30
TIMEFRAME = 60
CONFIANCA_MINIMA = 50
MAX_SINAIS_DIARIOS = 100
MAX_LOSSES_CONSECUTIVOS = 3
MAX_TENTATIVAS_RECONEXAO = 5
TEMPO_ESPERA_RECONEXAO = 30

# ═══════════════════════════════════════════
# CONFIGURAÇÃO PARA RAILWAY
# ═══════════════════════════════════════════
def carregar_config():
    """Carrega configuração das variáveis de ambiente do Railway"""
    # Railway fornece PORT automaticamente
    port = int(os.environ.get('PORT', 8000))
    
    token = os.environ.get('TELEGRAM_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    email = os.environ.get('IQ_EMAIL')
    senha = os.environ.get('IQ_SENHA')
    
    if not (token and chat and email and senha):
        logger.error("❌ Configure as variáveis de ambiente no Railway!")
        print("""
╔═══════════════════════════════════════════╗
║   ⚠️ VARIÁVEIS DE AMBIENTE NECESSÁRIAS    ║
╠═══════════════════════════════════════════╣
║ TELEGRAM_TOKEN    - Token do bot Telegram  ║
║ TELEGRAM_CHAT_ID  - ID do chat Telegram    ║
║ IQ_EMAIL          - Email da IQ Option     ║
║ IQ_SENHA          - Senha da IQ Option     ║
╚═══════════════════════════════════════════╝
        """)
        # Não sair imediatamente para permitir que o Railway mostre logs
        return None
    
    config = {
        "token": token,
        "chat": chat,
        "email": email,
        "senha": senha,
        "port": port
    }
    
    logger.info("✅ Configuração carregada das variáveis de ambiente")
    return config

# ═══════════════════════════════════════════
# LOGGING OTIMIZADO PARA RAILWAY
# ═══════════════════════════════════════════
def configurar_logging():
    """Configura logging para ambiente Railway"""
    # No Railway, logs vão para stdout automaticamente
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger('QuantumIA')
    logger.setLevel(logging.INFO)
    
    return logger

logger = configurar_logging()

# ═══════════════════════════════════════════
# FASTAPI PARA HEALTH CHECK DO RAILWAY
# ═══════════════════════════════════════════
app = FastAPI(title="Quantum IA M1", version="3.0")

@app.get("/")
async def root():
    """Rota principal"""
    return {
        "status": "running",
        "bot": "Quantum IA M1",
        "version": "3.0"
    }

@app.get("/health")
async def health_check():
    """Health check para Railway"""
    global bot_instance
    
    if bot_instance:
        status = {
            "status": "healthy" if bot_instance.operacional else "degraded",
            "conexao_iq": "conectado" if bot_instance.iq_api and bot_instance.iq_api.check_connect() else "desconectado",
            "velas_carregadas": sum(len(v) for v in bot_instance.velas.values()),
            "sinais_enviados": bot_instance.sinais,
            "estrategia_atual": bot_instance.catalogo.estrategia_atual if bot_instance.catalogo else "N/A",
            "placar": bot_instance.placar
        }
    else:
        status = {
            "status": "starting",
            "conexao_iq": "não iniciado"
        }
    
    return JSONResponse(status)

@app.get("/status")
async def status_detalhado():
    """Status detalhado do bot"""
    global bot_instance
    
    if not bot_instance:
        return {"status": "não inicializado"}
    
    return {
        "operacional": bot_instance.operacional,
        "conexao": {
            "iq_option": "conectado" if bot_instance.iq_api and bot_instance.iq_api.check_connect() else "desconectado",
            "telegram": "configurado" if bot_instance.tg else "não configurado"
        },
        "estatisticas": {
            "sinais": bot_instance.sinais,
            "placar": bot_instance.placar,
            "taxa_acerto": bot_instance.calcular_taxa_acerto()
        },
        "velas": {
            "total": sum(len(v) for v in bot_instance.velas.values()),
            "por_ativo": {k: len(v) for k, v in bot_instance.velas.items()}
        },
        "catalogo": {
            "estrategia_atual": bot_instance.catalogo.estrategia_atual,
            "estrategias": {
                nome: {
                    "wins": dados['wins'],
                    "losses": dados['losses'],
                    "taxa": bot_instance.catalogo.get_taxa(nome)
                }
                for nome, dados in bot_instance.catalogo.estrategias.items()
            }
        }
    }

# ═══════════════════════════════════════════
# CLASSES PRINCIPAIS (MANTIDAS DO CÓDIGO ANTERIOR)
# ═══════════════════════════════════════════
class Telegram:
    def __init__(self, token, chat_id):
        self.url = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id
        self.logger = logging.getLogger('Telegram')
    
    async def send(self, txt):
        """Envia mensagem Telegram"""
        try:
            response = requests.post(
                f"{self.url}/sendMessage",
                json={"chat_id": self.chat_id, "text": txt, "parse_mode": "Markdown"},
                timeout=10
            )
            if response.status_code == 200:
                self.logger.debug("Mensagem enviada com sucesso")
            else:
                self.logger.warning(f"Erro ao enviar mensagem: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Erro ao enviar mensagem Telegram: {e}")

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
        self.logger = logging.getLogger('Catalogo')
    
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
            if total >= 3:
                taxa = (dados['wins'] / total) * 100
                if taxa > melhor_taxa:
                    melhor_taxa = taxa
                    melhor_nome = nome
        
        if melhor_nome and melhor_nome != self.estrategia_atual:
            self.logger.info(f"Estratégia alterada: {self.estrategia_atual} → {melhor_nome}")
            self.estrategia_atual = melhor_nome
        
        return self.estrategia_atual

class Bot:
    def __init__(self, config):
        self.config = config
        self.tg = Telegram(config['token'], config['chat'])
        self.velas = {nome: deque(maxlen=100) for nome in ATIVOS_OTC}
        self.catalogo = Catalogo()
        self.iq_api = None
        self.placar = {'w': 0, 'g1': 0, 'l': 0}
        self.ult_sinal = 0
        self.sinais = 0
        self.ultimo_dia = datetime.now(FUSO_BR).day
        self.logger = logging.getLogger('Bot')
        self.operacional = False
        self.velas_atualizando = False
        self.reconexoes = 0
        self.max_reconexoes = MAX_TENTATIVAS_RECONEXAO
    
    def calcular_taxa_acerto(self):
        total = self.placar['w'] + self.placar['g1'] + self.placar['l']
        if total == 0:
            return 0
        return round(((self.placar['w'] + self.placar['g1']) / total) * 100, 1)
    
    def conectar_iq(self):
        """Conecta à IQ Option"""
        try:
            if self.iq_api:
                try: 
                    self.iq_api.close()
                except: 
                    pass
                self.iq_api = None
            
            self.logger.info("🔌 Conectando à IQ Option...")
            
            # Timeout para conexão
            result = []
            thread = threading.Thread(
                target=lambda: result.append(self._conectar_thread()),
                daemon=True
            )
            thread.start()
            thread.join(timeout=30)
            
            if result and result[0]:
                self.iq_api = result[0][0]
                if self.iq_api and self.iq_api.check_connect():
                    self.logger.info("✅ Conectado à IQ Option")
                    self.operacional = True
                    return self.iq_api
            
            self.logger.error("❌ Falha na conexão")
            self.operacional = False
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro na conexão: {e}")
            self.operacional = False
            return None
    
    def _conectar_thread(self):
        """Conecta em thread separada"""
        try:
            from iqoptionapi.stable_api import IQ_Option
            api = IQ_Option(self.config['email'], self.config['senha'])
            check, _ = api.connect()
            if check:
                return (api, True)
            return None
        except Exception as e:
            self.logger.error(f"Erro na thread de conexão: {e}")
            return None
    
    async def atualizar_velas(self):
        """Atualiza velas de todos os ativos"""
        if self.velas_atualizando:
            return
        
        self.velas_atualizando = True
        
        try:
            if not self.iq_api or not self.iq_api.check_connect():
                self.logger.warning("API desconectada, tentando reconectar...")
                if self.reconexoes < self.max_reconexoes:
                    self.reconexoes += 1
                    self.conectar_iq()
                else:
                    self.logger.error("Máximo de reconexões atingido")
                    return
            
            api = self.iq_api
            
            for nome, ativo_id in ATIVOS_OTC.items():
                try:
                    if not api.check_connect():
                        break
                    
                    # Timeout para chamada da API
                    c = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, 
                            lambda: api.get_candles(ativo_id, TIMEFRAME, 60, time.time())
                        ),
                        timeout=10
                    )
                    
                    if c and len(c) > 0:
                        self.velas[nome].clear()
                        velas_validas = 0
                        
                        for x in c[-60:]:
                            if validar_vela(x):
                                self.velas[nome].append({
                                    'time': datetime.fromtimestamp(x['from'], FUSO_BR),
                                    'open': float(x['open']), 
                                    'high': float(x['max']),
                                    'low': float(x['min']), 
                                    'close': float(x['close']),
                                    'volume': int(x.get('volume', 0))
                                })
                                velas_validas += 1
                    
                    await asyncio.sleep(0.5)
                    
                except asyncio.TimeoutError:
                    self.logger.error(f"Timeout ao atualizar {nome}")
                except Exception as e:
                    self.logger.error(f"Erro ao atualizar {nome}: {e}")
            
            # Reset reconexões se sucesso
            self.reconexoes = 0
            self.operacional = True
            total_velas = sum(len(v) for v in self.velas.values())
            self.logger.info(f"✅ Velas atualizadas: {total_velas} velas")
            
        except Exception as e:
            self.logger.error(f"Erro geral na atualização: {e}")
            self.operacional = False
        finally:
            self.velas_atualizando = False
    
    def buscar_sinal(self):
        """Busca sinais usando a estratégia atual"""
        melhor = None
        melhor_score = 0
        
        estrategia = self.catalogo.estrategias[self.catalogo.estrategia_atual]['strategy']
        
        for par, velas in self.velas.items():
            if len(velas) < 4:
                continue
            
            direcao, conf = estrategia.analisar(velas)
            
            if direcao and conf >= CONFIANCA_MINIMA and conf > melhor_score:
                melhor_score = conf
                melhor = {
                    'ativo': par, 
                    'direcao': direcao, 
                    'confianca': conf, 
                    'estrategia': self.catalogo.estrategia_atual
                }
        
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
        
        emoji_direcao = "🟢" if direcao == 'CALL' else "🔴"
        
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM IA M1 PRO ✅
⏲ EXPIRAÇÃO: M1

👉🏼 HORARIO: {hora}

🏳ATIVO: {ativo}-OTC {direcao} {emoji_direcao}

📊 Confiança: {conf:.0f}%
🧠 Estratégia: {est}

🍀🍀BOA SORTE 🍀 🍀"""
    
    async def monitorar_resultado(self, sinal, horario_entrada):
        """Monitora resultado do sinal"""
        ativo = sinal['ativo']
        direcao = sinal['direcao']
        estrategia_nome = sinal['estrategia']
        
        try:
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
            
            self.catalogo.registrar(estrategia_nome, ganhou)
            
            if ganhou:
                self.placar['w'] += 1
                resultado = "✅ WIN"
            else:
                if USAR_GALE:
                    # Implementação do Gale
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
            
            # Reavalia catálogo
            if self.sinais % 5 == 0:
                self.catalogo.escolher_melhor()
            
            total = self.placar['w'] + self.placar['g1'] + self.placar['l']
            tx = round(((self.placar['w'] + self.placar['g1']) / total) * 100, 1) if total > 0 else 0.0
            
            msg = f"""{resultado}
📊 {ativo}-OTC | {direcao} {'🟢' if direcao=='CALL' else '🔴'}
📊 Placar: 🟢{self.placar['w']}W 🟡{self.placar['g1']}G1 🔴{self.placar['l']}L
🎯 Assertividade: {tx}%"""
            
            await self.tg.send(msg)
            
            if self.sinais % 10 == 0:
                await self.tg.send(self.catalogo.relatorio())
                
        except Exception as e:
            self.logger.error(f"Erro ao monitorar resultado: {e}")
    
    def verificar_zeramento_diario(self):
        agora = datetime.now(FUSO_BR)
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'g1': 0, 'l': 0}
            asyncio.create_task(self.tg.send("🔄 *PLACAR ZERADO*"))
            self.logger.info("🔄 Placar zerado para novo dia")
    
    async def executar(self):
        """Executa o bot principal"""
        self.logger.info("🚀 Bot iniciando no Railway...")
        
        mensagem_inicial = f"""🔥 *QUANTUM IA M1 PRO*
🚂 Railway Edition
🧠 6 Estratégias Adaptativas
📊 {len(ATIVOS_OTC)} Pares OTC
⏱️ M1
🔄 Auto-Recuperação
📡 Monitoramento 24/7"""
        
        await self.tg.send(mensagem_inicial)
        
        # Conexão inicial
        self.conectar_iq()
        
        # Atualização inicial
        await self.atualizar_velas()
        
        # Loop principal
        while True:
            try:
                self.verificar_zeramento_diario()
                
                agora = datetime.now(FUSO_BR)
                
                # Atualizar velas a cada 15 segundos
                if agora.second in [0, 15, 30, 45] and not self.velas_atualizando:
                    await self.atualizar_velas()
                
                # Verificar se há velas disponíveis
                total_velas = sum(len(v) for v in self.velas.values())
                if total_velas == 0:
                    self.logger.warning("⚠️ Nenhuma vela disponível!")
                    await asyncio.sleep(5)
                    continue
                
                # Buscar e enviar sinais
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
                        await self.tg.send(msg)
                        self.logger.info(f"📡 Sinal: {sinal['ativo']} {sinal['direcao']} via {sinal['estrategia']}")
                        asyncio.create_task(self.monitorar_resultado(sinal, horario_entrada))
                
                # Log de status a cada minuto
                if agora.second == 0:
                    self.logger.info(
                        f"💓 {agora.strftime('%H:%M:%S')} | "
                        f"Velas: {total_velas} | "
                        f"Sinais: {self.sinais} | "
                        f"🧠 {self.catalogo.estrategia_atual} | "
                        f"📡 {'Conectado' if self.iq_api and self.iq_api.check_connect() else 'Desconectado'}"
                    )
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Erro no loop principal: {e}", exc_info=True)
                await asyncio.sleep(5)

# ═══════════════════════════════════════════
# VARIÁVEL GLOBAL PARA HEALTH CHECK
# ═══════════════════════════════════════════
bot_instance = None

async def start_bot():
    """Inicia o bot em background"""
    global bot_instance
    
    config = carregar_config()
    if not config:
        logger.error("❌ Configuração inválida")
        return
    
    bot_instance = Bot(config)
    
    try:
        await bot_instance.executar()
    except Exception as e:
        logger.critical(f"Erro fatal: {e}", exc_info=True)

@app.on_event("startup")
async def startup_event():
    """Inicia o bot quando o servidor FastAPI iniciar"""
    asyncio.create_task(start_bot())

# ═══════════════════════════════════════════
# EXECUÇÃO PRINCIPAL
# ═══════════════════════════════════════════
if __name__ == "__main__":
    # Para Railway, usar uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
