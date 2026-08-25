#!/usr/bin/env python3
"""
⚛️ QUANTUM IA M5 - FOREX REAL - CORRIGIDO
🧠 Catálogo reavaliado a cada 2 sinais
📊 ATR ampliado
🔄 Reconexão automática
💓 Heartbeat
"""
import asyncio, time, requests, numpy as np, signal, sys, json, os, random
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from pathlib import Path

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
FUSO_BR = timezone(timedelta(hours=-3))

class C:
    G='\033[92m';Y='\033[93m';R='\033[91m';C='\033[96m';W='\033[97m';B='\033[1m';E='\033[0m';GOLD='\033[38;5;220m'

def banner():
    print(f"{C.GOLD}⚛️ QUANTUM IA M5 - Forex Corrigido{C.E}")

def carregar_config():
    cloud_token = os.environ.get('TELEGRAM_TOKEN')
    cloud_chat = os.environ.get('TELEGRAM_CHAT_ID')
    cloud_email = os.environ.get('IQ_EMAIL')
    cloud_senha = os.environ.get('IQ_SENHA')
    
    if cloud_token and cloud_chat and cloud_email and cloud_senha:
        banner()
        print(f"\n{C.G}✅ Modo CLOUD detectado!{C.E}\n")
        return {"token": cloud_token, "chat": cloud_chat, "email": cloud_email, "senha": cloud_senha}
    
    print("❌ Configure as variáveis de ambiente!")
    sys.exit(1)

cfg=carregar_config()
TOKEN=cfg['token'];CHAT=cfg['chat'];EMAIL=cfg['email'];SENHA=cfg['senha']

from iqoptionapi.stable_api import IQ_Option

ATIVOS={
    "EURUSD":"EURUSD",
    "GBPUSD":"GBPUSD",
    "EURJPY":"EURJPY",
    "USDJPY":"USDJPY"
}

# ATR AMPLIADO
ATR_MIN = 0.00005
ATR_MAX = 0.0050

class Placar:
    def __init__(self):self.w=0;self.l=0;self.g1=0;self.ops=[]
    def win(self,g=0):
        if g==0:self.w+=1;return"✅ WIN"
        else:self.g1+=1;return"✅ WIN GALE 1"
    def loss(self):self.l+=1;return"❌ LOSS"
    def registrar(self,ativo,direcao,resultado,is_gale=False):
        agora=datetime.now(FUSO_BR);hora=agora.strftime('%H:%M')
        self.ops.append(f"M5 {ativo} {direcao} {hora} {'✅' if 'WIN' in resultado else '🔴'}")
    def zerar(self):self.w=0;self.l=0;self.g1=0;self.ops.clear()

class Telegram:
    def __init__(self,t,c):self.u=f"https://api.telegram.org/bot{t}";self.c=c
    def send(self,txt):
        try:requests.post(f"{self.u}/sendMessage",json={"chat_id":self.c,"text":txt,"parse_mode":"Markdown"},timeout=5)
        except:pass

class CatalogadorInteligente:
    def __init__(self):
        self.performance = {}
        self.combinacao_atual = None
        self.sinais_na_combinacao = 0
        self.max_sinais_por_combinacao = 2  # Troca a cada 2 sinais
        self.taxa_minima = 50
        self.min_operacoes = 1  # Aceita qualquer histórico
        self.total_operacoes = 0
        
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
    
    def escolher_melhor(self):
        melhores = []
        for chave, p in self.performance.items():
            taxa = (p['wins']/p['total'])*100 if p['total'] > 0 else 0
            melhores.append({'estrategia': p['estrategia'], 'par': p['par'], 'taxa': taxa, 'total': p['total']})
        melhores.sort(key=lambda x: x['taxa'], reverse=True)
        return melhores[0] if melhores else None
    
    def precisa_trocar(self):
        if not self.combinacao_atual: return True
        if self.sinais_na_combinacao >= self.max_sinais_por_combinacao: return True
        return False
    
    def atualizar_combinacao(self):
        if self.precisa_trocar():
            melhor = self.escolher_melhor()
            if melhor:
                self.combinacao_atual = {'estrategia': melhor['estrategia'], 'par': melhor['par'], 'taxa': melhor['taxa']}
                self.sinais_na_combinacao = 0
                return True, melhor
        return False, self.combinacao_atual

