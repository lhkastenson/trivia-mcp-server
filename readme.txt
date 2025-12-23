# Bar Trivia Research MCP Server

A Model Context Protocol (MCP) server that aggregates trivia data from DuckDuckGo, Wikipedia, and web sources for bar trivia preparation.

## Purpose

This MCP server provides a secure interface for AI assistants to research and compile trivia facts across multiple categories including history, entertainment, sports, geography, and science. Perfect for preparing for bar trivia nights!

## Features

### Current Implementation

- **`research_trivia_topic`** - Deep research on any specific trivia topic using Wikipedia and web searches
- **`trivia_for_today`** - Get historical events, famous birthdays, and entertainment facts for today's date
- **`trivia_for_week`** - Compile weekly trivia highlights including events and celebrity birthdays
- **`search_entertainment_trivia`** - Search movies, TV shows, music, Oscars, and Emmy trivia
- **`search_sports_trivia`** - Search NFL, NBA, MLB, NHL, soccer, and Olympics trivia
- **`search_geography_trivia`** - Search countries, capitals, landmarks, and world facts
- **`search_science_trivia`** - Search space, biology, chemistry, physics, and technology trivia
- **`fetch_trivia_from_url`** - Extract trivia-relevant content from any URL

## Prerequisites

- Docker Desktop with MCP Toolkit enabled
- Docker MCP CLI plugin (`docker mcp` command)

## Installation

See the step-by-step instructions provided below.

## Usage Examples

In Claude Desktop, you can ask:

- "Research trivia about the Roman Empire"
- "What historical events happened on this day?"
- "Get trivia for this week's bar trivia night"
- "Find Oscar trivia about Leonardo DiCaprio"
- "Search NFL Super Bowl trivia"
- "What are some interesting facts about Mount Everest?"
- "Find space trivia about black holes"
- "Fetch trivia from this URL: https://example.com/trivia"

## Architecture

Claude Desktop → MCP Gateway → Trivia MCP Server → DuckDuckGo/Wikipedia/Web
                                    ↓
                            Docker Container
                            (No secrets required)

## Data Sources

This server aggregates data from:
1. **Wikipedia API** - Article summaries, On This Day events, birthdays
2. **DuckDuckGo Search** - Web search results for trivia facts
3. **Direct URL Fetch** - Extract content from any accessible webpage

## Development

### Local Testing

```bash
# Run directly (no API keys needed)
python trivia_server.py

# Test MCP protocol
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python trivia_server.py
```

### Adding New Tools

1. Add the function to trivia_server.py
2. Decorate with @mcp.tool()
3. Use SINGLE-LINE docstrings only
4. Update the catalog entry with the new tool name
5. Rebuild the Docker image

## Troubleshooting

### Tools Not Appearing

1. Verify Docker image built successfully
2. Check catalog and registry files
3. Ensure Claude Desktop config includes custom catalog
4. Restart Claude Desktop

### Search Results Empty

1. Check network connectivity in Docker container
2. Verify DuckDuckGo and Wikipedia APIs are accessible
3. Try simpler search queries

### Rate Limiting

- DuckDuckGo may rate limit excessive requests
- Wikipedia API has reasonable limits
- Space out rapid successive queries

## Security Considerations

- No API keys or secrets required
- Running as non-root user in container
- No sensitive data logged
- Read-only data retrieval only

## License

MIT License
