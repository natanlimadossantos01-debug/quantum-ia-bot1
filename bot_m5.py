#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║   ⚛️  Q U A N T U M   I A   M 5           ║
║   🧠 Máxima Assertividade | 🔥 65%+        ║
║   🎯 65% Taxa Mínima | 🛡️ Filtro Pavio    ║
║   📐 Filtro Tendência | 📊 Super 5/3 + Last ║
║   ⏱️ 10min entre sinais | 🚫 Bloqueio Vela Forte ║
╚══════════════════════════════════════════════╝
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os, random
from datetime import datetime, timedelta, timezone
from collections import deque
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)

FUSO_BR = timezone(timedelta(hours=-3))

FILOSOFIA_SAMURAI = [
    "⚔️ A vitória começa na execução perfeita, não no resultado.",
    "🎯 O objetivo é o trade certo, não o dinheiro.",
    "🧘 Aceite a perda como parte do caminho do guerreiro.",
    "🐉 O mercado é um oponente vivo. Respeite-o.",
    "🕯️ Cada vela é uma batalha. Cada dia, uma guerra.",
    "⏳ Paciência é arma. Espere a confirmação.",
    "🌊 A tendência é sua amiga. Não a desafie.",
    "🛡️ O stop é o escudo do samurai. Use-o com honra.",
    "📚 O verdadeiro guerreiro estuda seus erros.",
    "🧠 Mente vazia, espírito pronto. Sem emoção.",
    "🔥 Paixão pelo processo, não pelo resultado.",
    "⛩️ Disciplina é o alicerce do trader samurai.",
    "⚡ O momento da execução é tudo. Hesitação é derrota.",
    "🏔️ A montanha do lucro se conquista com paciência.",
    "🌅 Cada amanhecer traz uma nova oportunidade de batalha."
]

def get_filosofia():
    return random.choice(FILOSOFIA_SAMURAI)

class C:
    G='\033[92m';Y='\033[93m';R='\033[91m';C='\033[96m';W='\033[97m';B='\033[1m';E='\033[0m';GOLD='\033[38;5;220m'

def clear(): os.system('clear 2>/dev/null || cls 2>/dev/null')

def banner():
    clear()
    print(f"{C.GOLD}{C.B}╔══════════════════════════════════════════════╗")
    print(f"║   ⚛️  Q U A N T U M   I A   M 5           ║")
    print(f"║   🧠 Máxima Assertividade | 🔥 65%+        ║")
    print(f"║   🎯 65% Taxa Mínima | 🛡️ Filtro Pavio    ║")
    print(f"║   📐 Filtro Tendência | Super 5/3 + Last   ║")
    print(f"║   ⏱️ 10min entre sinais | 🚫 Bloqueio Vela Forte ║")
    print(f"╚══════════════════════════════════════════════╝{C.E}")

CONFIG_FILE="config_quantum_m5.json"

def carregar_config():
    cloud_token = os.environ.get('TELEGRAM_TOKEN')
    cloud_chat = os.environ.get('TELEGRAM_CHAT_ID')
    cloud_email = os.environ.get('IQ_EMAIL')
    cloud_senha = os.environ.get('IQ_SENHA')
    
    if cloud_token and cloud_chat and cloud_email and cloud_senha:
        banner()
        print(f"\n{C.G}✅ Modo CLOUD detectado!{C.E}\n")
        return {"token": cloud_token, "chat": cloud_chat, "email": cloud_email, "senha": cloud_senha}
    
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE) as f: cfg=json.load(f)
        if 'token' not in cfg: Path(CONFIG_FILE).unlink();return carregar_config()
        banner();print(f"\n{C.G}✅ Config carregada!{C.E}\n");return cfg
    
    banner()
    try:
        cfg={
            "token":input(f"{C.G}Token Telegram: {C.E}").strip(),
            "chat":input(f"{C.G}Chat ID: {C.E}").strip(),
            "email":input(f"\n{C.G}Email IQ: {C.E}").strip(),
            "senha":input(f"{C.G}Senha IQ: {C.E}").strip()
        }
    except (EOFError, KeyboardInterrupt):
        print(f"\n{C.R}❌ Configure as variáveis de ambiente!{C.E}")
        sys.exit(1)
    
    with open(CONFIG_FILE,'w') as f: json.dump(cfg,f,indent=2)
    banner();print(f"\n{C.G}✅ Salvo!{C.E}\n");return cfg

cfg=carregar_config()
TOKEN=cfg['token'];CHAT=cfg['chat'];EMAIL=cfg['email'];SENHA=cfg['senha']

from iqoptionapi.stable_api import IQ_Option

ATIVOS_OTC={
    "EURUSD":"EURUSD-OTC",
    "GBPUSD":"GBPUSD-OTC",
    "EURGBP":"EURGBP-OTC",
    "EURJPY":"EURJPY-OTC"
}