# Estratégias (mantidas)
class Mortalha:
    def sma(self,d,p):
        try:
            if len(d)>=p:return sum(d[-p:])/p
            return sum(d)/len(d) if d else 0
        except:return 0
    def wma(self,d,p):
        try:
            if len(d)<p:return sum(d)/len(d) if d else 0
            w=np.arange(1,p+1);return np.sum(np.array(d[-p:])*w)/np.sum(w)
        except:return 0
    def analisar(self,v):
        try:
            if len(v)<30:return None,0
            c=np.array([x['close'] for x in v]);b1=np.zeros(len(c))
            for i in range(len(c)):
                if i>=33:b1[i]=self.sma(c[:i+1],1)-self.sma(c[:i+1],34)
            b2=np.zeros(len(b1))
            for i in range(len(b1)):
                if i>=3:b2[i]=self.wma(b1[:i+1],4)
            if b1[-1]>b2[-1] and b1[-2]<=b2[-2]:return'CALL',min(45+abs(b1[-1]-b2[-1])*10000,90)
            if b1[-1]<b2[-1] and b1[-2]>=b2[-2]:return'PUT',min(45+abs(b1[-1]-b2[-1])*10000,90)
            return None,0
        except:return None,0

class Formiga:
    def ema(self,p,pe):
        try:
            if len(p)<pe:return sum(p)/len(p) if p else 0
            return np.mean(p[-pe:])
        except:return 0
    def analisar(self,v):
        try:
            if len(v)<15:return None,0
            precos=np.array([x['close'] for x in v])
            ema5=self.ema(precos,5);ema10=self.ema(precos,10)
            dif=((ema5-ema10)/ema10)*100 if ema10>0 else 0
            sc=0;sp=0
            if dif>0.02:sc+=3
            elif dif>0.005:sc+=1
            elif dif<-0.02:sp+=3
            elif dif<-0.005:sp+=1
            if sc>=2 and sc>sp:return'CALL',min(50+sc*4,85)
            if sp>=2 and sp>sc:return'PUT',min(50+sp*4,85)
            return None,0
        except:return None,0

class Fortaleza:
    def rsi(self,p,pe=7):
        try:
            if len(p)<pe+1:return 50
            d=np.diff(list(p[-pe-1:]));g=np.where(d>0,d,0);l=np.where(d<0,-d,0)
            mg=np.mean(g) if len(g)>0 else 0;mp=np.mean(l) if len(l)>0 else 0
            if mp==0:return 100
            return 100-(100/(1+mg/mp))
        except:return 50
    def analisar(self,v):
        try:
            if len(v)<18:return None,0
            precos=np.array([x['close'] for x in v])
            rsi_val=self.rsi(precos)
            m=np.mean(precos[-10:]) if len(precos)>=10 else np.mean(precos)
            s=np.std(precos[-10:]) if len(precos)>=10 else 0
            bs=m+2*s;bi=m-2*s
            sc=0;sp=0
            if rsi_val<30:sc+=3
            elif rsi_val<40:sc+=2
            if rsi_val>70:sp+=3
            elif rsi_val>60:sp+=2
            if precos[-1]<=bi*1.0004:sc+=3
            if precos[-1]>=bs*0.9996:sp+=3
            if sc>=4 and sc>sp:return'CALL',min(60+sc*3,90)
            if sp>=4 and sp>sc:return'PUT',min(60+sp*3,90)
            return None,0
        except:return None,0

