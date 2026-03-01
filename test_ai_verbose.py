import ai_service
import logging
from langchain.globals import set_debug

# Ativar logs do LangChain
set_debug(True)
logging.basicConfig(level=logging.DEBUG)

print("Iniciando teste verbose do Agente...")
resposta = ai_service.analisar_mensagem('123', 'Analisa BTC')
print("\n--- RESPOSTA FINAL ---\n")
print(resposta)
