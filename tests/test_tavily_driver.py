"""Unit tests for the Tavily driver (no API key required)."""

import pytest
from unittest.mock import MagicMock

import sys
import os

# Add the node source to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nodes', 'src', 'nodes'))


class TestTavilyDriverToolQuery:
    """Test tool discovery and schema correctness."""

    def _make_driver(self):
        from tool_tavily.tavily_driver import TavilyDriver
        mock_client = MagicMock()
        return TavilyDriver(server_name='tavily', client=mock_client)

    def test_returns_four_tools(self):
        driver = self._make_driver()
        tools = driver._tool_query()
        assert len(tools) == 4

    def test_tool_names_are_namespaced(self):
        driver = self._make_driver()
        tools = driver._tool_query()
        names = [t['name'] for t in tools]
        assert 'tavily.search' in names
        assert 'tavily.extract' in names
        assert 'tavily.research' in names
        assert 'tavily.map' in names

    def test_custom_server_name(self):
        from tool_tavily.tavily_driver import TavilyDriver
        driver = TavilyDriver(server_name='websearch', client=MagicMock())
        tools = driver._tool_query()
        names = [t['name'] for t in tools]
        assert 'websearch.search' in names

    def test_all_tools_have_input_schema(self):
        driver = self._make_driver()
        for tool in driver._tool_query():
            assert 'inputSchema' in tool
            assert 'properties' in tool['inputSchema']

    def test_search_requires_query(self):
        driver = self._make_driver()
        tools = driver._tool_query()
        search = [t for t in tools if t['name'] == 'tavily.search'][0]
        assert 'query' in search['inputSchema']['required']


class TestTavilyDriverValidation:
    """Test input validation."""

    def _make_driver(self):
        from tool_tavily.tavily_driver import TavilyDriver
        return TavilyDriver(server_name='tavily', client=MagicMock())

    def test_search_validates_missing_query(self):
        driver = self._make_driver()
        with pytest.raises(ValueError, match='missing required fields'):
            driver._tool_validate(tool_name='tavily.search', input_obj={})

    def test_extract_validates_missing_urls(self):
        driver = self._make_driver()
        with pytest.raises(ValueError, match='missing required fields'):
            driver._tool_validate(tool_name='tavily.extract', input_obj={})

    def test_research_validates_missing_query(self):
        driver = self._make_driver()
        with pytest.raises(ValueError, match='missing required fields'):
            driver._tool_validate(tool_name='tavily.research', input_obj={})

    def test_unknown_tool_raises(self):
        driver = self._make_driver()
        with pytest.raises(ValueError, match='Unknown tool'):
            driver._tool_validate(tool_name='tavily.unknown', input_obj={})

    def test_valid_search_passes(self):
        driver = self._make_driver()
        driver._tool_validate(tool_name='tavily.search', input_obj={'query': 'test'})

    def test_bare_name_stripping(self):
        driver = self._make_driver()
        assert driver._bare_name('tavily.search') == 'search'
        assert driver._bare_name('search') == 'search'


class TestTavilyDriverInvoke:
    """Test tool invocation with mocked SDK."""

    def _make_driver(self):
        from tool_tavily.tavily_driver import TavilyDriver
        mock_client = MagicMock()
        mock_client.search.return_value = {
            'results': [
                {'title': 'Test', 'url': 'https://example.com', 'content': 'Hello', 'score': 0.9}
            ],
            'answer': 'Test answer',
        }
        mock_client.extract.return_value = {
            'results': [
                {'url': 'https://example.com', 'raw_content': 'Full content here'}
            ]
        }
        mock_client.map.return_value = {
            'urls': ['https://example.com/a', 'https://example.com/b']
        }
        return TavilyDriver(server_name='tavily', client=mock_client), mock_client

    def test_search_returns_results(self):
        driver, _ = self._make_driver()
        result = driver._tool_invoke(tool_name='tavily.search', input_obj={'query': 'test'})
        assert result['success'] is True
        assert result['result_count'] == 1
        assert result['results'][0]['title'] == 'Test'

    def test_search_passes_params(self):
        driver, mock = self._make_driver()
        driver._tool_invoke(
            tool_name='tavily.search',
            input_obj={'query': 'test', 'topic': 'news', 'max_results': 10},
        )
        mock.search.assert_called_once()
        call_kwargs = mock.search.call_args[1]
        assert call_kwargs['query'] == 'test'
        assert call_kwargs['topic'] == 'news'
        assert call_kwargs['max_results'] == 10

    def test_extract_returns_content(self):
        driver, _ = self._make_driver()
        result = driver._tool_invoke(
            tool_name='tavily.extract',
            input_obj={'urls': ['https://example.com']},
        )
        assert result['success'] is True
        assert result['results'][0]['raw_content'] == 'Full content here'

    def test_map_returns_urls(self):
        driver, _ = self._make_driver()
        result = driver._tool_invoke(
            tool_name='tavily.map',
            input_obj={'url': 'https://example.com'},
        )
        assert result['success'] is True
        assert len(result['urls']) == 2

    def test_search_handles_sdk_error(self):
        from tool_tavily.tavily_driver import TavilyDriver
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception('Invalid API key')
        driver = TavilyDriver(server_name='tavily', client=mock_client)
        result = driver._tool_invoke(tool_name='tavily.search', input_obj={'query': 'test'})
        assert result['success'] is False
        assert 'Invalid API key' in result['error']

    def test_time_range_conversion(self):
        from tool_tavily.tavily_driver import _time_range_to_days
        assert _time_range_to_days('day') == 1
        assert _time_range_to_days('week') == 7
        assert _time_range_to_days('month') == 30
        assert _time_range_to_days('year') == 365


class TestNormalizeToolInput:
    """Test the input normalization helper."""

    def test_none_returns_empty_dict(self):
        from tool_tavily.tavily_driver import _normalize_tool_input
        assert _normalize_tool_input(None) == {}

    def test_dict_passes_through(self):
        from tool_tavily.tavily_driver import _normalize_tool_input
        assert _normalize_tool_input({'query': 'test'}) == {'query': 'test'}

    def test_json_string_parsed(self):
        from tool_tavily.tavily_driver import _normalize_tool_input
        result = _normalize_tool_input('{"query": "test"}')
        assert result == {'query': 'test'}

    def test_unwraps_input_wrapper(self):
        from tool_tavily.tavily_driver import _normalize_tool_input
        result = _normalize_tool_input({'input': {'query': 'test'}})
        assert result == {'query': 'test'}

    def test_strips_security_context(self):
        from tool_tavily.tavily_driver import _normalize_tool_input
        result = _normalize_tool_input({'query': 'test', 'security_context': 'secret'})
        assert 'security_context' not in result
