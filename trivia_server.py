#!/usr/bin/env python3
"""Bar Trivia Research MCP Server - Aggregate trivia data from DuckDuckGo, Wikipedia, and web sources."""
import os
import sys
import logging
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("trivia-server")

# Initialize MCP server
mcp = FastMCP("trivia")

# === UTILITY FUNCTIONS ===

async def duckduckgo_search(query: str, max_results: int = 5) -> list:
    """Search DuckDuckGo and return results."""
    results = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15, follow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html5lib")
            result_divs = soup.find_all("div", class_="result")
            for div in result_divs[:max_results]:
                title_elem = div.find("a", class_="result__a")
                snippet_elem = div.find("a", class_="result__snippet")
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    results.append({"title": title, "link": link, "snippet": snippet})
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
    return results


async def wikipedia_search(query: str, limit: int = 5) -> list:
    """Search Wikipedia and return matching article titles."""
    results = []
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "opensearch", "search": query, "limit": limit, "format": "json"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if len(data) >= 4:
                titles, descriptions, links = data[1], data[2], data[3]
                for i, title in enumerate(titles):
                    results.append({
                        "title": title,
                        "description": descriptions[i] if i < len(descriptions) else "",
                        "url": links[i] if i < len(links) else ""
                    })
    except Exception as e:
        logger.error(f"Wikipedia search error: {e}")
    return results


async def wikipedia_summary(title: str) -> str:
    """Get Wikipedia article summary."""
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "query", "titles": title, "prop": "extracts", "exintro": True,
                  "explaintext": True, "format": "json", "redirects": 1}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id != "-1":
                    return page.get("extract", "No summary available.")[:2000]
    except Exception as e:
        logger.error(f"Wikipedia summary error: {e}")
    return "Could not fetch summary."


