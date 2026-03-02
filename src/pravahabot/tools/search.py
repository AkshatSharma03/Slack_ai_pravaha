"""Web search via DuckDuckGo — no API key required."""
import requests


def search_web(query: str) -> str:
    """Search the web and return the top results as formatted text."""
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                results.append(f"**{title}**\n{body}\n{href}")

        if results:
            return f"Search results for '{query}':\n\n" + "\n\n---\n\n".join(results)
        return f"No results found for: {query}"

    except ImportError:
        return _ddg_html_fallback(query)
    except Exception as e:
        fallback = _ddg_html_fallback(query)
        return fallback if fallback else f"Search failed: {str(e)}"


def _ddg_html_fallback(query: str) -> str:
    """Fallback: scrape DuckDuckGo HTML results."""
    try:
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        }
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for result in soup.find_all("div", class_="result", limit=5):
            title_el = result.find("a", class_="result__a")
            snippet_el = result.find("a", class_="result__snippet")
            if title_el and snippet_el:
                results.append(
                    f"**{title_el.get_text(strip=True)}**\n"
                    f"{snippet_el.get_text(strip=True)}"
                )

        return "\n\n---\n\n".join(results) if results else f"No results for: {query}"
    except Exception as e:
        return f"Search unavailable: {str(e)}"
