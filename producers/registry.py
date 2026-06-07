"""Producer registry — maps a source name to its producer class.

Classes are referenced lazily (by module path) so that importing the
registry never imports Selenium/jobspy; the heavy deps load only when a
browser-based producer is actually instantiated.
"""
from __future__ import annotations

import importlib
from typing import Type

from producers.base import BaseProducer

# source name -> "module:ClassName"
_REGISTRY: dict[str, str] = {
    "wuzzuf": "producers.sources.wuzzuf:WuzzufProducer",
    "forasna": "producers.sources.forasna:ForasnaProducer",
    "jobzella": "producers.sources.jobzella:JobzellaProducer",
    "bayt": "producers.sources.bayt:BaytProducer",
    "indeed": "producers.sources.indeed:IndeedProducer",
}

# Producers that need a real browser / heavy optional deps. The runner can
# skip these gracefully on machines that lack a browser.
BROWSER_SOURCES = frozenset({"jobzella", "bayt", "indeed"})


def all_producer_names() -> list[str]:
    return list(_REGISTRY)


def get_producer_class(name: str) -> Type[BaseProducer]:
    if name not in _REGISTRY:
        raise KeyError(f"unknown producer: {name!r}. Known: {all_producer_names()}")
    module_path, class_name = _REGISTRY[name].split(":")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_producer(name: str, config=None) -> BaseProducer:
    return get_producer_class(name)(config=config)