async def fetch_on_this_day(month: int, day: int) -> dict:
    """Fetch On This Day data from Wikipedia API."""
    events = {"events": [], "births": [], "deaths": []}
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{month:02d}/{day:02d}"
        headers = {"User-Agent": "TriviaMCPServer/1.0"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            for event in data.get("events", [])[:10]:
                year = event.get("year", "")
                text = event.get("text", "")
                events["events"].append(f"{year}: {text}")
            for birth in data.get("births", [])[:10]:
                year = birth.get("year", "")
                text = birth.get("text", "")
                events["births"].append(f"{year}: {text}")
            for death in data.get("deaths", [])[:5]:
                year = death.get("year", "")
                text = death.get("text", "")
                events["deaths"].append(f"{year}: {text}")
    except Exception as e:
        logger.error(f"On This Day fetch error: {e}")
    return events


async def fetch_url_content(url: str, max_chars: int = 5000) -> str:
    """Fetch and extract text content from a URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15, follow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html5lib")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            text = " ".join(text.split())
            return text[:max_chars]
    except Exception as e:
        logger.error(f"URL fetch error: {e}")
        return f"Error fetching URL: {str(e)}"


# === MCP TOOLS ===

@mcp.tool()
async def research_trivia_topic(topic: str = "", depth: str = "normal") -> str:
    """Research a specific trivia topic using DuckDuckGo and Wikipedia searches."""
    logger.info(f"Researching trivia topic: {topic}")
    
    if not topic.strip():
        return "❌ Error: Please provide a topic to research"
    
    try:
        output = [f"🔍 TRIVIA RESEARCH: {topic.upper()}", "=" * 50, ""]
        
        # Wikipedia search and summaries
        wiki_results = await wikipedia_search(topic, limit=3)
        if wiki_results:
            output.append("📚 WIKIPEDIA FINDINGS:")
            output.append("-" * 30)
            for result in wiki_results:
                output.append(f"\n**{result['title']}**")
                if result['description']:
                    output.append(f"   {result['description']}")
                summary = await wikipedia_summary(result['title'])
                if summary and summary != "Could not fetch summary.":
                    output.append(f"   Summary: {summary[:800]}...")
            output.append("")
        
        # DuckDuckGo search for additional context
        search_queries = [f"{topic} trivia facts", f"{topic} interesting facts history"]
        ddg_limit = 5 if depth.strip().lower() == "deep" else 3
        
        output.append("🌐 WEB SEARCH RESULTS:")
        output.append("-" * 30)
        
        for query in search_queries:
            ddg_results = await duckduckgo_search(query, max_results=ddg_limit)
            if ddg_results:
                for result in ddg_results:
                    output.append(f"\n• {result['title']}")
                    if result['snippet']:
                        output.append(f"  {result['snippet']}")
        
        output.append("")
        output.append("=" * 50)
        output.append("✅ Research complete! Use these facts for your trivia questions.")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Research error: {e}")
        return f"❌ Error researching topic: {str(e)}"


@mcp.tool()
async def trivia_for_today(date_override: str = "") -> str:
    """Get trivia facts for today including historical events, birthdays, movies, and TV shows."""
    logger.info("Fetching trivia for today")
    
    try:
        if date_override.strip():
            parts = date_override.strip().split("-")
            if len(parts) == 2:
                month, day = int(parts[0]), int(parts[1])
            else:
                return "❌ Error: Date format should be MM-DD (e.g., 12-25)"
        else:
            today = datetime.now()
            month, day = today.month, today.day
        
        output = [f"📅 TRIVIA FOR {month:02d}/{day:02d}", "=" * 50, ""]
        
        # On This Day from Wikipedia
        otd_data = await fetch_on_this_day(month, day)
        
        if otd_data["events"]:
            output.append("🏛️ HISTORICAL EVENTS:")
            output.append("-" * 30)
            for event in otd_data["events"][:8]:
                output.append(f"• {event}")
            output.append("")
        
        if otd_data["births"]:
            output.append("🎂 FAMOUS BIRTHDAYS:")
            output.append("-" * 30)
            for birth in otd_data["births"][:8]:
                output.append(f"• {birth}")
            output.append("")
        
        if otd_data["deaths"]:
            output.append("🕯️ NOTABLE DEATHS:")
            output.append("-" * 30)
            for death in otd_data["deaths"][:5]:
                output.append(f"• {death}")
            output.append("")
        
        # Search for entertainment releases on this date
        month_names = ["", "January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        date_str = f"{month_names[month]} {day}"
        
        output.append("🎬 ENTERTAINMENT ON THIS DATE:")
        output.append("-" * 30)
        
        entertainment_results = await duckduckgo_search(f"movies released {date_str} history", max_results=4)
        for result in entertainment_results:
            output.append(f"• {result['title']}")
            if result['snippet']:
                output.append(f"  {result['snippet'][:150]}")
        
        output.append("")
        output.append("=" * 50)
        output.append("✅ Daily trivia loaded!")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Today trivia error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def trivia_for_week(start_date: str = "") -> str:
    """Get trivia highlights for the current or specified week including events and birthdays."""
    logger.info("Fetching trivia for the week")
    
    try:
        if start_date.strip():
            parts = start_date.strip().split("-")
            if len(parts) == 3:
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                start = datetime(year, month, day)
            else:
                return "❌ Error: Date format should be YYYY-MM-DD (e.g., 2025-01-15)"
        else:
            start = datetime.now()
            start = start - timedelta(days=start.weekday())
        
        output = [f"📆 WEEKLY TRIVIA: Week of {start.strftime('%B %d, %Y')}", "=" * 50, ""]
        
        month_names = ["", "January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        
        # Collect highlights for each day of the week
        weekly_events = []
        weekly_births = []
        
        for i in range(7):
            current = start + timedelta(days=i)
            day_name = current.strftime("%A")
            date_display = current.strftime("%m/%d")
            
            otd_data = await fetch_on_this_day(current.month, current.day)
            
            if otd_data["events"]:
                for event in otd_data["events"][:2]:
                    weekly_events.append(f"[{date_display}] {event}")
            
            if otd_data["births"]:
                for birth in otd_data["births"][:2]:
                    weekly_births.append(f"[{date_display}] {birth}")
        
        if weekly_events:
            output.append("🏛️ KEY HISTORICAL EVENTS THIS WEEK:")
            output.append("-" * 30)
            for event in weekly_events[:14]:
                output.append(f"• {event}")
            output.append("")
        
        if weekly_births:
            output.append("🎂 CELEBRITY BIRTHDAYS THIS WEEK:")
            output.append("-" * 30)
            for birth in weekly_births[:14]:
                output.append(f"• {birth}")
            output.append("")
        
        # Entertainment news for the week
        output.append("🎬 ENTERTAINMENT HIGHLIGHTS:")
        output.append("-" * 30)
        
        week_str = start.strftime("%B %Y")
        ent_results = await duckduckgo_search(f"new movies tv shows {week_str}", max_results=5)
        for result in ent_results:
            output.append(f"• {result['title']}")
        
        output.append("")
        output.append("=" * 50)
        output.append("✅ Weekly trivia compiled!")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Week trivia error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def search_entertainment_trivia(category: str = "", query: str = "") -> str:
    """Search for movie, TV, music, or awards trivia with specified category and query."""
    logger.info(f"Searching entertainment trivia: {category} - {query}")
    
    if not query.strip():
        return "❌ Error: Please provide a search query"
    
    cat = category.strip().lower() if category.strip() else "general"
    
    try:
        output = [f"🎬 ENTERTAINMENT TRIVIA: {query.upper()}", "=" * 50, ""]
        
        # Build search queries based on category
        if cat in ["movie", "movies", "film"]:
            searches = [f"{query} movie trivia facts", f"{query} film behind the scenes"]
            wiki_query = f"{query} film"
        elif cat in ["tv", "television", "show"]:
            searches = [f"{query} tv show trivia", f"{query} television series facts"]
            wiki_query = f"{query} TV series"
        elif cat in ["music", "song", "album"]:
            searches = [f"{query} music trivia facts", f"{query} song history"]
            wiki_query = query
        elif cat in ["oscar", "oscars", "academy", "awards"]:
            searches = [f"{query} Oscar Academy Award trivia", f"{query} award winning"]
            wiki_query = f"{query} Academy Award"
        elif cat in ["emmy", "emmys"]:
            searches = [f"{query} Emmy Award trivia", f"{query} Emmy winning"]
            wiki_query = f"{query} Emmy Award"
        else:
            searches = [f"{query} entertainment trivia", f"{query} pop culture facts"]
            wiki_query = query
        
        # Wikipedia search
        wiki_results = await wikipedia_search(wiki_query, limit=3)
        if wiki_results:
            output.append("📚 WIKIPEDIA:")
            output.append("-" * 30)
            for result in wiki_results[:2]:
                output.append(f"\n**{result['title']}**")
                summary = await wikipedia_summary(result['title'])
                if summary != "Could not fetch summary.":
                    output.append(f"   {summary[:600]}...")
            output.append("")
        
        # Web searches
        output.append("🌐 TRIVIA FACTS:")
        output.append("-" * 30)
        
        for search_query in searches:
            results = await duckduckgo_search(search_query, max_results=4)
            for result in results:
                output.append(f"• {result['title']}")
                if result['snippet']:
                    output.append(f"  {result['snippet'][:200]}")
        
        output.append("")
        output.append("=" * 50)
        output.append("✅ Entertainment trivia found!")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Entertainment search error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def fetch_trivia_from_url(url: str = "") -> str:
    """Fetch and extract trivia-relevant content from a specific URL."""
    logger.info(f"Fetching trivia from URL: {url}")
    
    if not url.strip():
        return "❌ Error: Please provide a URL to fetch"
    
    try:
        content = await fetch_url_content(url.strip(), max_chars=6000)
        
        if content.startswith("Error"):
            return f"❌ {content}"
        
        output = [
            "📄 CONTENT FROM URL",
            "=" * 50,
            f"Source: {url}",
            "-" * 50,
            "",
            content,
            "",
            "=" * 50,
            "✅ Content extracted! Review for trivia-worthy facts."
        ]
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"URL fetch error: {e}")
        return f"❌ Error fetching URL: {str(e)}"


@mcp.tool()
async def search_sports_trivia(sport: str = "", query: str = "") -> str:
    """Search for sports trivia including teams, players, records, and championships."""
    logger.info(f"Searching sports trivia: {sport} - {query}")
    
    if not query.strip():
        return "❌ Error: Please provide a search query"
    
    sport_type = sport.strip().lower() if sport.strip() else ""
    
    try:
        output = [f"🏆 SPORTS TRIVIA: {query.upper()}", "=" * 50, ""]
        
        # Build sport-specific searches
        if sport_type in ["nfl", "football"]:
            searches = [f"{query} NFL football trivia", f"{query} Super Bowl history"]
        elif sport_type in ["nba", "basketball"]:
            searches = [f"{query} NBA basketball trivia", f"{query} NBA championship"]
        elif sport_type in ["mlb", "baseball"]:
            searches = [f"{query} MLB baseball trivia", f"{query} World Series"]
        elif sport_type in ["nhl", "hockey"]:
            searches = [f"{query} NHL hockey trivia", f"{query} Stanley Cup"]
        elif sport_type in ["soccer", "football", "mls", "premier"]:
            searches = [f"{query} soccer football trivia", f"{query} World Cup"]
        elif sport_type in ["olympics", "olympic"]:
            searches = [f"{query} Olympic trivia", f"{query} Olympic medal history"]
        else:
            searches = [f"{query} sports trivia facts", f"{query} sports history records"]
        
        # Wikipedia search
        wiki_results = await wikipedia_search(query, limit=3)
        if wiki_results:
            output.append("📚 WIKIPEDIA:")
            output.append("-" * 30)
            for result in wiki_results[:2]:
                output.append(f"\n**{result['title']}**")
                summary = await wikipedia_summary(result['title'])
                if summary != "Could not fetch summary.":
                    output.append(f"   {summary[:600]}...")
            output.append("")
        
        # Web searches
        output.append("🌐 SPORTS FACTS:")
        output.append("-" * 30)
        
        for search_query in searches:
            results = await duckduckgo_search(search_query, max_results=4)
            for result in results:
                output.append(f"• {result['title']}")
                if result['snippet']:
                    output.append(f"  {result['snippet'][:200]}")
        
        output.append("")
        output.append("=" * 50)
        output.append("✅ Sports trivia compiled!")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Sports search error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def search_geography_trivia(query: str = "", category: str = "") -> str:
    """Search for geography trivia including countries, capitals, landmarks, and world facts."""
    logger.info(f"Searching geography trivia: {query}")
    
    if not query.strip():
        return "❌ Error: Please provide a geography query"
    
    cat = category.strip().lower() if category.strip() else ""
    
    try:
        output = [f"🌍 GEOGRAPHY TRIVIA: {query.upper()}", "=" * 50, ""]
        
        # Build category-specific searches
        if cat in ["capital", "capitals"]:
            searches = [f"{query} capital city trivia", f"{query} capital facts"]
        elif cat in ["landmark", "landmarks", "wonder"]:
            searches = [f"{query} landmark trivia facts", f"{query} famous places"]
        elif cat in ["country", "countries", "nation"]:
            searches = [f"{query} country facts trivia", f"{query} nation history"]
        elif cat in ["flag", "flags"]:
            searches = [f"{query} flag trivia facts", f"{query} flag history meaning"]
        else:
            searches = [f"{query} geography trivia", f"{query} world facts"]
        
        # Wikipedia search
        wiki_results = await wikipedia_search(query, limit=3)
        if wiki_results:
            output.append("📚 WIKIPEDIA:")
            output.append("-" * 30)
            for result in wiki_results[:2]:
                output.append(f"\n**{result['title']}**")
                summary = await wikipedia_summary(result['title'])
                if summary != "Could not fetch summary.":
                    output.append(f"   {summary[:700]}...")
            output.append("")
        
        # Web searches
        output.append("🌐 GEOGRAPHY FACTS:")
        output.append("-" * 30)
        
        for search_query in searches:
            results = await duckduckgo_search(search_query, max_results=4)
            for result in results:
                output.append(f"• {result['title']}")
                if result['snippet']:
                    output.append(f"  {result['snippet'][:200]}")
        
        output.append("")
        output.append("=" * 50)
        output.append("✅ Geography trivia compiled!")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Geography search error: {e}")
        return f"❌ Error: {str(e)}"


@mcp.tool()
async def search_science_trivia(field: str = "", query: str = "") -> str:
    """Search for science and technology trivia including discoveries, inventions, and facts."""
    logger.info(f"Searching science trivia: {field} - {query}")
    
    if not query.strip():
        return "❌ Error: Please provide a science query"
    
    field_type = field.strip().lower() if field.strip() else ""
    
    try:
        output = [f"🔬 SCIENCE TRIVIA: {query.upper()}", "=" * 50, ""]
        
        # Build field-specific searches
        if field_type in ["space", "astronomy", "nasa"]:
            searches = [f"{query} space astronomy trivia", f"{query} NASA facts"]
        elif field_type in ["biology", "nature", "animal"]:
            searches = [f"{query} biology nature trivia", f"{query} animal facts"]
        elif field_type in ["chemistry", "element"]:
            searches = [f"{query} chemistry trivia", f"{query} element facts"]
        elif field_type in ["physics"]:
            searches = [f"{query} physics trivia facts", f"{query} science discovery"]
        elif field_type in ["tech", "technology", "computer"]:
            searches = [f"{query} technology trivia", f"{query} invention history"]
        else:
            searches = [f"{query} science trivia facts", f"{query} scientific discovery"]
        
        # Wikipedia search
        wiki_results = await wikipedia_search(query, limit=3)
        if wiki_results:
            output.append("📚 WIKIPEDIA:")
            output.append("-" * 30)
            for result in wiki_results[:2]:
                output.append(f"\n**{result['title']}**")
                summary = await wikipedia_summary(result['title'])
                if summary != "Could not fetch summary.":
                    output.append(f"   {summary[:700]}...")
            output.append("")
        
        # Web searches
        output.append("🌐 SCIENCE FACTS:")
        output.append("-" * 30)
        
        for search_query in searches:
            results = await duckduckgo_search(search_query, max_results=4)
            for result in results:
                output.append(f"• {result['title']}")
                if result['snippet']:
                    output.append(f"  {result['snippet'][:200]}")
        
        output.append("")
        output.append("=" * 50)
        output.append("✅ Science trivia compiled!")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Science search error: {e}")
        return f"❌ Error: {str(e)}"


# === SERVER STARTUP ===
if __name__ == "__main__":
    logger.info("Starting Bar Trivia Research MCP server...")
    
    try:
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
