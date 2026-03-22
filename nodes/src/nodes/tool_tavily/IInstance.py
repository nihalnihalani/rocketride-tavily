# =============================================================================
# MIT License
# Copyright (c) 2026 Nihal Nihalani
# =============================================================================

"""
Tavily AI Search tool node instance.

Delegates tool invoke operations to the TavilyDriver.
"""

from __future__ import annotations

from typing import Any

from rocketlib import IInstanceBase

from .IGlobal import IGlobal


class IInstance(IInstanceBase):
    IGlobal: IGlobal

    def invoke(self, param: Any) -> Any:  # noqa: ANN401
        driver = getattr(self.IGlobal, 'driver', None)
        if driver is None:
            raise RuntimeError('tool_tavily: driver not initialized')
        return driver.handle_invoke(param)
