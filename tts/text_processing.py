import re
from num2words import num2words

class TextProcessor:
    @staticmethod
    def adaptar_texto_para_tts(texto, lang):
        # Converter números para palavras (incluindo decimais)

        # Adicionar pausas com vírgulas em frases longas
        texto = re.sub(r'\b(e|mas|porém)\b', r'\1,', texto, flags=re.IGNORECASE)
        
        texto = re.sub(
            r'\d+[\.,]?\d*', 
            lambda x: num2words(
                float(x.group().replace(',', '.')),  # Converte para float
                lang=lang                         # Define o idioma como português brasileiro
            ), 
            texto  # <--- Parâmetro "string" obrigatório do re.sub
        )
        
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