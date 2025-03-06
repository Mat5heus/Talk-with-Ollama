import re
from langdetect import detect

def limpar_texto(texto):
     # Remove caracteres especiais não desejados (exceto pontuações comuns)
    texto_limpo = re.sub(r'[^\w\s.,!?:;]', '', texto)
    # Remove múltiplos espaços em branco
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
    return texto_limpo.strip()


def detectar_idioma(texto):
    try:
        return detect(texto)
    except:
        return "pt"