class Placar:
    def __init__(self):self.w=0;self.l=0;self.g1=0;self.s=deque(maxlen=20);self.ops=[]
    def win(self,g=0):
        if g==0:self.w+=1;self.s.append('🟢');return"✅ WIN"
        else:self.g1+=1;self.s.append('🟡');return"✅ WIN GALE 1"
    def loss(self):self.l+=1;self.s.append('🔴');return"❌ LOSS"
    def registrar(self,ativo,direcao,conf,resultado,is_gale=False):
        agora=datetime.now(FUSO_BR);hora=agora.strftime('%H:%M')
        sufixo="¹" if is_gale else "";emoji="✅️" if "WIN" in resultado else "🔴"
        self.ops.append(f"M5 {ativo}-OTC {direcao} {hora} {emoji}{sufixo}")
    def zerar(self):self.w=0;self.l=0;self.g1=0;self.s.clear();self.ops.clear()

class Telegram:
    def __init__(self,t,c):self.u=f"https://api.telegram.org/bot{t}";self.c=c
    def send(self,txt):
        try:requests.post(f"{self.u}/sendMessage",json={"chat_id":self.c,"text":txt,"parse_mode":"Markdown"},timeout=5)
        except:pass

# ═══════════════════════════════════════════
# 🧠 CATALOGADOR INTELIGENTE
# ═══════════════════════════════════════════
class CatalogadorInteligente:
    def __init__(self):
        self.performance = {}
        self.combinacao_atual = None
        self.sinais_na_combinacao = 0
        self.max_sinais_por_combinacao = 1
        self.taxa_minima = 65
        self.min_operacoes = 5
        self.total_operacoes = 0
        self.ultimo_relatorio = 0
        
    def registrar(self, estrategia, par, venceu):
        chave = f"{estrategia}|{par}"
        if chave not in self.performance:
            self.performance[chave] = {'wins': 0, 'losses': 0, 'total': 0, 'estrategia': estrategia, 'par': par}
        self.performance[chave]['total'] += 1
        if venceu: self.performance[chave]['wins'] += 1
        else: self.performance[chave]['losses'] += 1
        self.total_operacoes += 1
    
    def get_taxa(self, estrategia, par):
        chave = f"{estrategia}|{par}"
        if chave in self.performance:
            p = self.performance[chave]
            return round((p['wins']/p['total'])*100, 1) if p['total'] > 0 else 0
        return 0
    
    def get_melhores(self, min_ops=5):
        melhores = []
        for chave, p in self.performance.items():
            if p['total'] >= min_ops:
                taxa = (p['wins']/p['total'])*100
                if taxa >= self.taxa_minima:
                    melhores.append({
                        'estrategia': p['estrategia'],
                        'par': p['par'],
                        'taxa': round(taxa, 1),
                        'total': p['total'],
                        'wins': p['wins'],
                        'losses': p['losses']
                    })
        melhores.sort(key=lambda x: x['taxa'], reverse=True)
        return melhores
    
    def escolher_melhor(self):
        melhores = self.get_melhores(self.min_operacoes)
        return melhores[0] if melhores else None
    
    def precisa_trocar(self):
        if not self.combinacao_atual: return True
        if self.sinais_na_combinacao >= self.max_sinais_por_combinacao: return True
        taxa_atual = self.get_taxa(self.combinacao_atual['estrategia'], self.combinacao_atual['par'])
        if taxa_atual < self.taxa_minima: return True
        melhor = self.escolher_melhor()
        if melhor and melhor['taxa'] > taxa_atual + 5: return True
        return False
    
    def atualizar_combinacao(self):
        if self.precisa_trocar():
            melhor = self.escolher_melhor()
            if melhor:
                self.combinacao_atual = {'estrategia': melhor['estrategia'], 'par': melhor['par'], 'taxa': melhor['taxa']}
                self.sinais_na_combinacao = 0
                return True, melhor
        return False, self.combinacao_atual
    
    def get_relatorio(self):
        melhores = self.get_melhores(2)
        if not melhores: return None
        msg = "📊 *CATALOGADOR INTELIGENTE M5*\n"
        msg += f"📈 Total: {self.total_operacoes} operações\n"
        if self.combinacao_atual:
            msg += f"🎯 *Atual:* {self.combinacao_atual['estrategia']} em {self.combinacao_atual['par']} ({self.combinacao_atual['taxa']}%)\n"
        msg += f"\n🏆 *Top Combinações:*\n"
        for i, m in enumerate(melhores[:6], 1):
            emoji = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else "📊"
            msg += f"{emoji} {m['estrategia']} | {m['par']}\n   {m['taxa']}% | {m['wins']}W/{m['losses']}L ({m['total']} ops)\n"
        return msg

