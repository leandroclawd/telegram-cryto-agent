import ai_service
import traceback

try:
    print("Testing ETH...")
    resposta = ai_service.analisar_mensagem('test_eth_1', 'analisa ETH')
    print("Resposta:")
    print(resposta)
except Exception as e:
    print("Exception capturada:")
    traceback.print_exc()
