#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M1 - CATÁLOGO INTELIGENTE PRO
🧠 Testa 6 estratégias e usa a melhor automaticamente
📊 12 Pares OTC
⏱️ Timeframe: M1
🔄 Gale 1
📈 Reavaliação a cada 10 sinais
💾 Persistência de dados
📝 Logging profissional
🛡️ Rate limiting
📊 Dashboard em tempo real
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os
import pickle, logging, yaml
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

# Configurações padrão (podem ser sobrescritas pelo config.yaml)
INTERVALO_MINIMO = 300
USAR_GALE = True
ANTECEDENCIA = 30
TIMEFRAME = 60
CONFIANCA_MINIMA = 50
MAX_SINAIS_DIARIOS = 200
MAX_LOSSES_CONSECUTIVOS = 2

def banner():
    print("""
╔═══════════════════════════════════════════╗
║   ⚛️ QUANTUM IA M1 - CATÁLOGO INTELIGENTE PRO ║
║   🧠 6 Estratégias Adaptativas             ║
║   📊 12 Pares OTC                          ║
║   💾 Persistência Inteligente              ║
║   🛡️ Rate Limiting & Monitoramento         ║
╚═══════════════════════════════════════════╝
    """)

# ═══════════════════════════════════════════
# SISTEMA DE LOGGING
# ═══════════════════════════════════════════
def configurar_logging():
    """Configura sistema de logging profissional"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f'bot_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler(),
            logging.FileHandler(log_dir / 'bot_completo.log')
        ]
    )
    
    # Criar logger específico para o bot
    logger = logging.getLogger('QuantumIA')
    logger.setLevel(logging.INFO)
    
    return logger

logger = configurar_logging()

# ═══════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════
def carregar_config():
    """Carrega configuração de variáveis de ambiente e arquivo YAML"""
    token = os.environ.get('TELEGRAM_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    email = os.environ.get('IQ_EMAIL')
    senha = os.environ.get('IQ_SENHA')
    
    if not (token and chat and email and senha):
        logger.error("❌ Configure as variáveis de ambiente!")
        banner()
        print("❌ Configure as variáveis de ambiente!")
        sys.exit(1)
    
    config = {
        "token": token,
        "chat": chat,
        "email": email,
        "senha": senha
    }
    
    # Carregar configurações avançadas do arquivo
    config_path = Path('config.yaml')
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                
            global INTERVALO_MINIMO, USAR_GALE, ANTECEDENCIA, TIMEFRAME
            global CONFIANCA_MINIMA, MAX_SINAIS_DIARIOS, MAX_LOSSES_CONSECUTIVOS
            
            INTERVALO_MINIMO = yaml_config.get('intervalo_minimo', INTERVALO_MINIMO)
            USAR_GALE = yaml_config.get('usar_gale', USAR_GALE)
            ANTECEDENCIA = yaml_config.get('antecedencia', ANTECEDENCIA)
            TIMEFRAME = yaml_config.get('timeframe', TIMEFRAME)
            CONFIANCA_MINIMA = yaml_config.get('confianca_minima', CONFIANCA_MINIMA)
            MAX_SINAIS_DIARIOS = yaml_config.get('max_sinais_diarios', MAX_SINAIS_DIARIOS)
            MAX_LOSSES_CONSECUTIVOS = yaml_config.get('max_losses_consecutivos', MAX_LOSSES_CONSECUTIVOS)
            
            logger.info("✅ Configurações avançadas carregadas do config.yaml")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar config.yaml: {e}")
    
    logger.info("✅ Configuração carregada com sucesso")
    banner()
    print("✅ Modo CLOUD detectado!")
    
    return config

cfg = carregar_config()
TOKEN = cfg['token']
CHAT = cfg['chat']
EMAIL = cfg['email']
SENHA = cfg['senha']

from iqoptionapi.stable_api import IQ_Option

# ═══════════════════════════════════════════
# ATIVOS OTC
# ═══════════════════════════════════════════
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

# ═══════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════
class RateLimiter:
    """Controla chamadas à API para evitar bloqueios"""
    def __init__(self, max_calls=10, time_window=60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque(maxlen=max_calls)
        self.logger = logging.getLogger('RateLimiter')
    
    def can_call(self):
        """Verifica se pode fazer chamada"""
        now = time.time()
        
        # Remove chamadas antigas
        while self.calls and now - self.calls[0] > self.time_window:
            self.calls.popleft()
        
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False
    
    async def wait_if_needed(self):
        """Aguarda se necessário antes de fazer chamada"""
        if not self.can_call():
            time_to_wait = self.time_window - (time.time() - self.calls[0])
            if time_to_wait > 0:
                self.logger.info(f"Rate limit atingido. Aguardando {time_to_wait:.2f}s")
                await asyncio.sleep(time_to_wait)
                return await self.wait_if_needed()
        return True

# ═══════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════
class Telegram:
    def __init__(self, token, chat_id):
        self.url = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id
        self.logger = logging.getLogger('Telegram')
        self.rate_limiter = RateLimiter(max_calls=30, time_window=60)
    
    async def send(self, txt):
        """Envia mensagem com rate limiting"""
        try:
            if await self.rate_limiter.wait_if_needed():
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
    
    def send_sync(self, txt):
        """Envia mensagem de forma síncrona (para emergências)"""
        try:
            requests.post(
                f"{self.url}/sendMessage",
                json={"chat_id": self.chat_id, "text": txt, "parse_mode": "Markdown"},
                timeout=10
            )
        except:
            pass

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
# VALIDAÇÃO DE VELAS
# ═══════════════════════════════════════════
def validar_vela(vela):
    """Valida se a vela tem dados consistentes"""
    if not isinstance(vela, dict):
        return False
    
    required_keys = ['open', 'high', 'low', 'close', 'from']
    if not all(key in vela for key in required_keys):
        return False
    
    try:
        high = float(vela['high'])
        low = float(vela['low'])
        open_price = float(vela['open'])
        close_price = float(vela['close'])
        
        # Validar consistência dos preços
        if high < max(open_price, close_price) or low > min(open_price, close_price):
            return False
        
        if high <= low:
            return False
        
        # Validar timestamps
        from_time = float(vela['from'])
        if from_time <= 0:
            return False
        
        return True
    except (ValueError, TypeError):
        return False

# ═══════════════════════════════════════════
# CATÁLOGO INTELIGENTE COM PERSISTÊNCIA
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
        self.logger = logging.getLogger('Catalogo')
        self.carregar_estado()
    
    def registrar(self, nome, ganhou):
        """Registra resultado e salva estado"""
        if nome in self.estrategias:
            if ganhou:
                self.estrategias[nome]['wins'] += 1
            else:
                self.estrategias[nome]['losses'] += 1
            self.salvar_estado()
    
    def get_taxa(self, nome):
        """Retorna taxa de acerto da estratégia"""
        if nome in self.estrategias:
            total = self.estrategias[nome]['wins'] + self.estrategias[nome]['losses']
            if total > 0:
                return (self.estrategias[nome]['wins'] / total) * 100
        return 0
    
    def escolher_melhor(self):
        """Escolhe a melhor estratégia baseado no desempenho"""
        melhor_nome = None
        melhor_taxa = 0
        
        for nome, dados in self.estrategias.items():
            total = dados['wins'] + dados['losses']
            if total >= 3:  # Mínimo 3 operações
                taxa = (dados['wins'] / total) * 100
                if taxa > melhor_taxa:
                    melhor_taxa = taxa
                    melhor_nome = nome
        
        if melhor_nome and melhor_nome != self.estrategia_atual:
            self.logger.info(f"Estratégia alterada: {self.estrategia_atual} → {melhor_nome}")
            self.estrategia_atual = melhor_nome
        
        return self.estrategia_atual
    
    def salvar_estado(self):
        """Salva estatísticas das estratégias em arquivo"""
        try:
            estado = {
                nome: {'wins': d['wins'], 'losses': d['losses']} 
                for nome, d in self.estrategias.items()
            }
            estado['estrategia_atual'] = self.estrategia_atual
            
            with open('catalogo_state.pkl', 'wb') as f:
                pickle.dump(estado, f)
            
            self.logger.debug("Estado do catálogo salvo")
        except Exception as e:
            self.logger.error(f"Erro ao salvar estado do catálogo: {e}")
    
    def carregar_estado(self):
        """Carrega estatísticas salvas"""
        try:
            with open('catalogo_state.pkl', 'rb') as f:
                estado = pickle.load(f)
                
                for nome, dados in estado.items():
                    if nome == 'estrategia_atual':
                        self.estrategia_atual = dados
                    elif nome in self.estrategias:
                        self.estrategias[nome]['wins'] = dados['wins']
                        self.estrategias[nome]['losses'] = dados['losses']
            
            self.logger.info("✅ Estado do catálogo carregado")
        except FileNotFoundError:
            self.logger.info("Nenhum estado anterior encontrado")
        except Exception as e:
            self.logger.error(f"Erro ao carregar estado do catálogo: {e}")
    
    def relatorio(self):
        """Gera relatório detalhado do catálogo"""
        msg = "📊 *CATÁLOGO INTELIGENTE*\n\n"
        
        # Ordenar estratégias por taxa de acerto
        estrategias_ordenadas = sorted(
            self.estrategias.items(),
            key=lambda x: self.get_taxa(x[0]),
            reverse=True
        )
        
        for nome, dados in estrategias_ordenadas:
            total = dados['wins'] + dados['losses']
            if total > 0:
                taxa = self.get_taxa(nome)
                emoji = "🟢" if taxa >= 60 else "🟡" if taxa >= 50 else "🔴"
                msg += f"{emoji} {nome}: {taxa:.0f}% ({dados['wins']}W/{dados['losses']}L)\n"
            else:
                msg += f"⚪ {nome}: Sem dados\n"
        
        msg += f"\n🎯 *Atual:* {self.estrategia_atual}"
        return msg

# ═══════════════════════════════════════════
# MONITOR DE SAÚDE
# ═══════════════════════════════════════════
class HealthMonitor:
    """Monitora a saúde do bot"""
    def __init__(self, bot):
        self.bot = bot
        self.last_signal_time = time.time()
        self.errors_count = 0
        self.max_errors = 5
        self.last_health_check = time.time()
        self.logger = logging.getLogger('HealthMonitor')
    
    def check_health(self):
        """Verifica se o bot está saudável"""
        issues = []
        
        # Verificar conexão
        if not self.bot.iq_api or not self.bot.iq_api.check_connect():
            issues.append("Conexão perdida")
        
        # Verificar tempo desde último sinal
        time_since_signal = time.time() - self.last_signal_time
        if time_since_signal > 3600:  # 1 hora sem sinais
            issues.append(f"Sem sinais por {time_since_signal/60:.0f} minutos")
        
        # Verificar erros
        if self.errors_count >= self.max_errors:
            issues.append(f"Muitos erros: {self.errors_count}")
        
        return issues
    
    async def monitor_loop(self):
        """Loop de monitoramento contínuo"""
        while True:
            try:
                issues = self.check_health()
                
                if issues:
                    alert = "⚠️ *ALERTA DE SAÚDE*\n"
                    alert += "\n".join(f"• {issue}" for issue in issues)
                    await self.bot.tg.send(alert)
                    self.logger.warning(alert)
                
                # Reset contador de erros se passou 1 hora sem erros
                if time.time() - self.last_health_check > 3600:
                    self.errors_count = 0
                    self.last_health_check = time.time()
                
                await asyncio.sleep(300)  # Verificar a cada 5 minutos
                
            except Exception as e:
                self.logger.error(f"Erro no monitor de saúde: {e}")
                await asyncio.sleep(60)

# ═══════════════════════════════════════════
# BOT PRINCIPAL
# ═══════════════════════════════════════════
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
        self.rate_limiter = RateLimiter(max_calls=10, time_window=60)
        self.health_monitor = HealthMonitor(self)
        self.logger = logging.getLogger('Bot')
        self.losses_consecutivos = 0
        
        # Carregar placar salvo
        self.carregar_placar()
    
    def carregar_placar(self):
        """Carrega placar salvo"""
        try:
            with open('placar_state.pkl', 'rb') as f:
                placar_salvo = pickle.load(f)
                self.placar = placar_salvo
                self.logger.info(f"✅ Placar carregado: {self.placar}")
        except FileNotFoundError:
            self.logger.info("Nenhum placar anterior encontrado")
        except Exception as e:
            self.logger.error(f"Erro ao carregar placar: {e}")
    
    def salvar_placar(self):
        """Salva placar atual"""
        try:
            with open('placar_state.pkl', 'wb') as f:
                pickle.dump(self.placar, f)
        except Exception as e:
            self.logger.error(f"Erro ao salvar placar: {e}")

    def conectar_iq(self):
        """Conecta à IQ Option"""
        try:
            if self.iq_api:
                try: 
                    self.iq_api.close()
                except: 
                    pass
            
            self.logger.info("Conectando à IQ Option...")
            self.iq_api = IQ_Option(EMAIL, SENHA)
            check, _ = self.iq_api.connect()
            
            if check:
                self.logger.info("✅ Conectado à IQ Option")
                return self.iq_api
            else:
                self.logger.error("❌ Falha na conexão")
                return None
        except Exception as e:
            self.logger.error(f"❌ Erro na conexão: {e}")
            return None

    async def reconectar_se_necessario(self):
        """Reconecta se necessário"""
        if self.iq_api is None or not self.iq_api.check_connect():
            self.logger.warning("🔄 Reconectando à IQ Option...")
            return self.conectar_iq()
        return self.iq_api

    async def atualizar_velas(self):
        """Atualiza velas de todos os ativos"""
        api = await self.reconectar_se_necessario()
        if not api:
            return
        
        for nome, ativo_id in ATIVOS_OTC.items():
            try:
                if not api.check_connect():
                    api = await self.reconectar_se_necessario()
                    if not api:
                        break
                
                # Rate limiting
                if not self.rate_limiter.can_call():
                    self.logger.warning(f"Rate limit atingido ao atualizar {nome}")
                    await asyncio.sleep(2)
                    continue
                
                c = api.get_candles(ativo_id, TIMEFRAME, 60, time.time())
                
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
                    
                    if velas_validas < 50:
                        self.logger.warning(f"Poucas velas válidas para {nome}: {velas_validas}")
                        
            except Exception as e:
                self.logger.error(f"Erro ao atualizar {nome}: {e}")
                self.health_monitor.errors_count += 1

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
        """Calcula horário de entrada"""
        agora = datetime.now(FUSO_BR)
        return agora.replace(second=0, microsecond=0) + timedelta(minutes=1)

    def formatar_sinal(self, sinal, horario):
        """Formata mensagem de sinal"""
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
            
            # Registra no catálogo
            self.catalogo.registrar(estrategia_nome, ganhou)
            
            if ganhou:
                self.placar['w'] += 1
                self.losses_consecutivos = 0
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
                        self.losses_consecutivos = 0
                        resultado = "✅ WIN GALE 1"
                    else:
                        self.placar['l'] += 1
                        self.losses_consecutivos += 1
                        resultado = "❌ LOSS"
                else:
                    self.placar['l'] += 1
                    self.losses_consecutivos += 1
                    resultado = "❌ LOSS"
            
            # Salvar placar
            self.salvar_placar()
            
            # Verificar stop loss
            if self.losses_consecutivos >= MAX_LOSSES_CONSECUTIVOS:
                alerta = f"🛑 *STOP LOSS ATIVADO*\n{MAX_LOSSES_CONSECUTIVOS} losses consecutivos!\nBot pausado por segurança."
                await self.tg.send(alerta)
                self.logger.warning(alerta)
                await asyncio.sleep(3600)  # Pausa de 1 hora
                self.losses_consecutivos = 0
            
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
            self.health_monitor.last_signal_time = time.time()
            
            # Envia relatório a cada 10 sinais
            if self.sinais % 10 == 0:
                await self.tg.send(self.catalogo.relatorio())
                
        except Exception as e:
            self.logger.error(f"Erro ao monitorar resultado: {e}")
            self.health_monitor.errors_count += 1

    def verificar_zeramento_diario(self):
        """Verifica se deve zerar placar diário"""
        agora = datetime.now(FUSO_BR)
        if agora.day != self.ultimo_dia:
            self.ultimo_dia = agora.day
            self.placar = {'w': 0, 'g1': 0, 'l': 0}
            self.salvar_placar()
            asyncio.create_task(self.tg.send("🔄 *PLACAR ZERADO*"))
            self.logger.info("🔄 Placar zerado para novo dia")

    async def executar(self):
        """Executa o bot principal"""
        banner()
        self.logger.info("⚛️ Bot Catálogo Inteligente PRO iniciando...")
        
        mensagem_inicial = f"""🔥 *QUANTUM IA CATÁLOGO PRO*
