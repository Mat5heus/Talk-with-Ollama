import requests
import json

def verificar_ollama_rodando():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except requests.ConnectionError:
        return False

def listar_modelos():
    response = requests.get("http://localhost:11434/api/tags")
    return [modelo['name'] for modelo in response.json()['models']]

def chat_ollama():
    if not verificar_ollama_rodando():
        print("Erro: Ollama não está rodando. Por favor inicie o Ollama primeiro.")
        return

    modelos = listar_modelos()
    print("Modelos disponíveis:")
    for i, modelo in enumerate(modelos):
        print(f"{i + 1}. {modelo}")
    
    escolha = int(input("Escolha o número do modelo que deseja usar: ")) - 1
    modelo_selecionado = modelos[escolha]

    mensagens = []
    print("\nChat iniciado! Digite 'sair' para encerrar.\n")
    
    try:
        while True:
            entrada_usuario = input("Você: ")
            
            if entrada_usuario.lower() == 'sair':
                break

            mensagens.append({
                "role": "user",
                "content": entrada_usuario
            })

            dados = {
                "model": modelo_selecionado,
                "messages": mensagens,
                "stream": False
            }

            resposta = requests.post(
                "http://localhost:11434/api/chat",
                json=dados
            )

            if resposta.status_code == 200:
                resposta_json = resposta.json()
                resposta_assistente = resposta_json['message']['content']
                print(f"\nAssistente: {resposta_assistente}\n")
                mensagens.append({
                    "role": "assistente",
                    "content": resposta_assistente
                })
            else:
                print(f"Erro na resposta da API: {resposta.text}")

    except KeyboardInterrupt:
        print("\nChat encerrado pelo usuário.")

if __name__ == "__main__":
    chat_ollama()