from pathlib import Path
import subprocess
import os

class SoundPlayer:
    def __init__(self):
        self.sounds_dir = Path(__file__).parent.parent / "sounds"
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