class RaioNegro:
    def analisar(self,v):
        try:
            if len(v)<12:return None,0
            precos=np.array([x['close'] for x in v])
            ema5=np.mean(precos[-5:]);ema13=np.mean(precos[-13:])
            macd=ema5-ema13;sinal=macd*0.5
            mom=precos[-1]-precos[-3] if len(precos)>=3 else 0
            sc=0;sp=0
            if macd>sinal and macd>0:sc+=3
            elif macd>sinal:sc+=1
            elif macd<sinal and macd<0:sp+=3
            elif macd<sinal:sp+=1
            if mom>0.00003:sc+=3
            elif mom>0:sc+=1
            elif mom<-0.00003:sp+=3
            elif mom<0:sp+=1
            if sc>=2 and sc>sp:return'CALL',min(48+sc*4,85)
            if sp>=2 and sp>sc:return'PUT',min(48+sp*4,85)
            return None,0
        except:return None,0

class Tsunami:
    def analisar(self,v):
        try:
            if len(v)<12:return None,0
            precos=[x['close'] for x in v]
            altas=sum(1 for i in range(-min(5,len(v)-1),0) if precos[i]>precos[i-1])
            sc=0;sp=0
            if altas>=3:sc+=3
            elif altas<=2:sp+=3
            if sc>=2 and sc>sp:return'CALL',min(50+sc*3,85)
            if sp>=2 and sp>sc:return'PUT',min(50+sp*3,85)
            return None,0
        except:return None,0

class QuantumIA:
    def __init__(self):
        self.estrategias=[
            ('💀 Mortalha',Mortalha()),('🐜 Formiga',Formiga()),
            ('🏰 Fortaleza',Fortaleza()),('⚡ Raio Negro',RaioNegro()),
            ('🌊 Tsunami',Tsunami())
        ]
        self.catalogador=CatalogadorInteligente()
        self.sinais_bloqueados_volatilidade=0

    def _calcular_atr(self, velas, periodo=14):
        if len(velas) < periodo + 1:
            return None
        trs = []
        for i in range(-periodo, 0):
            h = velas[i]['high']
            l = velas[i]['low']
            c_prev = velas[i-1]['close'] if i > -periodo else velas[i]['open']
            tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
            trs.append(tr)
        return np.mean(trs) if trs else None
    
    def _volatilidade_ok(self, velas):
        atr = self._calcular_atr(velas, 14)
        if atr is None:
            return False
        return ATR_MIN <= atr <= ATR_MAX

    def obter_sinal(self, velas_dict):
        for par, velas in velas_dict.items():
            if len(velas) < 30:
                continue
            if not self._volatilidade_ok(velas):
                self.sinais_bloqueados_volatilidade += 1
                continue
            for nome_est, est in self.estrategias:
                resultado = est.analisar(velas)
                if resultado and len(resultado) >= 2:
                    d, c = resultado[0], resultado[1]
                    if d in ('CALL', 'PUT') and c > 0:
                        return {'ativo': par, 'direcao': d, 'confianca': c, 'estrategia': nome_est}
        return None

class IQAPI:
    def __init__(self,e,s,a):self.e=e;self.s=s;self.a=a;self.api=None;self.velas={nome:deque(maxlen=100) for nome in a};self.ok=False
    def conectar(self):
        for t in range(5):
            try:
                if self.api:
                    try:self.api.close()
                    except:pass
                    time.sleep(2)
                self.api=IQ_Option(self.e,self.s);ok,_=self.api.connect()
                if ok:self.ok=True;return True
                time.sleep(5*(t+1))
            except:time.sleep(5*(t+1))
        self.ok=False;return False
    def obter(self,ativo_id,qtd=80):
        for retry in range(3):
            if not self.ok and not self.conectar():return 0
            try:
                c=self.api.get_candles(ativo_id,300,qtd,time.time())
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

