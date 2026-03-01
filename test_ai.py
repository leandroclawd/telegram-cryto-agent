import ai_service
import traceback

try:
    print("Testing ai_service...")
    resposta = ai_service.analisar_mensagem('test_user_1', 'Analisa BTC')
    print("Resposta:")
    print(resposta)
except Exception as e:
    print("Exception capturada:")
    traceback.print_exc()