# ═══════════════════════════════════════════
# 📊 FILTRO DE TENDÊNCIA AVANÇADO
# ═══════════════════════════════════════════
class FiltroTendencia:
    def __init__(self):
        self.forca_minima = 0.0002
        
    def analisar_tendencia(self, velas):
        if len(velas) < 20:
            return "NEUTRA", 0
        precos = [v['close'] for v in velas]
        ema9 = np.mean(precos[-9:])
        ema21 = np.mean(precos[-21:])
        high = [v['high'] for v in velas]
        low = [v['low'] for v in velas]
        plus_dm, minus_dm, tr = [], [], []
        for i in range(1, min(14, len(velas))):
            up_move = high[-i] - high[-i-1]
            down_move = low[-i-1] - low[-i]
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
            true_range = max(high[-i]-low[-i], abs(high[-i]-precos[-i-1]), abs(low[-i]-precos[-i-1]))
            tr.append(true_range)
        if not tr: return "NEUTRA", 0
        atr = np.mean(tr)
        plus_di = (np.mean(plus_dm)/atr*100) if atr>0 and plus_dm else 0
        minus_di = (np.mean(minus_dm)/atr*100) if atr>0 and minus_dm else 0
        dx = abs(plus_di - minus_di)/(plus_di + minus_di)*100 if (plus_di+minus_di)>0 else 0
        if ema9 > ema21*(1+self.forca_minima) and plus_di > minus_di:
            tendencia = "ALTA FORTE 📈" if dx>25 else "ALTA 📈"
        elif ema9 < ema21*(1-self.forca_minima) and minus_di > plus_di:
            tendencia = "BAIXA FORTE 📉" if dx>25 else "BAIXA 📉"
        else:
            tendencia = "NEUTRA ➡️"
            dx = min(dx, 20)
        return tendencia, dx
    
    def sinal_alinhado(self, direcao_sinal, tendencia, forca):
        if "NEUTRA" in tendencia:
            return True
        if direcao_sinal == "CALL":
            if "ALTA" in tendencia:
                return True
            elif "BAIXA" in tendencia and forca < 25:
                return True
            else:
                return False
        else:
            if "BAIXA" in tendencia:
                return True
            elif "ALTA" in tendencia and forca < 25:
                return True
            else:
                return False

# ═══════════════════════════════════════════
# 📊 ESTRATÉGIAS M5 (SUPER 5, SUPER 3, LAST OF FIVE)
# ═══════════════════════════════════════════

class Super5:
    """SUPER 5 - M5 (Maioria/Minoria)"""
    def __init__(self, modo='minoria'):
        self.modo = modo
        self.tamanho_quadrante = 6
        self.velas_analise = 3
        
    def analisar(self, v):
        try:
            if len(v) < self.tamanho_quadrante * 2:
                return None, 0
            ultimas_velas = list(v[-self.tamanho_quadrante*2:])
            quadrante_anterior = ultimas_velas[-self.tamanho_quadrante:]
            velas_analise = quadrante_anterior[-self.velas_analise:]
            calls = sum(1 for x in velas_analise if x['close'] > x['open'])
            puts = self.velas_analise - calls
            if self.modo == 'minoria':
                alvo = 'CALL' if calls < puts else 'PUT'
            else:
                alvo = 'CALL' if calls > puts else 'PUT'
            diff = abs(calls - puts)
            conf = 50 + diff * 10
            conf = min(conf, 85)
            return alvo, conf
        except:
            return None, 0

class Super3:
    """SUPER 3 - M5 (Maioria/Minoria)"""
    def __init__(self, modo='minoria'):
        self.modo = modo
        self.tamanho_quadrante = 3
        
    def analisar(self, v):
        try:
            if len(v) < self.tamanho_quadrante * 2:
                return None, 0
            ultimas_velas = list(v[-self.tamanho_quadrante*2:])
            quadrante_anterior = ultimas_velas[-self.tamanho_quadrante:]
            calls = sum(1 for x in quadrante_anterior if x['close'] > x['open'])
            puts = self.tamanho_quadrante - calls
            if self.modo == 'minoria':
                alvo = 'CALL' if calls < puts else 'PUT'
            else:
                alvo = 'CALL' if calls > puts else 'PUT'
            diff = abs(calls - puts)
            conf = 50 + diff * 15
            conf = min(conf, 85)
            return alvo, conf
        except:
            return None, 0

class LastOfFive:
    """LAST OF FIVE - M5 (Maioria/Minoria)"""
    def __init__(self, modo='minoria'):
        self.modo = modo
        self.tamanho_quadrante = 6
        self.velas_analise = 5
        
    def analisar(self, v):
        try:
            if len(v) < self.tamanho_quadrante * 2:
                return None, 0
            ultimas_velas = list(v[-self.tamanho_quadrante*2:])
            quadrante_anterior = ultimas_velas[-self.tamanho_quadrante:]
            velas_analise = quadrante_anterior[-self.velas_analise:]
            calls = sum(1 for x in velas_analise if x['close'] > x['open'])
            puts = self.velas_analise - calls
            if self.modo == 'minoria':
                alvo = 'CALL' if calls < puts else 'PUT'
            else:
                alvo = 'CALL' if calls > puts else 'PUT'
            diff = abs(calls - puts)
            conf = 50 + diff * 8
            conf = min(conf, 85)
            return alvo, conf
        except:
            return None, 0

