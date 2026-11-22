"""Fixtures shared by all tests."""

from __future__ import annotations

import socket

import pytest


def _refuse_network(*args, **kwargs):
    raise AssertionError(
        "a test tried to use the network; qrlocal must work offline."
    )


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Fail any test that resolves a host name or opens a connection."""
    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, _refuse_network)
    for name in ("create_connection", "getaddrinfo", "gethostbyname"):
        monkeypatch.setattr(socket, name, _refuse_network)
