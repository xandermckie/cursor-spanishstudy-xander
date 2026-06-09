"""
API fetchers for Estudio Abroad — backward-compatible package entry point.

Submodules:
  cache        — global JSON cache I/O
  translation  — translation API orchestration and caching
  core         — homepage, vocab, phrasebook, reader, travel, stats
"""

from __future__ import annotations

from types import ModuleType


def _export_module(module: ModuleType) -> None:
    for name in dir(module):
        if name.startswith("__"):
            continue
        globals()[name] = getattr(module, name)


from fetcher import cache as _cache
from fetcher import core as _core
from fetcher import translation as _translation

_export_module(_cache)
_export_module(_translation)
_export_module(_core)

del _cache, _core, _translation, _export_module, ModuleType
