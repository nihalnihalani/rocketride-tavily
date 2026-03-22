# =============================================================================
# MIT License
# Copyright (c) 2026 Nihal Nihalani
# =============================================================================

"""
Tavily AI Search tool node - global (shared) state.

Reads the Tavily API key from config, creates a TavilyClient,
and builds a TavilyDriver that implements the ToolsBase interface.
"""

from __future__ import annotations

from ai.common.config import Config
from rocketlib import IGlobalBase, OPEN_MODE, warning

from tavily import TavilyClient

from .tavily_driver import TavilyDriver


class IGlobal(IGlobalBase):
    """Global state for tool_tavily."""

    driver: TavilyDriver | None = None

    def beginGlobal(self) -> None:
        if self.IEndpoint.endpoint.openMode == OPEN_MODE.CONFIG:
            return

        cfg = Config.getNodeConfig(self.glb.logicalType, self.glb.connConfig)

        apikey = str((cfg.get('apikey') or '')).strip()

        if not apikey:
            raise Exception('tool_tavily: apikey is required. Get a free key at https://tavily.com')

        server_name = str(cfg.get('serverName') or 'tavily').strip()
        search_depth = str(cfg.get('searchDepth') or 'basic').strip()
        max_results = int(cfg.get('maxResults') or 5)
        topic = str(cfg.get('topic') or 'general').strip()
        include_answer = bool(cfg.get('includeAnswer', False))
        include_images = bool(cfg.get('includeImages', False))

        try:
            client = TavilyClient(api_key=apikey)
            self.driver = TavilyDriver(
                server_name=server_name,
                client=client,
                default_search_depth=search_depth,
                default_max_results=max_results,
                default_topic=topic,
                default_include_answer=include_answer,
                default_include_images=include_images,
            )
        except Exception as e:
            warning(str(e))
            raise

    def validateConfig(self) -> None:
        try:
            cfg = Config.getNodeConfig(self.glb.logicalType, self.glb.connConfig)
            apikey = str((cfg.get('apikey') or '')).strip()
            if not apikey:
                warning('apikey is required')
        except Exception as e:
            warning(str(e))

    def endGlobal(self) -> None:
        self.driver = None
