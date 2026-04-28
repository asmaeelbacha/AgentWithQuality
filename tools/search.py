import os
from langchain_tavily import TavilySearch
from dotenv import load_dotenv

load_dotenv()

def get_search_tool(max_results: int = 2) -> TavilySearch:
    return TavilySearch(
        max_results=max_results,
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
    )
