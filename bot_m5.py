#!/usr/bin/env python3
"""
⚛️ ESPELHO TRADER MAGO - TELEGRAM
📡 Copia sinais (texto) + repassa fotos de resultado
✅ Sem contagem / sem placar / sem classificação
✅ Zeramento à meia-noite (horário de Brasília) — só log
❌ SEM OCR
"""

# ==============================
# FUSO HORÁRIO BRASÍLIA (UTC-3)
# ==============================
import os
os.environ['TZ'] = 'America/Sao_Paulo'
try:
    import time
    time.tzset()
except Exception:
    pass

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime, timedelta
import re
import asyncio
import sys

# ==============================
# CONFIGURAÇÕES
# ==============================
api_id = int(os.environ.get('API_ID', '22453120'))
api_hash = os.environ.get('API_HASH', '89826a4104518e9ed650cdb451ad8b53')
SESSAO_STRING = os.environ.get('SESSAO_STRING', '')

origem = int(os.environ.get('CANAL_ORIGEM', '-1001245695047'))
destino = int(os.environ.get('CANAL_DESTINO', '-1004483690234'))

if not SESSAO_STRING:
    print("❌ ERRO: Variável SESSAO_STRING não definida!")
    sys.exit(1)

client = TelegramClient(StringSession(SESSAO_STRING), api_id, api_hash)

# ==============================
# FUNÇÕES
# ==============================

def horario():
    return datetime.now().strftime("%H:%M:%S")

def obter_texto(event):
    msg = event.message
    return msg.message or msg.text or ""

def eh_sinal(texto):
    t = texto.lower()
    tem_ativo = 'ativo:' in t
    tem_horario = 'horário:' in t or 'horario:' in t
    return tem_ativo and tem_horario

def extrair_dados_sinal(texto):
    dados = {
        'ativo': 'EUR/JPY (OTC)',
        'direcao': 'CALL',
        'horario': '',
        'expiracao': 'M1'
    }
    m = re.search(r'Ativo:\s*([^\n]+)', texto, re.IGNORECASE)
    if m: dados['ativo'] = m.group(1).strip()
    m = re.search(r'Hor[áa]rio:\s*(\d{1,2}:\d{2})', texto, re.IGNORECASE)
    if m: dados['horario'] = m.group(1).strip()
    m = re.search(r'Expira[çc][ãa]o:\s*([^\n]+)', texto, re.IGNORECASE)
    if m: dados['expiracao'] = m.group(1).strip()
    m = re.search(r'Dire[çc][ãa]o:\s*([^\n]+)', texto, re.IGNORECASE)
    if m:
        d = m.group(1).strip().upper()
        if 'CALL' in d or '🟢' in d or 'COMPRA' in d:
            dados['direcao'] = 'CALL'
        elif 'PUT' in d or '🔴' in d or 'VENDA' in d:
            dados['direcao'] = 'PUT'
        else:
            dados['direcao'] = d
    if not dados['horario']:
        dados['horario'] = datetime.now().strftime("%H:%M")
    return dados

def formatar_sinal(dados):
    emoji_direcao = '🟢' if dados['direcao'] == 'CALL' else '🔴'
    return f"""⚛️ SINAL TRADER MAGO ⚛️

⏰ Horário: {dados['horario']}
💵 Ativo: {dados['ativo']}
📉 Direção: {dados['direcao']} {emoji_direcao}
⏳ Expiração: {dados['expiracao']}

⚠️ Entrar somente no horário marcado.
🔄 2 recuperação (Gale 2)!"""

async def log_zeramento():
    while True:
        agora = datetime.now()
        meia_noite = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        if agora >= meia_noite:
            meia_noite = meia_noite + timedelta(days=1)
        espera = (meia_noite - agora).total_seconds()
        print(f"[{horario()}] ⏰ Próximo log de zeramento em {espera/3600:.2f}h (00:00 Brasília)")
        await asyncio.sleep(espera)
        print(f"[{horario()}] 🔄 NOVO DIA (horário Brasília)")

@client.on(events.NewMessage(chats=origem))
async def processar_mensagem(event):
    texto = obter_texto(event)
    tem_foto = event.message.photo is not None

    print(f"[{horario()}] 🔔 Nova mensagem (foto={tem_foto})")

    # ---- 1) É SINAL? ----
    if texto and eh_sinal(texto):
        dados = extrair_dados_sinal(texto)
        msg = formatar_sinal(dados)
        print(f"[{horario()}] 📊 SINAL | {dados['ativo']} | {dados['direcao']} | {dados['horario']}")
        try:
            await client.send_message(destino, msg)
            print(f"[{horario()}] ✅ Sinal enviado!")
        except Exception as e:
            print(f"[{horario()}] ❌ Erro: {e}")
        print("=" * 40)
        return

    # ---- 2) É FOTO? Repassa igual ----
    if tem_foto:
        print(f"[{horario()}] 🖼️ Foto detectada — repassando...")
        try:
            # Baixa a imagem e reenvia igual
            foto_bytes = await event.message.download_media(file=bytes)
            legenda = texto if texto else None
            await client.send_file(destino, foto_bytes, caption=legenda)
            print(f"[{horario()}] ✅ Foto repassada!")
        except Exception as e:
            print(f"[{horario()}] ❌ Erro ao repassar foto: {e}")
        print("=" * 40)
        return

    # ---- 3) Qualquer outro texto — ignora ----
    print(f"[{horario()}] 📝 Ignorada")
    print("=" * 40)

async def main():
    print("=" * 50)
    print("     ⚛️ ESPELHO TRADER MAGO ⚛️")
    print("=" * 50)
    print(f"🕐 Fuso horário: {time.tzname}")
    print(f"🕐 Agora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} (Brasília)")
    await client.start()
    print("✅ Conectado")
    print(f"📡 Origem: {origem}")
    print(f"📡 Destino: {destino}")
    print("📋 Modo: repassar foto de resultado sem classificar")
    print("⏳ Aguardando...")
    asyncio.create_task(log_zeramento())
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Encerrado!")
