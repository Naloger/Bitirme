# -*- coding: utf-8 -*-
"""Shared helpers for test input/output tracing."""
from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


def trace_call(func: Callable[..., T], *args: Any, label: str | None = None, **kwargs: Any) -> T:
    """Log and print a function call's inputs and outputs."""
    name = label or getattr(func, "__name__", "call")
    logger.info("%s input -> args=%r kwargs=%r", name, args, kwargs)
    print(f"{name} input -> args={args!r} kwargs={kwargs!r}")
    result = func(*args, **kwargs)
    logger.info("%s output -> %r", name, result)
    print(f"{name} output -> {result!r}")
    return result

