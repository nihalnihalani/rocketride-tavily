# rocketride-tavily

**AI-powered web search, extraction, and crawling for RocketRide pipelines.**

> Give your RocketRide agents the entire internet as a knowledge source.

## The Problem

RocketRide has 50+ pipeline nodes, 13 LLM providers, 8 vector databases, OCR, NER, embeddings, and multi-agent workflows -- but **zero web search capability**.

This means:

- **RAG pipelines are blind to real-time information.** You can query your vector DB, but you can't answer "What happened today?" or "What's the current price of Bitcoin?"
- **Agents can't research.** RocketRide agents have HTTP tools and Firecrawl for scraping, but no way to *discover* relevant URLs. They need a search engine.
- **Grounded answers are impossible.** Without web search, LLM responses rely entirely on training data. No citations, no freshness, no fact-checking.

## What This Adds

A new **Tavily AI Search** tool node that plugs directly into RocketRide's visual pipeline builder. It gives any agent or pipeline access to 4 web capabilities:

| Tool | What It Does | Example Use |
|------|-------------|-------------|
| `tavily.search` | AI-optimized web search with ranked, scored results | "Find recent articles about RocketRide" |
| `tavily.extract` | Extract clean content from URLs | Read the full text of search results |
| `tavily.crawl` | Intelligently crawl websites | Explore documentation sites |
| `tavily.map` | Discover site URL structure | Map a competitor's website |

### Why Tavily?

