from tts.piper_manager import PiperManager
from tts.text_processing import TextProcessor
from audio.sound_player import SoundPlayer
from utils import helpers, ollama_client
from utils.tavily_client import TavilyService  # Altere a importação
import config
import time
import re
import requests
import sys
import signal
import termios
import tty
import json
import os

class ChatHandler:
    def __init__(self):
        self.sound_player = SoundPlayer()
        self.piper_manager = PiperManager()
        self.text_processor = TextProcessor()
        self.current_language_model = None  # Rastreia o modelo TTS atual
        self.tavily_client = TavilyService()  # Substitua TavilyClient por TavilyService
        self.search_context = ""  # Armazena contexto de pesquisas
        self.original_terminal_settings = None  # Armazenará as configurações originais
        self._setup_signal_handlers()
        self.tool_responses = []  # Armazena resultados de ferramentas
       
    def _processar_resposta_modelo(self, resposta_bruta):
        """Detecta e executa chamadas de ferramentas"""
        try:
            # # Tenta parsear JSON da resposta
            # tool_call = json.loads(resposta_bruta.strip())
            # if tool_call.get("name") == "search_on_web":
            #     query = tool_call.get("parameters", {}).get("query")
            #     return self._executar_pesquisa(query)
            tool_call = json.loads(resposta_bruta.strip())
            if tool_call.get("name") == "search_on_web":
                query = tool_call.get("parameters", {}).get("query")
                resultados = self._executar_pesquisa(query)
                
                # Envia answer + fontes como contexto estruturado
                return json.dumps({
                    "type": "research_result",
                    "answer": resultados["answer"],
                    "sources": resultados["sources"]
                })
        except json.JSONDecodeError:
            # Se não for JSON, retorna resposta normal
            return resposta_bruta
        except Exception as e:
            return f"[ERRO: {str(e)}]"

    def _executar_pesquisa(self, tool_call):
        """Executa pesquisa e formata resultados"""
        if tool_call.get("name") == "search_on_web":
            query = tool_call.get("parameters", {}).get("query")
            resultados = self.tavily_client.pesquisar(query)
            
            if not resultados:
                return "Nenhum resultado encontrado."
            
            contexto = ""
            if resultados.get("answer"):
                contexto += f"🔍 Resposta verificada: {resultados['answer']}\n\n"
            
            contexto += "📚 Fontes:\n"
            for idx, fonte in enumerate(resultados.get("results", [])[:3]):
                contexto += f"\n{idx+1}. {fonte['title']}\n{fonte['content']}\n"
            
            return contexto
        return ""

    def _handle_exit(self, signum, frame):
        """Executa limpeza antes de sair"""
        print("\n\nEncerrando...")
        self._restore_terminal()  # Restaura o terminal
        self.piper_manager._kill_processes()  # Mata processos de áudio
        self.sound_player.play_sound("exit")  # Som de saída
        sys.exit(0)

    def _setup_signal_handlers(self):
        """Configura tratadores para sinais de interrupção"""
        signal.signal(signal.SIGINT, self._handle_exit)  # Usar _handle_exit ao invés de _handle_signal
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_signal(self, signum, frame):
        """Restaura o terminal antes de sair"""
        self._restore_terminal()
        sys.exit(1)

    def _save_terminal_settings(self):
        """Salva as configurações originais do terminal"""
        self.original_terminal_settings = termios.tcgetattr(sys.stdin)

    def _detectar_chamada_ferramenta(self, resposta):
        """Detecta tool calls de forma flexível, sem depender de JSON válido"""
        try:
           # Passo 1: Encontra os blocos do tool call ou JSON
            tool_call_match = re.search(
                r'<\|tool_call\|>(.*?)<\|/tool_call\|>',
                resposta,
                re.DOTALL
            )

            json_call_match = re.search(
                r'(\[.*?\]).*?(\{.*?\})',  # Captura [ ] e { } separadamente
                resposta,
                re.DOTALL
            )

            if not (tool_call_match or json_call_match):
                return None

            # Passo 2: Decidir qual conteúdo processar
            if tool_call_match:
                content = tool_call_match.group(1)
            elif json_call_match:
                # Combina conteúdo de [ ] e { ] (grupos 1 e 2)
                content = f"{json_call_match.group(1)}{json_call_match.group(2)}"

            # Passo 3: Verificar se é uma chamada para 'search_on_web'
            if "search_on_web" not in content:
                return None

            # Passo 4: Extração flexível da query
            query = None

            # Tentativa 1: Extração via JSON estruturado
            json_pattern = r'"query":\s*"([^"]+)"'
            json_match = re.search(json_pattern, content, re.DOTALL)
            if json_match:
                query = json_match.group(1).strip()

            # Tentativa 2: Extração via padrões semi-estruturados (fallback)
            if not query:
                fallback_patterns = [
                    r"query=['‘’“”]([^'’“”]+)['‘’“”]",
                    r'termos?[\s:=]+["\']?([^"\'\n]+)',
                    r'busca por (.*?)(?=\n|$|\))'
                ]
                for pattern in fallback_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        query = match.group(1).strip()
                        break

            # Passo 5: Limpeza e retorno
            if query:
                query = re.sub(r'[”“]', '', query)  # Remove aspas inteligentes
                return {
                    "name": "search_on_web",
                    "parameters": {"query": query}
                }

            return None

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Erro ao processar tool call: {e}")
            return None

    def _restore_terminal(self):
        """Restaura o terminal para o estado original"""
        if self.original_terminal_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_terminal_settings)
        # Força limpeza dos processos
        self.piper_manager._kill_processes()

    def _atualizar_modelo_tts(self, texto):
        """Atualiza o modelo TTS com base no idioma detectado."""
        idioma = helpers.detectar_idioma(texto) if len(texto) >= 2 else "pt"
        caminho_modelo = config.PIPER_MODELS.get(idioma, config.PIPER_MODELS["default"])
        
        # Sempre atualiza o modelo e verifica se os processos estão ativos
        self.current_language_model = caminho_modelo
        self.piper_manager.start_processes(caminho_modelo)
        time.sleep(0.2)  # Pausa para inicialização
    
    def _gerar_contexto_pesquisa(self, query):
        """Gera contexto de pesquisa para perguntas que requerem dados atualizados"""
        if not self._requer_pesquisa(query):
            return ""
            
        print("\n🔍 Realizando pesquisa...")
        resultados = self.tavily_client.pesquisar(query)
        
        if not resultados:
            return "\n[AVISO: Não foi possível obter dados atualizados]"
        
        # Formata os resultados
        contexto = "\n[Contexto de pesquisa atualizado]:\n"
        contexto += f"- Resposta resumida: {resultados.get('answer', '')}\n"
        for i, result in enumerate(resultados.get('results', [])[:3]):
            contexto += f"\nFonte {i+1}:\n"
            contexto += f"Título: {result.get('title', '')}\n"
            contexto += f"Conteúdo: {result.get('content', '')}\n"
            contexto += f"URL: {result.get('url', '')}\n"
        
        self.search_context = contexto
        return contexto

    def _processar_buffer_tts(self, buffer_texto, idioma):
        """Processa o buffer de texto para TTS."""
        if buffer_texto.strip():
            # Se idioma não for fornecido, detecte automaticamente
            if not idioma:
                idioma = helpers.detectar_idioma(buffer_texto) if len(buffer_texto) >= 2 else "pt"
            texto_limpo = self.text_processor.adaptar_texto_para_tts(buffer_texto, idioma)
            self.piper_manager.send_sentence(texto_limpo)

    def obter_entrada_usuario(self):
        """Obtém entrada do usuário via API ou manual."""
        self.sound_player.play_sound("voice_record")
        time.sleep(1)
        print("Pode falar. Estou te ouvindo...", end="", flush=True)
        
        try:
            """Obtém entrada do usuário com tratamento do terminal"""
            self._save_terminal_settings()  # Salva estado original
            tty.setraw(sys.stdin.fileno())  # Modo raw para captura de teclas
            mensagem_completa = ""
            with requests.get("http://localhost:5000/stream", stream=True) as response:
                response.raise_for_status()
                print("\r" + " " * 40 + "\r", end="", flush=True)
                print("Você: ", end="", flush=True)
                
                for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
                    if chunk:
                        chunk = chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk
                        if chunk == "\n":
                            print()
                            break
                        print(chunk, end="", flush=True)
                        mensagem_completa += chunk
            return mensagem_completa
        except Exception as e:
            self._restore_terminal()
            # os.system('stty sane')
            return input("\nVocê (entrada manual): ")
        finally:
            self._restore_terminal()
            # Adicione estas linhas para forçar reset do terminal
            #os.system('stty sane')  # Linux/Mac
            #os.system('reset')      # Força reset completo

    def _executar_loop_conversa(self, modelo_selecionado):
        """Gerencia o loop principal da conversa."""
        os.system('reset')
        mensagens = []
        print("\nChat iniciado! Pressione Ctrl+C para encerrar.\n")
        
        try:
            while True:
                # 1. Obter entrada do usuário
                entrada_usuario = self.obter_entrada_usuario()
                if not entrada_usuario.strip():
                    continue

                # 2. Adicionar mensagens ao histórico
                mensagens.extend([
                    {"role": "user", "content": entrada_usuario}
                ])
                
                # 3. Gerar resposta inicial do modelo
                print("\nAssistente: ", end="", flush=True)
                full_response = ""
                buffer_texto = ""
                pesquisa_realizada = False

                for chunk in ollama_client.gerar_resposta_ollama(mensagens, modelo_selecionado):
                    resposta_processada = self._processar_resposta_modelo(chunk)
                    full_response += resposta_processada

                    # 4. Processar cada chunk de resposta
                    print(chunk, end="", flush=True)
                    full_response += chunk
                    buffer_texto += chunk

                    # 5. Verificar chamada de ferramenta
                    if not pesquisa_realizada:
                        tool_call = self._detectar_chamada_ferramenta(full_response)
                        if tool_call:
                            # 6. Executar pesquisa e atualizar contexto
                            resultados = self._executar_pesquisa(tool_call)
                            print(f"\nResultados da API: {resultados}")
                            if resultados:
                                mensagens.append({
                                    "role": "tool",
                                    "content": resultados
                                })
                                pesquisa_realizada = True
                                #break  # Reinicia o loop para nova geração

                    # 7. Processamento de áudio
                    self._atualizar_modelo_tts(full_response)
                    idioma = helpers.detectar_idioma(full_response)
                    
                    if re.search(r'[.!?]\s*$', buffer_texto):
                        self._processar_buffer_tts(buffer_texto, idioma)
                        buffer_texto = ""

                # 8. Se pesquisa foi realizada, gerar resposta final
                if pesquisa_realizada:
                    for chunk in ollama_client.gerar_resposta_ollama(mensagens, modelo_selecionado):
                        print(chunk, end="", flush=True)
                        full_response += chunk

                # 9. Finalizar processamento
                self._processar_buffer_tts(buffer_texto, idioma)
                self.piper_manager.wait_for_completion()
                
                # 10. Atualizar histórico
                mensagens.append({"role": "assistant", "content": full_response})
                print("\n")

        except Exception as e:  # Adicione este bloco para capturar quaisquer exceções
            print(f"\nErro: {e}")
        finally:
            self._restore_terminal()  # Garante restauração
            self.sound_player.play_sound("exit")
            time.sleep(1)
    

    def iniciar_chat(self):
        """Fluxo principal para iniciar o chat."""
        try:
            self._save_terminal_settings()
            self.sound_player.play_sound("open")
        
            if not ollama_client.verificar_ollama_rodando():
                print("Erro: Ollama não está rodando. Inicie o Ollama primeiro.")
                return
            
            modelos = ollama_client.listar_modelos()
            print("Modelos disponíveis:")
            for i, modelo in enumerate(modelos):
                print(f"{i + 1}. {modelo}")

            model_not_defined = True
            while model_not_defined:
                try:
                    self._restore_terminal()
                    escolha = int(input("Escolha o número do modelo: ")) - 1
                    modelo_selecionado = modelos[escolha]
                    model_not_defined = False
                except:
                    print("Você deve escolher número da lista")
            
            self._executar_loop_conversa(modelo_selecionado)
        finally:
            self._restore_terminal()
            # Forçar reset final
            # os.system('stty sane')
            # os.system('reset')