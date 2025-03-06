import subprocess
import queue
import threading
from pathlib import Path
import time
import config

class PiperManager:
    def __init__(self):
        self.piper_process = None
        self.aplay_process = None
        self.current_model = None
        self.sentence_queue = queue.Queue()
        self.processing_thread = None
        self.running = False
        self.lock = threading.Lock()
        self.models = config.PIPER_MODELS

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
        
        #2. Fecha o pipe do Piper gradualmente
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
    
      