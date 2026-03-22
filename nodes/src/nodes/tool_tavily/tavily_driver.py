"""
Tavily AI Search tool-provider driver.

Implements `tool.query`, `tool.validate`, and `tool.invoke` for four Tavily
operations: search, extract, crawl, and map.  Follows the same ToolsBase
pattern as tool_firecrawl.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from rocketlib import warning

from ai.common.tools import ToolsBase


# ---------------------------------------------------------------------------
# Static tool definitions
# ---------------------------------------------------------------------------

SEARCH_TOOL = {
    'name': 'search',
    'description': (
        'Search the web using Tavily AI search. Returns ranked results with '
        'title, URL, content snippet, and relevance score. Optimized for AI '
        'agents and RAG pipelines. Supports topic filtering (general, news, '
        'finance) and time-range filtering.'
    ),
    'inputSchema': {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'The search query.',
            },
            'topic': {
                'type': 'string',
                'enum': ['general', 'news', 'finance'],
                'description': 'Search category. Default: general.',
            },
            'search_depth': {
                'type': 'string',
                'enum': ['basic', 'advanced'],
                'description': 'basic = fast, advanced = more thorough and relevant.',
            },
            'max_results': {
                'type': 'integer',
                'description': 'Maximum number of results (1-20). Default: 5.',
            },
            'time_range': {
                'type': 'string',
                'enum': ['day', 'week', 'month', 'year'],
                'description': 'Filter results by recency.',
            },
            'include_answer': {
                'type': 'boolean',
                'description': 'Include a Tavily-generated AI answer summary.',
            },
            'include_domains': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Only include results from these domains.',
            },
            'exclude_domains': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Exclude results from these domains.',
            },
        },
        'required': ['query'],
    },
}

EXTRACT_TOOL = {
    'name': 'extract',
    'description': (
        'Extract clean, readable content from one or more URLs. Returns '
        'markdown or text content suitable for LLM processing. Useful for '
        'reading full articles after finding them via search.'
    ),
    'inputSchema': {
        'type': 'object',
        'properties': {
            'urls': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'URLs to extract content from (max 20).',
            },
        },
        'required': ['urls'],
    },
}

CRAWL_TOOL = {
    'name': 'crawl',
    'description': (
        'Intelligently crawl a website starting from a URL. Follows links '
        'and extracts content from discovered pages. Supports natural '
        'language instructions to guide the crawler.'
    ),
    'inputSchema': {
        'type': 'object',
        'properties': {
            'url': {
                'type': 'string',
                'description': 'Starting URL to crawl.',
            },
            'max_depth': {
                'type': 'integer',
                'description': 'Maximum link depth to follow. Default: 1.',
            },
            'max_breadth': {
                'type': 'integer',
                'description': 'Maximum links to follow per page. Default: 20.',
            },
            'limit': {
                'type': 'integer',
                'description': 'Total page limit. Default: 50.',
            },
            'instructions': {
                'type': 'string',
                'description': 'Natural language guidance for the crawler.',
            },
        },
        'required': ['url'],
    },
}

MAP_TOOL = {
    'name': 'map',
    'description': (
        "Discover a website's URL structure. Returns a list of all "
        'discovered URLs without extracting content. Useful for site '
        'reconnaissance before targeted extraction.'
    ),
    'inputSchema': {
        'type': 'object',
        'properties': {
            'url': {
                'type': 'string',
                'description': 'Root URL to map.',
            },
            'max_depth': {
                'type': 'integer',
                'description': 'Maximum depth. Default: 2.',
            },
            'limit': {
                'type': 'integer',
                'description': 'Maximum URLs to return. Default: 100.',
            },
        },
        'required': ['url'],
    },
}

_TOOLS_BY_BARE_NAME: Dict[str, Dict[str, Any]] = {
    'search': SEARCH_TOOL,
    'extract': EXTRACT_TOOL,
    'crawl': CRAWL_TOOL,
    'map': MAP_TOOL,
}


class TavilyDriver(ToolsBase):
    """Tool provider for Tavily search, extract, crawl, and map."""

    def __init__(
        self,
        *,
        server_name: str,
        client: Any,
        default_search_depth: str = 'basic',
        default_max_results: int = 5,
        default_topic: str = 'general',
        default_include_answer: bool = False,
        default_include_images: bool = False,
    ) -> None:
        self._server_name = (server_name or '').strip() or 'tavily'
        self._client = client
        self._default_search_depth = default_search_depth
        self._default_max_results = default_max_results
        self._default_topic = default_topic
        self._default_include_answer = default_include_answer
        self._default_include_images = default_include_images

    def _bare_name(self, tool_name: str) -> str:
        """Strip server prefix, accepting both bare and namespaced tool names."""
        prefix = f'{self._server_name}.'
        return tool_name[len(prefix):] if tool_name.startswith(prefix) else tool_name

    # ------------------------------------------------------------------
    # ToolsBase hooks
    # ------------------------------------------------------------------

    def _tool_query(self) -> List[ToolsBase.ToolDescriptor]:
        return [
            {**tool, 'name': f'{self._server_name}.{tool["name"]}'}
            for tool in _TOOLS_BY_BARE_NAME.values()
        ]

    def _tool_validate(self, *, tool_name: str, input_obj: Any) -> None:  # noqa: ANN401
        tool = _TOOLS_BY_BARE_NAME.get(self._bare_name(tool_name))
        if tool is None:
            raise ValueError(f'Unknown tool {tool_name}')

        schema = tool.get('inputSchema') or {}
        required = schema.get('required', [])
        if not required:
            return
        if not isinstance(input_obj, dict):
            raise ValueError(f'Tool input must be an object; required fields={required}')
        missing = [k for k in required if k not in input_obj]
        if missing:
            raise ValueError(f'Tool input missing required fields: {missing}')

    def _tool_invoke(self, *, tool_name: str, input_obj: Any) -> Any:  # noqa: ANN401
        args = _normalize_tool_input(input_obj)
        bare = self._bare_name(tool_name)

        if bare == 'search':
            return self._invoke_search(args)
        elif bare == 'extract':
            return self._invoke_extract(args)
        elif bare == 'crawl':
            return self._invoke_crawl(args)
        elif bare == 'map':
            return self._invoke_map(args)
        else:
            raise ValueError(f'Unknown tool {tool_name}')

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _invoke_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get('query')
        if not query:
            raise ValueError('search requires a `query` parameter')

        kwargs: Dict[str, Any] = {
            'query': query,
            'search_depth': args.get('search_depth', self._default_search_depth),
            'max_results': args.get('max_results', self._default_max_results),
            'topic': args.get('topic', self._default_topic),
            'include_answer': args.get('include_answer', self._default_include_answer),
            'include_images': args.get('include_images', self._default_include_images),
        }

        if 'time_range' in args:
            kwargs['days'] = _time_range_to_days(args['time_range'])
        if 'include_domains' in args:
            kwargs['include_domains'] = args['include_domains']
        if 'exclude_domains' in args:
            kwargs['exclude_domains'] = args['exclude_domains']

        try:
            result = self._client.search(**kwargs)
        except Exception as e:
            return {'success': False, 'error': str(e)}

        return _normalize_search_response(result)

    def _invoke_extract(self, args: Dict[str, Any]) -> Dict[str, Any]:
        urls = args.get('urls')
        if not urls or not isinstance(urls, list):
            raise ValueError('extract requires a `urls` array parameter')

        try:
            result = self._client.extract(urls=urls)
        except Exception as e:
            return {'success': False, 'error': str(e)}

        return _normalize_extract_response(result)

    def _invoke_crawl(self, args: Dict[str, Any]) -> Dict[str, Any]:
        url = args.get('url')
        if not url:
            raise ValueError('crawl requires a `url` parameter')

        kwargs: Dict[str, Any] = {'url': url}
        if 'max_depth' in args:
            kwargs['max_depth'] = args['max_depth']
        if 'max_breadth' in args:
            kwargs['max_breadth'] = args['max_breadth']
        if 'limit' in args:
            kwargs['limit'] = args['limit']
        if 'instructions' in args:
            kwargs['instructions'] = args['instructions']

        try:
            result = self._client.crawl(**kwargs)
        except Exception as e:
            return {'success': False, 'error': str(e)}

        return _normalize_crawl_response(result)

    def _invoke_map(self, args: Dict[str, Any]) -> Dict[str, Any]:
        url = args.get('url')
        if not url:
            raise ValueError('map requires a `url` parameter')

        kwargs: Dict[str, Any] = {'url': url}
        if 'max_depth' in args:
            kwargs['max_depth'] = args['max_depth']
        if 'limit' in args:
            kwargs['limit'] = args['limit']

        try:
            result = self._client.map(**kwargs)
        except Exception as e:
            return {'success': False, 'error': str(e)}

        return _normalize_map_response(result)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _time_range_to_days(time_range: str) -> int:
    """Convert time range string to number of days for Tavily API."""
    mapping = {'day': 1, 'week': 7, 'month': 30, 'year': 365}
    return mapping.get(time_range, 7)


def _normalize_search_response(result: Any) -> Dict[str, Any]:
    """Normalize Tavily search response to a plain dict."""
    if isinstance(result, dict):
        data = result
    elif hasattr(result, 'model_dump'):
        data = result.model_dump(exclude_none=True)
    elif hasattr(result, '__dict__'):
        data = result.__dict__
    else:
        data = {'raw': str(result)}

    results = []
    for r in data.get('results', []):
        item = r if isinstance(r, dict) else (r.model_dump(exclude_none=True) if hasattr(r, 'model_dump') else {'raw': str(r)})
        results.append({
            'title': item.get('title', ''),
            'url': item.get('url', ''),
            'content': item.get('content', ''),
            'score': item.get('score', 0),
        })

    response: Dict[str, Any] = {
        'success': True,
        'results': results,
        'result_count': len(results),
    }

    if data.get('answer'):
        response['answer'] = data['answer']
    if data.get('images'):
        response['images'] = data['images']

    return response


def _normalize_extract_response(result: Any) -> Dict[str, Any]:
    """Normalize Tavily extract response."""
    if isinstance(result, dict):
        data = result
    elif hasattr(result, 'model_dump'):
        data = result.model_dump(exclude_none=True)
    elif hasattr(result, '__dict__'):
        data = result.__dict__
    else:
        data = {'raw': str(result)}

    extracted = []
    for r in data.get('results', []):
        item = r if isinstance(r, dict) else (r.model_dump(exclude_none=True) if hasattr(r, 'model_dump') else {'raw': str(r)})
        extracted.append({
            'url': item.get('url', ''),
            'raw_content': item.get('raw_content', ''),
        })

    return {
        'success': True,
        'results': extracted,
        'result_count': len(extracted),
    }


def _normalize_crawl_response(result: Any) -> Dict[str, Any]:
    """Normalize Tavily crawl response."""
    if isinstance(result, dict):
        data = result
    elif hasattr(result, 'model_dump'):
        data = result.model_dump(exclude_none=True)
    elif hasattr(result, '__dict__'):
        data = result.__dict__
    else:
        data = {'raw': str(result)}

    pages = []
    for r in data.get('results', data.get('pages', [])):
        item = r if isinstance(r, dict) else (r.model_dump(exclude_none=True) if hasattr(r, 'model_dump') else {'raw': str(r)})
        pages.append({
            'url': item.get('url', ''),
            'content': item.get('raw_content', item.get('content', '')),
            'metadata': item.get('metadata', {}),
        })

    return {
        'success': True,
        'pages': pages,
        'page_count': len(pages),
    }


def _normalize_map_response(result: Any) -> Dict[str, Any]:
    """Normalize Tavily map response."""
    urls: list = []

    if isinstance(result, dict):
        urls = result.get('urls', result.get('links', []))
    elif hasattr(result, 'model_dump'):
        data = result.model_dump(exclude_none=True)
        urls = data.get('urls', data.get('links', []))
    elif isinstance(result, list):
        urls = result
    elif hasattr(result, 'urls'):
        urls = list(result.urls)
    elif hasattr(result, 'links'):
        urls = list(result.links)

    # Ensure all items are strings
    urls = [str(u.url if hasattr(u, 'url') else u) for u in urls]

    return {
        'success': True,
        'urls': urls,
        'url_count': len(urls),
    }


def _normalize_tool_input(input_obj: Any) -> Dict[str, Any]:
    """Normalize tool input into a plain dict (handles Pydantic, JSON strings, wrappers)."""
    if input_obj is None:
        return {}

    if hasattr(input_obj, 'model_dump') and callable(getattr(input_obj, 'model_dump')):
        input_obj = input_obj.model_dump()
    elif hasattr(input_obj, 'dict') and callable(getattr(input_obj, 'dict')):
        input_obj = input_obj.dict()

    if isinstance(input_obj, str):
        try:
            parsed = json.loads(input_obj)
            if isinstance(parsed, dict):
                input_obj = parsed
        except Exception:
            pass

    if not isinstance(input_obj, dict):
        warning(f'tavily: unexpected input type {type(input_obj).__name__}: {input_obj!r}')
        return {}

    if 'input' in input_obj and isinstance(input_obj['input'], dict):
        inner = input_obj['input']
        extras = {k: v for k, v in input_obj.items() if k != 'input'}
        input_obj = {**inner, **extras}

    input_obj.pop('security_context', None)

    return input_obj
