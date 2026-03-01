import logging
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN
from ai_service import analisar_mensagem
from keep_alive import keep_alive
# Configuração de pradrão de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao comando /start com a persona definida."""
    welcome_message = (
        "Olá! 🚀 Sou seu **Agente Crypto sênior**.\n\n"
        "Mande o nome de um ativo (ex: **BTC**, **ETH**) ou pergunte sobre DeFi e Macroeconomia, "
        "e eu te entrego a visão atualizada."
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=welcome_message, 
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa as mensagens de texto do usuário."""
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    # Envia um aviso de "digitando..." para dar feedback visual de que não travou
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    
    try:
        # Roda o processamento pesado do Agente em uma thread separada para não travar o loop assíncrono do Telegram
        resposta_ai = await asyncio.to_thread(analisar_mensagem, chat_id, user_text)
        
        try:
            # Verifica se o agente gerou um gráfico (Procura pela tag e extrai o nome do arquivo)
            import re
            chart_match = re.search(r"\[CHART_GENERATED:(.+?)\]", resposta_ai)
            
            if chart_match:
                filename = chart_match.group(1)
                chart_path = os.path.join(os.getcwd(), filename)
                # Opcional: Remover a [FLAG] do texto final e limpar quebras de linha em excesso
                resposta_ai = re.sub(r"\n*\[CHART_GENERATED:(.+?)\]\n*", "\n\n", resposta_ai).strip()
                
                if os.path.exists(chart_path):
                    # Envia a foto sozinha, pois o Telegram não permite fotos no meio do texto
                    with open(chart_path, 'rb') as photo:
                        await context.bot.send_photo(chat_id=chat_id, photo=photo)

            # Tenta enviar com HTML ativado
            await context.bot.send_message(
                chat_id=chat_id, 
                text=resposta_ai, 
                parse_mode='HTML'
            )
        except Exception as e_mark:
            logging.warning(f"Erro de Parse HTML! Enviando como texto limpo. Erro: {e_mark}")
            # Se der erro de HTML e o texto for gigante, trunca para 4000 caracteres para não dar crash de limite
            safe_text = resposta_ai[:4000] + "\n\n(Texto truncado por limite no Telegram)" if len(resposta_ai) > 4000 else resposta_ai
            
            await context.bot.send_message(
                chat_id=chat_id, 
                text=safe_text
            )
    except Exception as e:
        logging.error(f"Erro geral ao processar a mensagem: {e}")
        await context.bot.send_message(
            chat_id=chat_id, 
            text="🚨 Foi mal, o servidor do bot deu uma rateada aqui. Tenta novamente!"
        )

if __name__ == '__main__':
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'seu_token_aqui_do_botfather':
        print("🚨 ERRO: TELEGRAM_TOKEN não configurado corretamente.")
        print("💡 Crie um arquivo .env na raiz do projeto e insira seu token do @BotFather.")
        exit(1)
        
    # Inicializa o bot
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Inicia o servidor web falso para manter o bot online no Render (Plano Free)
    keep_alive()

    # Registra os handlers (comandos e mensagens)
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    print("🤖 Agente Crypto iniciado! Pressione Ctrl+C para parar.")
    application.run_polling()
