import requests
import json
import subprocess
import re
import time
from langdetect import detect
import queue
import os
from pathlib import Path
import threading
from num2words import num2words  # Instale com: pip install num2words

SYSTEM_INSTRUCTION = """
    Always speak in portuguese.
    You are friendly friend.
    You know how to talk about a varity of topics.
    You are in a conversation, be natural and straightforward.
    don't numerate topics
    Today's Date: March 4, 2025.
    """

class PiperManager:
    def __init__(self):
        self.piper_process = None
        self.aplay_process = None
        self.current_model = None
        self.sentence_queue = queue.Queue()
        self.processing_thread = None
        self.running = False
        self.lock = threading.Lock()


    def start_processes(self, model_path):
       with self.lock:
            if model_path != self.current_model or not self._processes_alive():
                self._kill_processes()
                self.current_model = model_path
                
                # Cria novos processos
                self.piper_process = subprocess.Popen(
                    ['piper', '--model', model_path, '--output-raw'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0
                )
                
                self.aplay_process = subprocess.Popen(
                    ['aplay', '-r', '22050', '-f', 'S16_LE', '-t', 'raw'],
                    stdin=self.piper_process.stdout,
                    stderr=subprocess.DEVNULL,
                    bufsize=0
                )

                # Inicia thread de processamento
                self.running = True
                self.processing_thread = threading.Thread(target=self._process_sentence_queue)
                self.processing_thread.daemon = True
                self.processing_thread.start()

    def _kill_processes(self):
        self.running = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join()
            
        if self.piper_process:
            try:
                self.piper_process.stdin.close()
                self.piper_process.terminate()
                self.piper_process.wait()
            except:
                pass
                
        if self.aplay_process:
            try:
                self.aplay_process.terminate()
                self.aplay_process.wait()
            except:
                pass

    def _processes_alive(self):
        return (self.piper_process and self.piper_process.poll() is None and
                self.aplay_process and self.aplay_process.poll() is None)

    def _process_sentence_queue(self):
        while self.running or not self.sentence_queue.empty():
            try:
                sentence = self.sentence_queue.get(timeout=0.1)
                if self.piper_process and not self.piper_process.stdin.closed:
                    with self.lock:
                        self.piper_process.stdin.write((sentence + "\n").encode('utf-8'))
                        self.piper_process.stdin.flush()
                self.sentence_queue.task_done()
            except (queue.Empty, BrokenPipeError):
                continue
            except Exception as e:
                print(f"Erro: {e}")
                break

    def send_sentence(self, text):
         if text.strip():
            self.sentence_queue.put(text.strip())
    
    def wait_for_completion(self):
        """Espera bloqueante até finalizar toda reprodução"""
        # 1. Espera esvaziar a fila
        self.sentence_queue.join()
        
        # 2. Fecha o pipe do Piper gradualmente
        if self.piper_process and not self.piper_process.stdin.closed:
            try:
                self.piper_process.stdin.flush()
                self.piper_process.stdin.close()
            except BrokenPipeError:
                pass
        
        # 3. Espera bloqueante pelo término do aplay
        if self.aplay_process:
            try:
                # Espera ativa sem timeout
                while self.aplay_process.poll() is None:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass
    
    def adaptar_texto_para_tts(self, texto, lang):
        # Converter números para palavras (incluindo decimais)
        texto = re.sub(
            r'\d+[\.,]?\d*', 
            lambda x: num2words(
                float(x.group().replace(',', '.')),  # Converte para float
                lang=lang                         # Define o idioma como português brasileiro
            ), 
            texto  # <--- Parâmetro "string" obrigatório do re.sub
        )
        
        # Adicionar pausas com vírgulas em frases longas
        texto = re.sub(r'\b(e|mas|porém)\b', r'\1,', texto, flags=re.IGNORECASE)
        
        # Tratar siglas (ex: "EUA" → "E U A")
        texto = re.sub(r'\b([A-Z]{2,})\b', lambda x: ' '.join(x.group()), texto)
        
        # Substituir símbolos por palavras
        substituicoes = {
            r'R\$': 'reais ',
            r'%': 'por cento',
            r'km/h': 'quilômetros por hora',
            r'\.\.\.': ', ',  # Substitui "..." por pausa
            r'quatro/sete':'vinte quatro horas por dia'
        }
        for padrao, substituicao in substituicoes.items():
            texto = re.sub(padrao, substituicao, texto)
        
        # Converter palavras entre ** para MAIÚSCULAS (ex: **alerta** → ALERTA)
        texto = re.sub(
            r'\*\*(.*?)\*\*',  # Captura o texto entre **
            lambda x: x.group(1).upper(),  # Converte para maiúsculas
            texto
        )
        
        return texto

# Adicione esta classe para gerenciamento de sons
class SoundPlayer:
    def __init__(self):
        self.sounds_dir = Path(__file__).parent / "sounds"
        self.load_sounds()
    
    def load_sounds(self):
        # Crie uma pasta 'sounds' no mesmo diretório do script
        self.sounds = {
            "open": self.sounds_dir / "open.mp3",
            "exit": self.sounds_dir / "exit.mp3",
            "voice_record": self.sounds_dir / "voice_record.mp3"
        }
        
        # Verifique se os arquivos existem
        for sound in self.sounds.values():
            if not sound.exists():
                raise FileNotFoundError(f"Arquivo de som não encontrado: {sound}")

    def play_sound(self, sound_name):
        sound_path = self.sounds.get(sound_name)
        if sound_path and sound_path.exists():
            # Comando multiplataforma para reproduzir sons
            if os.name == 'nt':  # Windows
                subprocess.Popen(['open', str(sound_path)], shell=True)
            else:  # Linux/Mac
                subprocess.Popen(['mpg123', "-q", str(sound_path)])
           
def verificar_ollama_rodando():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except requests.ConnectionError:
        return False

def listar_modelos():
    response = requests.get("http://localhost:11434/api/tags")
    return [modelo['name'] for modelo in response.json()['models']]

def limpar_texto(texto):
    # Remove caracteres especiais não desejados (exceto pontuações comuns)
    texto_limpo = re.sub(r'[^\w\s.,!?:;]', '', texto)
    # Remove múltiplos espaços em branco
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
    return texto_limpo.strip()

def obter_entrada_usuario_via_api(sound_player):
    sound_player.play_sound("voice_record")
    time.sleep(1)
    print("Pode falar. Estou te ouvindo...", end="", flush=True)
    
    try:
        mensagem_completa = ""
        
        # Faz requisição para a API de streaming
        with requests.get("http://localhost:5000/stream", stream=True) as response:
            response.raise_for_status()  # Verifica se há erro na resposta
            
            # Limpa a linha de "Aguardando entrada..."
            print("\r" + " " * 40 + "\r", end="", flush=True)
            
            # Imprime "Você: " antes de começar a mostrar o stream
            print("Você: ", end="", flush=True)
            
            for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
                if chunk:
                    # Decodifica o chunk para texto se estiver em bytes
                    if isinstance(chunk, bytes):
                        chunk = chunk.decode('utf-8')
                    
                    # Verifica se é o caractere de nova linha que finaliza o stream
                    if chunk == "\n":
                        print()  # Adiciona quebra de linha após a mensagem completa
                        break
                    
                    # Exibe o chunk e o adiciona à mensagem completa
                    print(chunk, end="", flush=True)
                    mensagem_completa += chunk
                    
        return mensagem_completa
    except Exception as e:
        print(f"\nErro ao obter entrada do usuário via API: {e}")
        # Fallback para entrada manual se a API falhar
        return input("Você (entrada manual): ")

def chat_ollama():
    sound_player = SoundPlayer()
    sound_player.play_sound("open")
    piper_manager = PiperManager()  # Adicione esta linha
    current_language_model = None   # Rastreie o modelo atual

    if not verificar_ollama_rodando():
        print("Erro: Ollama não está rodando. Inicie o Ollama primeiro.")
        return

    modelos = listar_modelos()
    print("Modelos disponíveis:")
    for i, modelo in enumerate(modelos):
        print(f"{i + 1}. {modelo}")
    
    escolha = int(input("Escolha o número do modelo: ")) - 1
    modelo_selecionado = modelos[escolha]

    mensagens = []
    print("\nChat iniciado! Pressione Ctrl+C para encerrar.\n")
    
    try:
        while True:
            # Dentro do loop de resposta:
            buffer_texto = ""
            current_language_model = None  # Redefina para cada resposta

            # Obtém entrada do usuário via API de streaming
            entrada_usuario = obter_entrada_usuario_via_api(sound_player)
            
            # Verifica se a mensagem está vazia (possível erro na API)
            if not entrada_usuario.strip():
                continue
            
            mensagens.append({ "role":"system", "content": SYSTEM_INSTRUCTION })
            mensagens.append({"role": "user", "content": entrada_usuario})

            dados = {
                "model": modelo_selecionado,
                "messages": mensagens,
                "stream": True
            }

            full_response = ""
            buffer_texto = ""
            print("Assistente: ", end="", flush=True)
            
            with requests.post(
                "http://localhost:11434/api/chat",
                json=dados,
                stream=True
            ) as resposta:
                full_response = ""
                buffer_texto = ""

                for linha in resposta.iter_lines():
                    if linha:
                        chunk = json.loads(linha.decode('utf-8'))
                        content_chunk = chunk['message']['content']
                        
                        print(content_chunk, end="", flush=True)
                        full_response += content_chunk
                        buffer_texto += content_chunk

                        # Detecção de idioma (movido para fora do loop)
                        if len(full_response) >= 2:  # Aumente o limite para melhor detecção
                            try:
                                idioma = detect(full_response)
                            except:
                                idioma = "pt"
                        else:
                            idioma = "pt"  # Valor padrão

                        # Mapeamento de modelos
                        caminho_modelo_piper = {
                            "en": "/home/matheus/projetos/piper/models/en_US-ryan-high.onnx",
                            "pt": "/home/matheus/projetos/piper/models/pt_BR-faber-medium.onnx",
                            "es": "/home/matheus/projetos/piper/models/es_MX-claude-high.onnx",
                            "zh": "/home/matheus/projetos/piper/models/zh_CN-huayan-medium.onnx"
                        }.get(idioma, "/home/matheus/projetos/piper/models/pt_BR-faber-medium.onnx")  # Fallback

                        if current_language_model != caminho_modelo_piper:
                            current_language_model = caminho_modelo_piper
                            piper_manager.start_processes(caminho_modelo_piper)
                            time.sleep(0.2)  # Pequena pausa para inicialização

                        
                        # Processa o buffer quando encontrar pontuação de final de frase
                        if re.search(r'[.!?]\s*$', buffer_texto):
                            texto_limpo = piper_manager.adaptar_texto_para_tts(buffer_texto, idioma)
                            piper_manager.send_sentence(texto_limpo)  # Espaço entre frases
                            # Esperar até que o áudio termine completamente
                            buffer_texto = ""

            # Processa qualquer texto restante no buffer
            if buffer_texto.strip():
                texto_limpo = piper_manager.adaptar_texto_para_tts(buffer_texto, idioma)
                piper_manager.send_sentence(texto_limpo)
                time.sleep(0.1)  # Permite o início da reprodução
            
            piper_manager.wait_for_completion()

            mensagens.append({ "role":"system", "content": SYSTEM_INSTRUCTION })
            mensagens.append({"role": "assistant", "content": full_response})
            print("\n")

    except KeyboardInterrupt:
        print("\nChat encerrado.")
    except Exception as e:
        print(f"\nErro: {e}")
    finally:
        sound_player.play_sound("exit")
        time.sleep(1)


if __name__ == "__main__":
    chat_ollama()