# ═══════════════════════════════════════════
# ⚛️ QUANTUM IA - M5
# ═══════════════════════════════════════════
class QuantumIA:
    def __init__(self):
        self.estrategias=[
            ('📊 Super 5 Minoria', Super5(modo='minoria')),
            ('📊 Super 5 Maioria', Super5(modo='maioria')),
            ('📊 Super 3 Minoria', Super3(modo='minoria')),
            ('📊 Super 3 Maioria', Super3(modo='maioria')),
            ('📊 Last of Five Minoria', LastOfFive(modo='minoria')),
            ('📊 Last of Five Maioria', LastOfFive(modo='maioria')),
        ]
        self.catalogador=CatalogadorInteligente()
        self.filtro_tendencia=FiltroTendencia()
        self.sinais_bloqueados_pavio=0
        self.sinais_bloqueados_tendencia=0
        self.sinais_bloqueados_vela_forte=0

    def _pavio_ok(self, velas, direcao):
        if len(velas) < 2: return True
        va, vb = velas[-1], velas[-2]
        corpo_va = abs(va['close'] - va['open'])
        if corpo_va == 0: return False
        if direcao == 'CALL':
            if va['high'] - max(va['close'], va['open']) > corpo_va * 0.4: return False
        else:
            if min(va['close'], va['open']) - va['low'] > corpo_va * 0.4: return False
        corpo_vb = abs(vb['close'] - vb['open'])
        if corpo_vb > 0:
            if direcao == 'CALL':
                if vb['high'] - max(vb['close'], vb['open']) > corpo_vb * 0.5: return False
            else:
                if min(vb['close'], vb['open']) - vb['low'] > corpo_vb * 0.5: return False
        range_total = va['high'] - va['low']
        if range_total > 0 and corpo_va < range_total * 0.3: return False
        return True
    
    def _vela_forte_ok(self, velas):
        if len(velas) < 15: return True
        ranges = [velas[i]['high'] - velas[i]['low'] for i in range(-14, 0)]
        atr = np.mean(ranges)
        ultimo_range = velas[-1]['high'] - velas[-1]['low']
        if ultimo_range > atr * 2.0:
            return False
        return True
    
    def _tendencia_ok(self, velas, direcao, par):
        tendencia, forca = self.filtro_tendencia.analisar_tendencia(velas)
        alinhado = self.filtro_tendencia.sinal_alinhado(direcao, tendencia, forca)
        if not alinhado:
            print(f"  🚫 Bloqueado M5: {direcao} em {par} | Tendência: {tendencia} ({forca:.0f}%)")
        return alinhado

    def obter_sinal(self, velas_dict, bloqueados):
        trocou, combinacao = self.catalogador.atualizar_combinacao()
        if trocou and combinacao:
            print(f"  🧠 M5 Nova combinação: {combinacao['estrategia']} em {combinacao['par']} ({combinacao['taxa']}%)")
        # Tenta usar a combinação preferida
        if combinacao:
            par = combinacao['par']; est_nome = combinacao['estrategia']
            if par in velas_dict and par not in bloqueados and len(velas_dict[par]) >= 30:
                for nome, est in self.estrategias:
                    if nome == est_nome:
                        d, c = est.analisar(velas_dict[par])
                        if d and c >= 65:
                            if self._pavio_ok(velas_dict[par], d) and self._vela_forte_ok(velas_dict[par]) and self._tendencia_ok(velas_dict[par], d, par):
                                self.catalogador.sinais_na_combinacao += 1
                                tendencia, _ = self.filtro_tendencia.analisar_tendencia(velas_dict[par])
                                return {'ativo': par, 'direcao': d, 'confianca': c, 'estrategia': nome, 'tendencia': tendencia}
        # Fallback: busca qualquer sinal
        melhor = None; melhor_score = 0
        for nome_par, velas in velas_dict.items():
            if nome_par in bloqueados: continue
            if len(velas) < 30: continue
            tendencia, forca = self.filtro_tendencia.analisar_tendencia(velas)
            for nome_est, est in self.estrategias:
                try:
                    d, c = est.analisar(velas)
                    if d and c >= 65 and self._pavio_ok(velas, d) and self._vela_forte_ok(velas) and self.filtro_tendencia.sinal_alinhado(d, tendencia, forca):
                        score = c
                        if ("FORTE" in tendencia and 
                            ((d == "CALL" and "ALTA" in tendencia) or 
                             (d == "PUT" and "BAIXA" in tendencia))):
                            score += 10
                        taxa = self.catalogador.get_taxa(nome_est, nome_par)
                        if taxa > 60: score += taxa * 0.5
                        if score > melhor_score:
                            melhor_score = score
                            melhor = {'ativo': nome_par, 'direcao': d, 'confianca': c, 'estrategia': nome_est, 'tendencia': tendencia}
                except: pass
        return melhor

