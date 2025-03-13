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
        self.tavily_client = TavilyService()  # Substitua TavilyClient por TavilyService
        self.original_terminal_settings = None  # Armazenará as configurações originais
        self._setup_signal_handlers()


    def _executar_pesquisa(self, tool_call):
        """Executa pesquisa e formata resultados"""
        if tool_call.get("name") == "search_on_web":
            query = tool_call.get("parameters", {}).get("query")
            search_type = tool_call.get("parameters", {}).get("search_type")
            time_range = tool_call.get("parameters", {}).get("time_range")
            resultados = self.tavily_client.pesquisar(query, search_type=search_type, time_range=time_range)
            
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

    def _save_terminal_settings(self):
        """Salva as configurações originais do terminal"""
        self.original_terminal_settings = termios.tcgetattr(sys.stdin)

    # def _detectar_chamada_ferramenta(self, resposta):
    #     """Detecta chamadas de ferramentas incluindo formatos JSON complexos"""
    #     try:
    #         # Verifica se a função está mencionada em qualquer formato
    #         if not re.search(r'\bsearch_on_web\b', resposta, re.IGNORECASE):
    #             return None

    #         # Dicionário para armazenar os parâmetros encontrados
    #         params = {
    #             "query": None,
    #             "search_type": "general",
    #             "time_range": "none"
    #         }

    #         # Padrão abrangente para capturar parâmetros em diferentes formatos
    #         param_patterns = [
    #             (r'"query"\s*:\s*["\']?([^"\'{}]+)', 'query'),
    #             (r'(?:"search_type"|tipo)\s*[:=]\s*["\']?([^"\'{},]+)', 'search_type'),
    #             (r'(?:"time_range"|periodo)\s*[:=]\s*["\']?([^"\'{},]+)', 'time_range'),
    #             (r'\{.*?"parameters"\s*:\s*\{.*?"query"\s*:\s*"([^"]+).*?\}.*?\}', 'query'),  # JSON profundo
    #             (r'\[.*?\{.*?"name"\s*:\s*"search_on_web".*?\}.*?\]', None)  # Captura todo o array JSON
    #         ]

    #         # Busca por todos os parâmetros usando múltiplos padrões
    #         for pattern, param_name in param_patterns:
    #             matches = re.finditer(pattern, resposta, re.IGNORECASE | re.DOTALL)
    #             for match in matches:
    #                 if param_name is None:  # Caso especial para processamento de JSON completo
    #                     json_block = match.group(0)
    #                     # Extrai parâmetros do bloco JSON
    #                     for json_pattern, json_param in [
    #                         (r'"query"\s*:\s*"([^"]+)', 'query'),
    #                         (r'"time_range"\s*:\s*"([^"]+)', 'time_range'),
    #                         (r'"search_type"\s*:\s*"([^"]+)', 'search_type')
    #                     ]:
    #                         json_match = re.search(json_pattern, json_block, re.IGNORECASE)
    #                         if json_match:
    #                             params[json_param] = json_match.group(1).strip('"\' ')
    #                 elif match.group(1):
    #                     value = match.group(1).strip('"\':, ')
    #                     if value:
    #                         params[param_name] = value

    #         # Limpeza e normalização
    #         params["query"] = re.sub(r'[“”]', '', params["query"]).strip() if params["query"] else None
            
    #         # Validação dos valores
    #         valid_search_types = {"news", "finance", "general"}
    #         params["search_type"] = params["search_type"].lower()
    #         if params["search_type"] not in valid_search_types:
    #             params["search_type"] = "general"

    #         valid_time_ranges = {"none", "day", "week", "month", "year"}
    #         params["time_range"] = params["time_range"].lower()
    #         if params["time_range"] not in valid_time_ranges:
    #             params["time_range"] = "none"

    #         # Verificação do parâmetro obrigatório
    #         if not params["query"]:
    #             return None

    #         return {
    #             "name": "search_on_web",
    #             "parameters": {
    #                 "query": params["query"],
    #                 "search_type": params["search_type"],
    #                 "time_range": params["time_range"]
    #             }
    #         }

    #     except Exception as e:
    #         print(f"Erro na detecção de tool call: {e}")
    #         return None

    def _detectar_chamada_ferramenta(self, resposta):
        """Detecta apenas a primeira ocorrência válida e ignora blocos subsequentes"""
        try:
            # Encontra a PRIMEIRA ocorrência da palavra-chave
            first_occurrence = re.search(r'\bsearch_on_web\b', resposta, re.IGNORECASE)
            if not first_occurrence:
                return None

            params = {
                "query": None,
                "search_type": "general",
                "time_range": "none"
            }

            # Padrões prioritários para extração imediata
            priority_patterns = [
                # Padrão 1: Parâmetros estruturados próximos à keyword
                r'search_on_web[^\{]*\{([^\}]+)\}',
                # Padrão 2: Parâmetros inline
                r'\(([^\)]+)\)'
            ]

            extracted = False
            
            # Primeira fase: Busca por padrões estruturados próximos
            for pattern in priority_patterns:
                match = re.search(pattern, resposta, re.IGNORECASE)
                if match:
                    param_block = match.group(1)
                    # Extrai pares chave-valor do bloco
                    pairs = re.findall(r'(\w+)\s*[:=]\s*["\']?([^"\'\),]+)', param_block)
                    for key, value in pairs:
                        key = key.lower().strip()
                        value = value.strip(' "\'')
                        if key in params:
                            params[key] = value
                    if params["query"]:
                        extracted = True
                        break  # Para após primeira extração válida

            # Segunda fase: Busca textual se necessário
            if not extracted:
                # Procura padrões informais APENAS no contexto isolado
                informal_patterns = [
                    r'query\s*[=:]\s*["\']?([^"\'\,\s]+)',
                    r'["\']([^"\'\)]+)["\']\s*[,\)]'
                ]
                for pattern in informal_patterns:
                    match = re.search(pattern, resposta)
                    if match:
                        params["query"] = match.group(1).strip()
                        break

            # Validação e limpeza
            params["query"] = re.sub(r'[“”]', '', params["query"]).strip() if params["query"] else None
            
            if not params["query"]:
                return None

            return {
                "name": "search_on_web",
                "parameters": {
                    "query": params["query"],
                    "search_type": params["search_type"],
                    "time_range": params["time_range"]
                }
            }

        except Exception as e:
            print(f"Erro na detecção de tool call: {e}")
            return None
    
    def _restore_terminal(self):
        """Restaura o terminal para o estado original"""
        if self.original_terminal_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_terminal_settings)
        # Força limpeza dos processos
        #self.piper_manager._kill_processes()

    def _atualizar_modelo_tts(self, texto):
        """Atualiza o modelo TTS com base no idioma detectado."""
        idioma = helpers.detectar_idioma(texto) if len(texto) >= 2 else "pt"
        caminho_modelo = config.PIPER_MODELS.get(idioma, config.PIPER_MODELS["default"])
        
        # Sempre atualiza o modelo e verifica se os processos estão ativos
        self.piper_manager.start_processes(caminho_modelo)
        time.sleep(0.2)  # Pausa para inicialização
    

    def _processar_buffer_tts(self, buffer_texto, idioma):
        """Processa o buffer de texto para TTS."""
        if buffer_texto.strip():
            # Se idioma não for fornecido, detecte automaticamente
            if not idioma:
                idioma = helpers.detectar_idioma(buffer_texto) if len(buffer_texto) >= 2 else "pt"
            texto_limpo = self.text_processor.adaptar_texto_para_tts(buffer_texto, idioma)
            self.piper_manager.send_sentence(texto_limpo)

    def chat_handler(self):
        try:
            user_input = input("\nVocê (entrada manual): ")
            
            # Tentativa fallida para decodificar a entrada do usuário, captura o exceção.
            decoded_input = user_input.encode('utf-8').decode('utf-8', 'replace').strip()
            print(f"Entrada processada: {decoded_input}")
            return decoded_input
        except Exception as e:
            self._restore_terminal()
            # os.system('stty sane')
            print(f"Erro na entrada manual: {e}")


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
            return self.chat_handler() #input("\nVocê (entrada manual): ")
        finally:
            self._restore_terminal()
            # Adicione estas linhas para forçar reset do terminal
            os.system('stty sane')  # Linux/Mac
            #os.system('reset')      # Força reset completo



    def _executar_loop_conversa(self, modelo_selecionado):
        """Gerencia o loop principal da conversa."""
        os.system('reset')
        mensagens = []
        mensagens.append({"role": "system", "content": config.SYSTEM_INSTRUCTION})
        #mensagens.append({"role": "tool", "content": config.TOOL_SCHEMA})
        print("\nChat iniciado! Pressione Ctrl+C para encerrar.\n", flush=True)  # Forçar flush
        
        try:
            while True:
                # 1. Obter entrada do usuário
                entrada_usuario = self.obter_entrada_usuario()
                if not entrada_usuario.strip():
                    continue

                # 2. Adicionar ao histórico
                mensagens.append({"role": "user", "content": entrada_usuario})
                
                # 3. Gerar resposta do modelo
                print("\nAssistente: ", end="", flush=True)  # Forçar flush
                full_response = ""
                buffer_texto = ""
                pesquisa_realizada = False

                # Loop de geração principal
                for chunk in ollama_client.gerar_resposta_ollama(mensagens, modelo_selecionado):
                    full_response += chunk
                    
                    # Exibir no terminal IMEDIATAMENTE
                    print(chunk, end="", flush=True)  # Flush explícito
                    buffer_texto += chunk

                    # Verificar tool call
                    if not pesquisa_realizada:
                        tool_call = self._detectar_chamada_ferramenta(full_response)
                        if tool_call:
                            #Novo: Indicador de pesquisa iniciando
                            print("\n\n🌐 Buscando informações atualizadas...", end="\r", flush=True)
                            resultados = self._executar_pesquisa(tool_call)
                            #Novo: Indicador de pesquisa concluída
                            print("✅ Pesquisa concluída! Processando...".ljust(50), flush=True)
                            if resultados:
                                mensagens.append({"role": "tool", "content": resultados})
                                pesquisa_realizada = True
                                break  # Interrompe a geração atual para nova consulta

                    # Processar TTS
                    self._atualizar_modelo_tts(full_response)
                    idioma = helpers.detectar_idioma(full_response)
                    
                    # Enviar para TTS quando houver pausa natural
                    if re.search(r'[.!?]\s*$', buffer_texto):
                        self._processar_buffer_tts(buffer_texto, idioma)
                        buffer_texto = ""

                # 4. Se houve pesquisa, gerar resposta final
                if pesquisa_realizada:
                    print("\n🔍 Resposta com base na pesquisa:", end="", flush=True)  # Novo prompt
                    full_response = ""
                    buffer_texto = ""
                    
                    for chunk in ollama_client.gerar_resposta_ollama(mensagens, modelo_selecionado):
                        print(chunk, end="", flush=True)  # Exibir cada chunk
                        full_response += chunk
                        buffer_texto += chunk

                        # Processar TTS
                        self._atualizar_modelo_tts(full_response)
                        idioma = helpers.detectar_idioma(full_response)
                        
                        if re.search(r'[.!?]\s*$', buffer_texto):
                            self._processar_buffer_tts(buffer_texto, idioma)
                            buffer_texto = ""

                # 5. Finalizar processamento
                self._processar_buffer_tts(buffer_texto, idioma)
                self.piper_manager.wait_for_completion()
                
                # 6. Atualizar histórico
                mensagens.append({"role": "assistant", "content": full_response})
                print("\n")  # Nova linha após resposta

        except Exception as e:
            print(f"\n[ERRO] Falha ao exibir resposta: {str(e)}", flush=True)
        finally:
            self._restore_terminal()
            self.sound_player.play_sound("exit")

    

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