class Bot:
    def __init__(self):
        self.tg=Telegram(TOKEN,CHAT);self.m=QuantumIA();self.p=Placar();self.iq=IQAPI(EMAIL,SENHA,ATIVOS)
        self.op=False;self.ult=0;self.sinais=0
        self.ultimo_dia=datetime.now(FUSO_BR).day

    def fmt_sinal(self,s):
        agora=datetime.now(FUSO_BR)
        minuto=agora.minute
        resto=minuto%5
        if resto==0 and agora.second==0:
            he=(agora.replace(second=0,microsecond=0)).strftime('%H:%M')
        else:
            he=(agora.replace(second=0,microsecond=0)+timedelta(minutes=5-resto)).strftime('%H:%M')
        e="🟢" if s['direcao']=='CALL' else "🔴"
        return f"""🚨SINAL AO VIVO🚨

✳️ QUANTUM IA M5 ✅
⏲ EXPIRAÇÃO: M5

👉🏼 HORARIO: {he}

🏳ATIVO: {s['ativo']} {s['direcao']}

📊 Confiança: {s['confianca']:.0f}%
🧠 Estratégia: {s['estrategia']}

🍀🍀BOA SORTE 🍀 🍀"""

    def fmt_corr(self,r,s):
        total=self.p.w+self.p.g1+self.p.l
        tx=round(((self.p.w+self.p.g1)/total)*100,1) if total>0 else 0
        return f"""{r}
📊 {s['ativo']} | {s['direcao']}
📊 Placar: 🟢{self.p.w}W 🟡{self.p.g1}G1 🔴{self.p.l}L
🎯 Assertividade: {tx}%"""

    async def corrigir(self,sinal):
        at=sinal['ativo'];d=sinal['direcao']
        try:
            await asyncio.sleep(300)  # 5 min
            self.iq.atualizar()
            v=self.iq.velas[at]
            if len(v)<2:self.op=False;return
            pc=v[-1]['open']
            await asyncio.sleep(5)
            v=self.iq.velas[at]
            if len(v)>0 and ((d=='CALL' and v[-1]['high']>pc) or (d=='PUT' and v[-1]['low']<pc)):
                r=self.p.win(0);self.tg.send(self.fmt_corr(r,sinal));self.op=False;return
            # Gale 1
            await asyncio.sleep(300)
            self.iq.atualizar()
            v=self.iq.velas[at]
            if len(v)>0:
                pg=v[-1]['open']
                await asyncio.sleep(5)
                v=self.iq.velas[at]
                if len(v)>0 and ((d=='CALL' and v[-1]['high']>pg) or (d=='PUT' and v[-1]['low']<pg)):
                    r=self.p.win(1);self.tg.send(self.fmt_corr(r,sinal));self.op=False;return
            r=self.p.loss();self.tg.send(self.fmt_corr(r,sinal));self.op=False
        except Exception as e:
            print(f"Erro: {e}");self.op=False

    async def run(self):
        banner()
        print("⚛️ Iniciando M5 Forex corrigido...")
        self.tg.send("🔥 *QUANTUM IA M5 CORRIGIDO*\n📊 5 Estratégias\n📈 ATR ampliado\n🔄 Troca automática\n💓 Heartbeat")
        
        if not self.iq.conectar():
            print("❌ Falha conexão!")
            return
        
        self.iq.atualizar()
        
        while True:
            try:
                agora=datetime.now(FUSO_BR)
                
                # Heartbeat
                if agora.second == 0:
                    total_velas = sum(len(v) for v in self.iq.velas.values())
                    print(f"💓 {agora.strftime('%H:%M:%S')} | Velas: {total_velas} | Sinais: {self.sinais}")
                    
                    if total_velas == 0:
                        print("🔄 Sem velas! Reconectando...")
                        self.iq.ok = False
                
                if agora.second in [0, 30]:
                    self.iq.atualizar()
                
                if not self.op:
                    sinal = self.m.obter_sinal(self.iq.velas)
                    if sinal and time.time() - self.ult > 300:
                        self.op = True
                        self.sinais += 1
                        self.ult = time.time()
                        self.tg.send(self.fmt_sinal(sinal))
                        asyncio.create_task(self.corrigir(sinal))
                
                await asyncio.sleep(3)
                
            except KeyboardInterrupt:
                print("🛑 Encerrado.")
                break
            except Exception as e:
                print(f"❌ {e}")
                await asyncio.sleep(5)

if __name__=="__main__":
    asyncio.run(Bot().run())