# ═══════════════════════════════════════════
# 👨‍🏫 TRADER PROFESSOR
# ═══════════════════════════════════════════
class TraderProfessor:
    def __init__(self):
        self.historico=deque(maxlen=50)
        self.stats_pares={nome:{'wins':0,'losses':0,'total':0,'taxa':0} for nome in ATIVOS_OTC}
        self.tendencias={nome:"NEUTRA" for nome in ATIVOS_OTC}
        self.losses=deque(maxlen=50)
        self.filtro_tendencia=FiltroTendencia()
    
    def atualizar_stats(self,ativo,resultado):
        if ativo in self.stats_pares:
            self.stats_pares[ativo]['total']+=1
            if resultado=='win':self.stats_pares[ativo]['wins']+=1
            else:self.stats_pares[ativo]['losses']+=1
            t=self.stats_pares[ativo]['total'];w=self.stats_pares[ativo]['wins']
            self.stats_pares[ativo]['taxa']=round((w/t)*100,1) if t>0 else 0
    
    def atualizar_dados(self,velas_dict):
        for nome,velas in velas_dict.items():
            if len(velas)>=20:
                tendencia, forca = self.filtro_tendencia.analisar_tendencia(velas)
                self.tendencias[nome] = f"{tendencia} ({forca:.0f}%)"
    
    def ler_grafico(self,velas,direcao):
        if len(velas)<5:return"Poucas velas",[],True
        obs=[];v=velas[-1];v1=velas[-2]
        corpo=abs(v['close']-v['open']);range_total=v['high']-v['low']
        pavio_sup=v['high']-max(v['close'],v['open']);pavio_inf=min(v['close'],v['open'])-v['low']
        pavio_ok=True
        if direcao=='CALL':
            if pavio_inf>corpo*2 and pavio_sup<corpo*0.3:obs.append("🔨 Martelo")
            elif corpo>abs(v1['close']-v1['open'])*1.5 and v['close']>v1['open']:obs.append("📈 Engolfo alta")
            if pavio_sup>corpo*0.6:obs.append("⚠️ Pavio superior");pavio_ok=False
        else:
            if pavio_sup>corpo*2 and pavio_inf<corpo*0.3:obs.append("💫 Estrela cadente")
            elif corpo>abs(v1['close']-v1['open'])*1.5 and v['close']<v1['open']:obs.append("📉 Engolfo baixa")
            if pavio_inf>corpo*0.6:obs.append("⚠️ Pavio inferior");pavio_ok=False
        if corpo>range_total*0.6:obs.append("💪 Vela forte")
        precos=[x['close'] for x in velas]
        altas=sum(1 for i in range(-5,0) if i>=-len(precos)+1 and precos[i]>precos[i-1])
        if altas>=4:obs.append("📈 Tendência alta")
        elif altas<=1:obs.append("📉 Tendência baixa")
        else:obs.append("↔️ Sem direção")
        if not obs:obs.append("✅ Setup neutro")
        return" | ".join(obs),obs,pavio_ok
    
    def explicar_entrada(self,sinal,velas):
        ativo=sinal['ativo'];direcao=sinal['direcao'];conf=sinal.get('confianca',0)
        est=sinal.get('estrategia','N/A')
        leitura,obs,pavio_ok=self.ler_grafico(velas,direcao)
        tendencia=self.tendencias.get(ativo,'NEUTRA')
        alinhamento = "✅ ALINHADO" if (
            (direcao == "CALL" and "ALTA" in tendencia) or 
            (direcao == "PUT" and "BAIXA" in tendencia) or
            "NEUTRA" in tendencia
        ) else "⚠️ CONTRA TENDÊNCIA"
        filosofia=get_filosofia()
        return f"""👨‍🏫 *ANÁLISE DO TRADER M5*

📊 *Mercado:* {tendencia}
📐 *Alinhamento:* {alinhamento}
👁️ *Gráfico:* {leitura}
🧠 *Estratégia:* {est}
🎯 *Decisão:* {direcao} com {conf:.0f}% de confiança
⚔️ _{filosofia}_"""
    
    def explicar_loss(self,sinal,velas):
        ativo=sinal['ativo'];direcao=sinal['direcao'];conf=sinal.get('confianca',0)
        leitura,obs,pavio_ok=self.ler_grafico(velas,direcao)
        causas=[];v=velas[-1];corpo=abs(v['close']-v['open'])
        if corpo>0:
            if direcao=='CALL' and(v['high']-max(v['close'],v['open']))/corpo>0.6:causas.append("🕯️ Pavio superior grande")
            elif direcao=='PUT' and(min(v['close'],v['open'])-v['low'])/corpo>0.6:causas.append("🕯️ Pavio inferior grande")
        tendencia=self.tendencias.get(ativo,'NEUTRA')
        if direcao=='CALL' and 'BAIXA' in tendencia:causas.append("📉 Contra tendência de baixa")
        elif direcao=='PUT' and 'ALTA' in tendencia:causas.append("📈 Contra tendência de alta")
        if conf<65:causas.append("📊 Confiança baixa (<65%)")
        if not causas:causas.append("🎲 Movimento aleatório")
        self.losses.append({'ativo':ativo,'direcao':direcao,'confianca':conf,'causas':causas,'hora':datetime.now(FUSO_BR).hour})
        licao="Seguir o plano"
        if 'pavio' in str(causas).lower():licao="Verificar pavios antes de entrar"
        elif 'tendência' in str(causas).lower():licao="NÃO operar contra tendência - aguardar alinhamento"
        elif 'confiança' in str(causas).lower():licao="Esperar confiança mais alta (65%+)"
        filosofia=get_filosofia()
        return f"""🧠 *ANÁLISE DO LOSS M5*

🔴 {ativo}-OTC {direcao} | {conf:.0f}%
📊 Tendência: {tendencia}
🚫 *Causas:* {', '.join(causas)}
📚 *Lição:* {licao}
⚔️ _{filosofia}_"""
    
    def registrar(self,resultado):self.historico.append(1 if resultado=='win' else 0)