🧠 6 Estratégias Adaptativas
📊 {len(ATIVOS_OTC)} Pares OTC
⏱️ M1
🔄 Reavaliação automática
📈 Usa a melhor estratégia
💾 Persistência de dados
🛡️ Monitoramento avançado"""
        
        await self.tg.send(mensagem_inicial)
        
        if not self.conectar_iq():
            self.logger.error("❌ Falha na conexão inicial!")
            return
        
        await self.atualizar_velas()
        
        # Iniciar monitor de saúde
        asyncio.create_task(self.health_monitor.monitor_loop())
        
        while True:
            try:
                self.verificar_zeramento_diario()
                
                # Verificar limite de sinais diários
                if self.sinais >= MAX_SINAIS_DIARIOS:
                    self.logger.warning(f"Limite diário de sinais atingido: {MAX_SINAIS_DIARIOS}")
                    await asyncio.sleep(3600)  # Aguardar 1 hora
                    continue
                
                agora = datetime.now(FUSO_BR)
                if agora.second == 0:
                    total_velas = sum(len(v) for v in self.velas.values())
                    self.logger.info(f"💓 {agora.strftime('%H:%M:%S')} | Velas: {total_velas} | Sinais: {self.sinais} | 🧠 {self.catalogo.estrategia_atual}")
                    
                    if total_velas == 0:
                        self.logger.warning("🔄 Sem velas! Reconectando...")
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
                        await self.tg.send(msg)
                        self.logger.info(f"Sinal enviado: {sinal['ativo']} {sinal['direcao']} via {sinal['estrategia']}")
                        asyncio.create_task(self.monitorar_resultado(sinal, horario_entrada))
                
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Encerrado pelo usuário")
                break
            except Exception as e:
                self.logger.error(f"Erro no loop principal: {e}", exc_info=True)
                self.health_monitor.errors_count += 1
                await asyncio.sleep(5)

# ═══════════════════════════════════════════
# CONFIG YAML DE EXEMPLO
# ═══════════════════════════════════════════
def criar_config_exemplo():
    """Cria arquivo config.yaml de exemplo"""
    config_exemplo = """
# Configurações do QUANTUM IA M1 PRO
intervalo_minimo: 300  # Segundos entre sinais
usar_gale: true  # Usar Gale 1
antecedencia: 10  # Segundos de antecedência para envio
timeframe: 60  # Timeframe em segundos (60 = M1)
confianca_minima: 50  # Confiança mínima para enviar sinal
max_sinais_diarios: 100  # Máximo de sinais por dia
max_losses_consecutivos: 3  # Máximo de losses consecutivos (stop loss)
"""
    
    if not Path('config.yaml').exists():
        with open('config.yaml', 'w') as f:
            f.write(config_exemplo)
        logger.info("✅ config.yaml criado com valores padrão")

if __name__ == "__main__":
    criar_config_exemplo()
    asyncio.run(Bot().executar())
