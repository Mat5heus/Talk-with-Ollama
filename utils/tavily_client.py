# utils/tavily_client.py
from tavily import TavilyClient
import config
import re
from urllib.parse import quote


class TavilyService:
    def __init__(self):
        self.client = TavilyClient(config.TAVILY_API_KEY)
        self.search_depth = config.TAVILY_SEARCH_DEPTH
    

    @staticmethod
    def _limpar_conteudo(texto):
        """Remove markdown e caracteres especiais do conteúdo"""
        return re.sub(r'[\*\_\[\]\(\)]', '', texto).strip()

    from urllib.parse import quote

    def pesquisar(self, query, max_results=8, search_type="general", time_range=None):
        """
        Executa uma pesquisa usando a biblioteca oficial do Tavily.
        
        Parâmetros:
        - query (str): O termo de busca a ser pesquisado.
        - max_results (int): Número máximo de resultados a serem retornados (padrão: 8).
        - search_type (str): Tipo de pesquisa (padrão: "general").
        - time_range (str, opcional): Intervalo de tempo para restringir a busca.
        
        Retorna:
        - dict: Resultados formatados da pesquisa ou um erro, se aplicável.
        """
        
        # Verifica se a query é válida
        if not query or not isinstance(query, str):
            return {"error": "Query inválida"}

        # Sanitiza a query para evitar problemas de formatação na busca
        query_sanitizada = quote(query.strip().lower())

        try:
            # Realiza a pesquisa usando a API do Tavily
            search_result = self.client.search(
                query=query_sanitizada,  # Termo de busca
                search_depth=self.search_depth,  # Profundidade da busca
                topic=search_type,  # Tipo de pesquisa (ex: "general", "news", etc.)
                time_range=time_range,  # Filtro por intervalo de tempo, se especificado
                max_results=max_results,  # Número máximo de resultados desejados
                include_answer="advanced",  # Define o nível de resposta incluída nos resultados
                include_images=False  # Não inclui imagens nos resultados
            )
            
            # Formata e retorna os resultados obtidos
            return self._formatar_resultados(search_result)
        
        except Exception as e:
            # Em caso de erro na busca, exibe a mensagem no console e retorna None
            print(f"Erro no Tavily: {e}")
            return None


    def _formatar_resultados(self, raw_data):
        """Garante compatibilidade total com a estrutura esperada"""
        formatted = {
            "answer": raw_data.get("answer", ""),
            "results": []
        }
        
        for result in raw_data.get("results", []):
            formatted["results"].append({
                "title": result.get("title", "Sem título"),
                "content": self._limpar_conteudo(result.get("content", "")),
                "url": result.get("url", "")
            })
        
        return formatted