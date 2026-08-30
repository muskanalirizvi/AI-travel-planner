"""Web search tool backed by the Tavily Search API (free tier)."""

import os

import httpx
from langchain_core.tools import tool

from tools.net import system_certs_context, use_system_certs

_API_URL = "https://api.tavily.com/search"


def _client() -> httpx.Client:
    verify = system_certs_context() if use_system_certs() else True
    return httpx.Client(verify=verify, timeout=15.0)


@tool
def web_search(query: str) -> str:
    """Search the web for travel info not covered by the other tools.

    Use this for questions about attractions and things to do, visa/entry
    requirements, local customs, or other general travel info, e.g. "what
    documents do I need for a UAE visa from Pakistan" or "top attractions
    in Kyoto". Backed by the Tavily Search API (free tier, requires
    TAVILY_API_KEY from tavily.com). Returns a short synthesized answer
    plus a few source snippets with URLs.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY is not set in the environment; the web search tool is unavailable."

    try:
        with _client() as client:
            response = client.post(
                _API_URL,
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5,
                    "include_answer": True,
                },
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Error performing web search: {exc}"

    data = response.json()
    parts = []

    answer = data.get("answer")
    if answer:
        parts.append(f"Answer: {answer}")

    results = data.get("results") or []
    if results:
        parts.append("Sources:")
        for result in results:
            title = result.get("title", "untitled")
            url = result.get("url", "")
            content = (result.get("content") or "").strip()
            if len(content) > 300:
                content = content[:300].rstrip() + "..."
            parts.append(f"- {title} ({url}): {content}")

    if not parts:
        return f"No results found for '{query}'."

    return "\n".join(parts)
