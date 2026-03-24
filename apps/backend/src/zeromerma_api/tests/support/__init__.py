"""
Shared test support utilities for DB-backed ZeroMerma backend tests.

This package is intentionally small and explicit:
- db.py      -> reset helpers
- seeders.py -> canonical seed/setup helpers

The goal is to reduce copy-paste across endpoint suites while keeping test
setup readable and deterministic.
"""
