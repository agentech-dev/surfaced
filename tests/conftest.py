"""Pytest configuration and fixtures."""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires running ClickHouse server")