- **Built for AI agents** -- returns structured JSON with relevance scores, not HTML
- **800K+ developers** -- the most popular AI search API
- **Free tier** -- 1,000 credits/month at [tavily.com](https://tavily.com)
- **Official LangChain partner** -- battle-tested in production AI systems
- **Acquired by Nebius** (Feb 2026) -- backed by serious infrastructure

## Quick Start

### 1. Get a Tavily API key (free)

Sign up at [tavily.com](https://tavily.com) -- 1,000 free credits/month.

### 2. Install the node

Copy the `nodes/src/nodes/tool_tavily/` directory into your RocketRide server's `nodes/src/nodes/` directory:

```bash
cp -r nodes/src/nodes/tool_tavily /path/to/rocketride-server/nodes/src/nodes/
```

Restart the RocketRide server. The Tavily AI Search node will appear in the tool palette.

### 3. Add to a pipeline

1. Open your pipeline in the RocketRide visual builder
2. Drag the **Tavily AI Search** tool node onto the canvas
3. Enter your API key in the node configuration
4. Connect it to any agent node as a tool

The agent can now search the web, extract content, crawl sites, and map URLs.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| API Key | -- | Your Tavily API key ([get free](https://tavily.com)) |
| Search Depth | basic | `basic` (fast) or `advanced` (thorough) |
| Max Results | 5 | Results per search (1-20) |
| Topic | general | `general`, `news`, or `finance` |
| Include AI Answer | off | Add Tavily-generated answer summary |
| Include Images | off | Include image search results |

### Profiles

Three pre-configured profiles for common use cases:

| Profile | Search Depth | Max Results | Topic | Best For |
|---------|-------------|-------------|-------|----------|
| **Default** | basic | 5 | general | General-purpose search |
| **News** | basic | 10 | news | Current events, news monitoring |
| **Deep Research** | advanced | 10 | general | Thorough research with AI answer |

## How It Works

```
User Question
     |
     v
[RocketRide Agent]  <-- decides it needs web info
     |
     v
[Tavily AI Search Tool]
     |
     +-- tavily.search("query")     --> ranked results with scores
     +-- tavily.extract(["urls"])   --> clean page content
     +-- tavily.crawl("url")        --> crawled website pages
     +-- tavily.map("url")          --> discovered URL list
     |
     v
[Agent synthesizes answer with citations]
     |
     v
[Response to user]
```

### Example: Web Research Agent Pipeline

```
[Chat Source] --> [Agent (GPT-4)] --> [Response]
                       |
                  [Tool: Tavily Search]
                  [Tool: Tavily Extract]
```

**User asks:** "What are the latest developments in AI agent frameworks?"

1. Agent calls `tavily.search` with query and `topic=news`
2. Tavily returns 5 ranked results with titles, URLs, content snippets
3. Agent picks top results, calls `tavily.extract` for full page content
4. Agent synthesizes a grounded answer with citations:

> Based on recent web sources:
>
> 1. **CrewAI 3.0** launched with native tool orchestration ([source](https://example.com))
> 2. **LangGraph** added persistent memory ([source](https://example.com))
>
> Sources:
> - [CrewAI 3.0 Launch](https://example.com)
> - [LangGraph Memory](https://example.com)

## Tool API Reference

### tavily.search

Search the web with AI-optimized ranking.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | -- | Search query |
| `topic` | string | No | general | `general`, `news`, `finance` |
| `search_depth` | string | No | basic | `basic` or `advanced` |
| `max_results` | integer | No | 5 | Results to return (1-20) |
| `time_range` | string | No | -- | `day`, `week`, `month`, `year` |
| `include_answer` | boolean | No | false | Include AI answer summary |
| `include_domains` | string[] | No | -- | Only search these domains |
| `exclude_domains` | string[] | No | -- | Exclude these domains |

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "title": "Article Title",
      "url": "https://example.com/article",
      "content": "Relevant snippet from the page...",
      "score": 0.95
    }
  ],
  "result_count": 5,
  "answer": "AI-generated summary (if include_answer=true)"
}
```

### tavily.extract

Extract clean content from URLs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `urls` | string[] | Yes | URLs to extract (max 20) |

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "url": "https://example.com/article",
      "raw_content": "Full markdown content of the page..."
    }
  ],
  "result_count": 1
}
```

### tavily.crawl

Intelligently crawl a website.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | -- | Starting URL |
| `max_depth` | integer | No | 1 | Link depth to follow |
| `max_breadth` | integer | No | 20 | Links per page |
| `limit` | integer | No | 50 | Total page limit |
| `instructions` | string | No | -- | Natural language crawler guidance |

### tavily.map

Discover website URL structure.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | -- | Root URL to map |
| `max_depth` | integer | No | 2 | Depth limit |
| `limit` | integer | No | 100 | Max URLs |

## Architecture

This node follows RocketRide's standard tool node pattern (identical to `tool_firecrawl`):

```
tool_tavily/
  __init__.py          # Dependency loading + exports
  IGlobal.py           # Shared state: reads config, creates TavilyClient + driver
  IInstance.py          # Per-invocation: delegates to driver.handle_invoke()
  tavily_driver.py     # ToolsBase implementation: 4 tools with schemas
  services.json        # Node definition, config fields, profiles
  requirements.txt     # tavily-python
```

**Key design decisions:**
- Extends `ToolsBase` (same as Firecrawl) for consistent tool interface
- All Pydantic models converted to plain dicts before returning (avoids Mistake #19 from RocketRide docs)
- Namespaced tool names (`tavily.search`, not just `search`) to avoid collisions
- Graceful error handling -- returns `{success: false, error: "..."}` instead of crashing
- Zero new dependencies beyond `tavily-python` (MIT, maintained by Tavily/Nebius)

## Example Pipelines

Three ready-to-use `.pipe` files are included in `examples/`:

1. **`web-research-agent.pipe`** -- Chat agent with web search + content extraction
2. **`competitive-intel.pipe`** -- Automated competitive research pipeline
3. **`news-monitor.pipe`** -- News topic monitoring with time-range filtering

## Testing

```bash
# With real API key
TAVILY_API_KEY=tvly-xxx pytest tests/ -v

# Mock mode (no API key needed)
pytest tests/ -v -k "not integration"
```

## Links

- [Tavily Documentation](https://docs.tavily.com)
- [RocketRide Documentation](https://docs.rocketride.org)
- [RocketRide GitHub](https://github.com/rocketride-org/rocketride-server)

## License

MIT

#frontier-tower-hackathon