# ═══════════════════════════════════════════
# IQ API (Timeframe 300s = 5 minutos)
# ═══════════════════════════════════════════
class IQAPI:
    def __init__(self,e,s,a):self.e=e;self.s=s;self.a=a;self.api=None;self.velas={nome:deque(maxlen=100) for nome in a};self.ok=False;self.erros=0
    def conectar(self):
        for t in range(5):
            try:
                if self.api:
                    try:self.api.close()
                    except:pass
                    time.sleep(2)
                self.api=IQ_Option(self.e,self.s);ok,_=self.api.connect()
                if ok:self.ok=True;self.erros=0;return True
                time.sleep(5*(t+1))
            except:time.sleep(5*(t+1))
        self.ok=False;return False
    def obter(self,ativo_id,qtd=80):
        for retry in range(3):
            if not self.ok and not self.conectar():return 0
            try:
                c=self.api.get_candles(ativo_id,300,qtd,time.time())  # 300 segundos = 5 min
                if c and len(c)>0:
                    nome=[k for k,v in self.a.items() if v==ativo_id][0];self.velas[nome].clear()
                    for x in c[-qtd:]:
                        if isinstance(x,dict):
                            try:self.velas[nome].append({'time':datetime.fromtimestamp(x.get('from',0),FUSO_BR),'open':float(x['open']),'high':float(x['max']),'low':float(x['min']),'close':float(x['close']),'volume':int(x.get('volume',0))})
                            except:pass
                    return len(c)
            except:
                self.ok=False
                if retry<2:time.sleep(3);continue
        return 0
    def atualizar(self):
        if not self.ok:self.conectar()
        for n,i in self.a.items():
            try:self.obter(i)
            except:pass

