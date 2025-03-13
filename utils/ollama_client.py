import requests
import json
import config

def verificar_ollama_rodando():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except requests.ConnectionError:
        return False

def listar_modelos():
    response = requests.get("http://localhost:11434/api/tags")
    return [modelo['name'] for modelo in response.json()['models']]

def gerar_resposta_ollama(mensagens, modelo_selecionado):
    """Gera resposta do Ollama em formato de streaming"""
    dados = {
        "model": modelo_selecionado,
        "messages": mensagens,
        "tools":[config.TOOL_SCHEMA],
        "stream": True
    }

    try:
        with requests.post(
            "http://localhost:11434/api/chat",
            json=dados,
            stream=True
        ) as resposta:
            resposta.raise_for_status()

            for linha in resposta.iter_lines():
                if linha:
                    chunk = json.loads(linha.decode('utf-8'))
                    content_chunk = chunk['message']['content']
                    yield content_chunk

    except requests.exceptions.RequestException as e:
        yield f"\nErro na comunicação com Ollama: {str(e)}"
    except Exception as e:
        yield f"\nErro inesperado: {str(e)}"