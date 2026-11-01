"""Compatibility entry point; implementation lives in apps/quiz/juken."""
from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[1] / "apps/quiz/juken")]