# ═══════════════════════════════════════════
# BOT M5
# ═══════════════════════════════════════════
class Bot:
    def __init__(self):
        self.tg=Telegram(TOKEN,CHAT);self.m=QuantumIA();self.p=Placar();self.iq=IQAPI(EMAIL,SENHA,ATIVOS_OTC)
        self.professor=TraderProfessor()
        self.op=False;self.g=0;self.ult=0;self.sinais=0
        self.ultimo_dia=datetime.now(FUSO_BR).day;self.placar_enviado=False

    def _barra(self,pct):p=int(pct/10);return '█'*p+'░'*(10-p)

    def fechar_dia(self):
        agora=datetime.now(FUSO_BR);data=agora.strftime('%d/%m/%Y')
        dias={'Monday':'Segunda','Tuesday':'Terça','Wednesday':'Quarta','Thursday':'Quinta','Friday':'Sexta','Saturday':'Sábado','Sunday':'Domingo'}
        dia=dias.get(agora.strftime('%A'),'')
        w=self.p.w;g1=self.p.g1;l=self.p.l
        total_profit=w+g1;total_trades=total_profit+l
        tx=round((total_profit/total_trades)*100,1) if total_trades>0 else 0
        lucro=round(w*1.6+g1*0.4-l*5,2)
        lista_ops=""
        if self.p.ops:
            for op in self.p.ops[-50:]:lista_ops+=op+"\n"
        relatorio=self.m.catalogador.get_relatorio()
        msg=f"""📊 *PLACAR DIÁRIO M5*

🗓️ *{data} ({dia})*
⏰ {agora.strftime('%H:%M')}

┌──────────────────────────┐
│ ⚛️ QUANTUM IA M5        │
│ 🟢 Wins Diretos: {w}      │
│ 🟡 Gale 1: {g1}            │
│ 🔴 Losses: {l}            │
│ 📨 Total Sinais: {total_trades} │
│ 🎯 Assertividade: {tx}%   │
│ [{self._barra(tx)}]      │
│ 💰 Lucro: +R${lucro}      │
│ 🛡️ Pavios bloqueados: {self.m.sinais_bloqueados_pavio} │
│ 📊 Tendências bloqueadas: {self.m.sinais_bloqueados_tendencia} │
│ 🚫 Velas fortes bloqueadas: {self.m.sinais_bloqueados_vela_forte} │
└──────────────────────────┘

📋 *Operações do Dia:*
{lista_ops if lista_ops else 'Nenhuma operação'}

⚔️ _{get_filosofia()}_

🔄 *Placar zerado!*"""
        self.tg.send(msg)
        if relatorio:self.tg.send(relatorio)
        print(f"\n{C.GOLD}╔══════════════════════════════╗{C.E}")
        print(f"{C.GOLD}║ 📊 PLACAR DIÁRIO M5        ║{C.E}")
        print(f"{C.GOLD}║ 🟢{w}W 🟡{g1}G1 🔴{l}L 🎯{tx}% 💰+R${lucro} ║{C.E}")
        print(f"{C.GOLD}╚══════════════════════════════╝{C.E}\n")
        self.p.zerar();self.sinais=0;self.m.sinais_bloqueados_pavio=0;self.m.sinais_bloqueados_tendencia=0;self.m.sinais_bloqueados_vela_forte=0
        print(f"  {C.G}🔄 Placar ZERADO! Novo dia!{C.E}\n")

    def fmt_sinal(self,s):
        # Horário de entrada no próximo candle de 5 min
        agora = datetime.now(FUSO_BR)
        minutos_offset = 5
        next_candle = agora.replace(second=0, microsecond=0)
        while next_candle.minute % minutos_offset != 0:
            next_candle += timedelta(minutes=1)
        if next_candle <= agora:
            next_candle += timedelta(minutes=minutos_offset)
        he = next_candle.strftime('%H:%M')
        e="🟢" if s['direcao']=='CALL' else "🔴"
        est=s.get('estrategia','N/A')
        tendencia=s.get('tendencia','NEUTRA')
        return f"""⚛️ SINAL M5 ⚛️

⏰ Horário: {he}
💰 Ativo: {s['ativo']}-OTC
📈 Direção: {s['direcao']} {e}
⌛️ Expiração: M5
📊 Confiança: {s['confianca']:.0f}%
🧠 Estratégia: {est}
📐 Tendência: {tendencia}

⚠️ Entrar somente no horário marcado.
🔄 1 recuperação (Gale 1)!"""

    def fmt_corr(self,r,s):
        total_profit=self.p.w+self.p.g1
        total_trades=total_profit+self.p.l
        tx=round((total_profit/total_trades)*100,1) if total_trades>0 else 0
        return f"""{r}
📊 {s['ativo']}-OTC | {s['direcao']} {'🟢' if s['direcao']=='CALL' else '🔴'}
📊 Placar M5: 🟢{self.p.w}W 🟡{self.p.g1}G1 🔴{self.p.l}L
🎯 Assertividade: {tx}%"""

    def bateu(self,d,p,v):return v['high']>p if d=='CALL' else v['low']<p

    async def esperar_entrada(self):
        # Aguarda até o início do próximo candle de 5 min
        agora = datetime.now(FUSO_BR)
        next_candle = agora.replace(second=0, microsecond=0)
        while next_candle.minute % 5 != 0:
            next_candle += timedelta(minutes=1)
        if next_candle <= agora:
            next_candle += timedelta(minutes=5)
        espera = (next_candle - agora).total_seconds()
        if espera > 0:
            await asyncio.sleep(espera)
        self.iq.atualizar()

    async def corrigir(self,sinal):
        at=sinal['ativo'];d=sinal['direcao'];conf=sinal.get('confianca',0)
        estrategia_nome=sinal.get('estrategia','Desconhecida')
        try:
            await self.esperar_entrada()
            v=self.iq.velas[at]
            if len(v)<2:self.op=False;return
            pc=v[-1]['open'];hora=v[-1]['time'].strftime('%H:%M')
            print(f"\n  ⚛️ M5 {at}-OTC {d} | {estrategia_nome} | OPEN:{pc:.5f} | Vela:{hora}")
            # Aguarda quase 5 min (300s) para ver resultado
            await asyncio.sleep(290)
            self.iq.atualizar()
            v=self.iq.velas[at]
            if len(v)>0 and self.bateu(d,pc,v[-1]):
                r=self.p.win(0);print(f"  ✅ {r}");self.p.registrar(at,d,conf,"WIN")
                self.tg.send(self.fmt_corr(r,sinal))
                self.professor.registrar('win');self.professor.atualizar_stats(at,'win')
                self.m.catalogador.registrar(estrategia_nome,at,True)
                self.op=False;return
            print(f"  ❌ Principal")
            # Gale 1
            self.g=1
            await self.esperar_entrada()  # próximo candle de 5 min para gale
            v=self.iq.velas[at]
            if len(v)>0:
                pg=v[-1]['open']
                print(f"  🔄 GALE 1 M5 | OPEN:{pg:.5f}")
                await asyncio.sleep(290)
                self.iq.atualizar()
                v=self.iq.velas[at]
                if len(v)>0 and self.bateu(d,pg,v[-1]):
                    r=self.p.win(1);print(f"  ✅ {r}");self.p.registrar(at,d,conf,"WIN GALE 1",is_gale=True)
                    self.tg.send(self.fmt_corr(r,sinal))
                    self.professor.registrar('win');self.professor.atualizar_stats(at,'win')
                    self.m.catalogador.registrar(estrategia_nome,at,True)
                    self.op=False;return
            r=self.p.loss();print(f"  🔴 {r}");self.p.registrar(at,d,conf,"LOSS")
            self.tg.send(self.fmt_corr(r,sinal))
            self.professor.registrar('loss');self.professor.atualizar_stats(at,'loss')
            self.m.catalogador.registrar(estrategia_nome,at,False)
            explicacao=self.professor.explicar_loss(sinal,self.iq.velas[at])
            self.tg.send(explicacao)
            print(f"  🧠 Loss explicado!")
            self.op=False
        except Exception as e:print(f"  ❌ {e}");self.op=False

    async def run(self):
        banner()
        print(f"\n  ⚛️ Iniciando Quantum IA M5...\n")
        print(f"  🕐 Horário Brasil: {datetime.now(FUSO_BR).strftime('%H:%M:%S')}\n")
        print(f"  🔥 65% Taxa Mínima | 🔥 65% Confiança | 🛡️ Filtros | ⏱️ 10min entre sinais\n")
        if not self.iq.conectar():print(f"  ❌ Falha conexão!");return
        self.iq.atualizar()
        self.ultimo_dia=datetime.now(FUSO_BR).day
        print(f"\n  ✅ QUANTUM IA M5 | 🎯 Melhor Combinação | 4 Pares\n")
        self.tg.send(f"🔥 *QUANTUM IA M5*\n👨‍🏫 Trader Professor\n📊 6 Estratégias (Super 5/3 + Last)\n🎯 Taxa Mínima: 65%\n🔥 Confiança Mínima: 65%\n⏱️ Intervalo: 10min\n🛡️ Filtros: Pavio, Tendência, Vela Forte\n⏰ {datetime.now(FUSO_BR).strftime('%H:%M:%S')}")

        while True:
            try:
                agora=datetime.now(FUSO_BR)
                if agora.hour==23 and agora.minute==59 and not self.placar_enviado:
                    self.fechar_dia();self.placar_enviado=True
                if agora.day!=self.ultimo_dia:self.ultimo_dia=agora.day;self.placar_enviado=False
                if agora.second in[0,30]:
                    try:self.iq.atualizar();self.professor.atualizar_dados(self.iq.velas)
                    except:self.iq.ok=False
                if not self.op:
                    try:
                        sinal=self.m.obter_sinal(self.iq.velas,[])
                        if sinal and time.time()-self.ult>600:  # 10 minutos entre sinais
                            self.op=True;self.sinais+=1
                            est=sinal.get('estrategia','N/A')
                            print(f"\n⚛️ M5 #{self.sinais} {sinal['ativo']}-OTC {sinal['direcao']} | {sinal['confianca']:.0f}% | 🧠 {est}")
                            self.tg.send(self.fmt_sinal(sinal))
                            explicacao=self.professor.explicar_entrada(sinal,self.iq.velas[sinal['ativo']])
                            self.tg.send(explicacao)
                            self.ult=time.time()
                            asyncio.create_task(self.corrigir(sinal))
                    except:pass
                if self.m.catalogador.total_operacoes>0 and self.m.catalogador.total_operacoes%10==0 and self.m.catalogador.total_operacoes!=self.m.catalogador.ultimo_relatorio:
                    relatorio=self.m.catalogador.get_relatorio()
                    if relatorio:
                        self.tg.send(relatorio)
                        self.m.catalogador.ultimo_relatorio=self.m.catalogador.total_operacoes
                if agora.second in[0,30]:
                    try:
                        w,l,g1=self.p.w,self.p.l,self.p.g1
                        total_profit=w+g1;total_trades=total_profit+l
                        tx=round((total_profit/total_trades)*100,1) if total_trades>0 else 0
                        lucro=round(w*1.6+g1*0.4-l*5,2)
                        comb=self.m.catalogador.combinacao_atual
                        info_comb=f" | 🧠 {comb['estrategia']} em {comb['par']}" if comb else ""
                        print(f"{C.GOLD}┌──────────────────────────────────────────────────────┐{C.E}")
                        print(f"{C.GOLD}│{C.E} M5 ⏰ {agora.strftime('%H:%M:%S')} | 📨{self.sinais} | 🟢{w}W 🟡{g1}G1 🔴{l}L 🎯{tx}% | 💰+R${lucro} | 🛡️{self.m.sinais_bloqueados_pavio} | 📊{self.m.sinais_bloqueados_tendencia} | 🚫{self.m.sinais_bloqueados_vela_forte}{info_comb}")
                        print(f"{C.GOLD}│{C.E} 🔥 65%+ | ⚔️ {get_filosofia()}")
                        print(f"{C.GOLD}└──────────────────────────────────────────────────────┘{C.E}")
                    except:pass
                await asyncio.sleep(3)
            except KeyboardInterrupt:
                clear();w,l,g1=self.p.w,self.p.l,self.p.g1
                total_profit=w+g1;total_trades=total_profit+l
                tx=round((total_profit/total_trades)*100,1) if total_trades>0 else 0
                lucro=round(w*1.6+g1*0.4-l*5,2)
                print(f"\n👋 M5 🟢{w}W 🟡{g1}G1 🔴{l}L | 🎯{tx}% | 💰+R${lucro}\n")
                self.tg.send(f"⚠️ *M5 Desligado*\n🟢{w}W 🟡{g1}G1 🔴{l}L\n🎯{tx}%\n💰+R${lucro}")
                if self.iq.api:
                    try:self.iq.api.close()
                    except:pass
                break
            except Exception as e:
                print(f"  {C.R}❌ M5 erro: {str(e)[:40]}{C.E}");self.iq.ok=False;await asyncio.sleep(5)

if __name__=="__main__":
    asyncio.run(Bot().run())
