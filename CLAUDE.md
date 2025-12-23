# CLAUDE.md - Bar Trivia Research MCP Server

## Overview

This is a Model Context Protocol (MCP) server designed to help prepare for bar trivia nights by aggregating data from multiple sources: DuckDuckGo search, Wikipedia API, and direct URL fetching.

## Implementation Details

### Server Architecture

- **Framework**: FastMCP from mcp.server.fastmcp
- **Transport**: stdio (standard input/output)
- **Dependencies**: httpx (async HTTP), beautifulsoup4 (HTML parsing), html5lib (HTML5 parser)
- **No authentication required**: Uses free public APIs only

### Tool Inventory

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `research_trivia_topic` | Deep-dive research on any topic | `topic`, `depth` (normal/deep) |
| `trivia_for_today` | Daily historical events and birthdays | `date_override` (MM-DD format) |
| `trivia_for_week` | Weekly trivia compilation | `start_date` (YYYY-MM-DD format) |
| `search_entertainment_trivia` | Movies, TV, music, awards | `category`, `query` |
| `search_sports_trivia` | NFL, NBA, MLB, NHL, Olympics | `sport`, `query` |
| `search_geography_trivia` | Countries, capitals, landmarks | `query`, `category` |
| `search_science_trivia` | Space, biology, physics, tech | `field`, `query` |
| `fetch_trivia_from_url` | Extract content from URLs | `url` |

### Data Sources

1. **Wikipedia REST API** (`en.wikipedia.org/api/rest_v1/`)
   - On This Day events, births, deaths
   - Article summaries and extracts

2. **Wikipedia OpenSearch** (`en.wikipedia.org/w/api.php`)
   - Article title search
   - Article content retrieval

3. **DuckDuckGo HTML Search** (`html.duckduckgo.com/html/`)
   - Web search results with snippets
   - No API key required

### Design Decisions

1. **Single-line docstrings**: Required to prevent MCP gateway panic errors
2. **String parameters with empty defaults**: Avoids None/Optional type issues
3. **Async/await pattern**: All HTTP calls are non-blocking
4. **Graceful error handling**: Returns user-friendly error messages
5. **Output formatting**: Uses emojis and clear section headers

### Category Mappings

**Entertainment categories**: movie, movies, film, tv, television, show, music, song, album, oscar, oscars, academy, awards, emmy, emmys

**Sports categories**: nfl, football, nba, basketball, mlb, baseball, nhl, hockey, soccer, mls, premier, olympics, olympic

**Geography categories**: capital, capitals, landmark, landmarks, wonder, country, countries, nation, flag, flags

**Science categories**: space, astronomy, nasa, biology, nature, animal, chemistry, element, physics, tech, technology, computer

## Building and Running

```bash
# Build Docker image
docker build -t trivia-mcp-server .

# Test locally
python trivia_server.py

# View logs
docker logs <container_name>
```

## Known Limitations

1. DuckDuckGo may rate limit excessive requests
2. Wikipedia API returns English content only
3. URL fetch limited to 6000 characters
4. Some websites block automated fetching

## Extension Ideas

- Add support for specific trivia databases
- Integrate music charts API for current hits
- Add movie release calendar integration
- Support for other languages via Wikipedia language switching
