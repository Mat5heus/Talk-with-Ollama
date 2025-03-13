# Talk-with-Ollama

## Overview
This project is a comprehensive chatbot application designed for text-based interactions, integrating terminal handling, language detection, model TTS processing, and Ollama API communication for information retrieval. The primary focus of this bot is to provide human-like conversation while offering additional functionalities such as detecting specific tool calls within user messages.

### Key Features:
1. **Terminal Handling**: Handles input in both manual (keyboard) mode and automatically from the terminal stream, ensuring seamless integration with the rest of the application.
2. **Language Detection**: Utilizes libraries like langdetect to identify the primary language of user inputs for accurate TTS processing and other adaptive features.
3. **Model TTS Processing**: Implements a TTS processor that updates the text-to-speech model dynamically based on detected language, optimizing speech output.
4. **Ollama API Integration**: Communicates with Ollama to fetch information, enabling the bot to provide relevant responses backed by current data or queries.
5. **Tool Call Detection and Execution**: Incorporates a custom function `_detectar_chamada_ferramenta` that identifies specific tool calls in user messages. This feature can be extended for executing commands, improving the chatbot’s utility as an information gathering and action-oriented assistant.
6. **Loop Management (Chat)**: The main function `iniciar_chat()` manages a conversation loop between user inputs and bot responses, ensuring smooth flow with appropriate handling of model requests, tool executions, TTS processing, and more.
7. **User Interface**: Uses simple text-based interactions for both manual input and automated terminal streaming; all responses are printed to the console for real-time display.

## Dependencies:
- **Python 3** (for scripting)
- **AnyIO**: For asynchronous I/O operations efficiently managing concurrent tasks like API requests, TTS processing, etc.
- **Other Dependencies:** Libraries for handling file paths (`os`), terminal control (`pty`, `termios`), text utilities (`re` for regular expressions), and model integration with Ollama via HTTPX.

- [Piper](https://github.com/rhasspy/piper): For real-time TTS.
- [whisper-server](https://github.com/Mat5heus/whisper-server): For fast transcription. (You can integrate with other STT with you want)

### other dependencies:
mpg123 player for .mp3 (program sounds) and aplay for .wav files (Piper voices)

```bash
sudo apt install -y mpg123
```

### Installation:
To run this chatbot application, ensure you have Python 3 installed. Install dependencies using pip:
```bash
git clone https://github.com/Mat5heus/Talk-with-Ollama.git
cd Talk-with-Ollama
python -m venv .venv

# On Unix or MacOS
source .venv/bin/activate

# On Windows
.\venv\Scripts\activate

pip install -r requirements.txt
```

## Running the Project
1. Navigate to your project directory in a terminal or command prompt.
2. Execute `python path/to/your/main.py` where `path/to/your/` is the absolute path of the main file.
3. If any terminal integration issues arise, ensure proper permissions for the required files and directories are maintained.

### Contributing
Feel free to contribute by submitting pull requests with bug fixes or improvements. For feature additions, consider discussing ideas on GitHub.

## License
This project is licensed under GNU 3 LICENSE.

Happy coding! Let this chatbot application showcase your skills in Python and asynchronous processing, while emphasizing integrations with language detection and text-to-speech technologies for an engaging user experience.