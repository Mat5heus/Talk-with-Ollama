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

    def pesquisar(self, query, max_results=3):
        """Executa pesquisa usando a biblioteca oficial do Tavily"""

        if not query or not isinstance(query, str):
            return {"error": "Query inválida"}

        # Sanitiza a query
        query_sanitizada = quote(query.strip().lower())
    
        try:
            search_result = self.client.search(
                query=query,
                search_depth=self.search_depth,
                max_results=max_results,
                include_answer="advanced",
                include_images=False
            )
            return self._formatar_resultados(search_result)
        except Exception as e:
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