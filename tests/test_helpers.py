"""Tests of ``python_template.helpers``."""

from __future__ import annotations

import sys

import pytest

import python_template.helpers
from python_template.helpers import is_argument, is_installed


def test_all_public_names_are_importable():
    for name in python_template.helpers.__all__:
        assert hasattr(python_template.helpers, name)


# --- is_installed ------------------------------------------------------------


@pytest.mark.parametrize("package_name", ["sys", "pytest", "python_template"])
def test_is_installed_returns_true_for_an_installed_package(package_name):
    assert is_installed(package_name) is True


def test_is_installed_returns_false_for_a_missing_package():
    assert is_installed("python_template_package_that_does_not_exist") is False


def test_is_installed_returns_false_for_a_blocked_package(monkeypatch):
    # A None entry in sys.modules makes the package look missing. Tests of
    # optional dependencies rely on this.
    monkeypatch.setitem(sys.modules, "json", None)

    assert is_installed("json") is False


# --- is_argument -------------------------------------------------------------


def _function(alpha, beta=1, *args, gamma=None, **kwargs):
    """Take parameters of every kind (used by the tests of is_argument)."""


class _Model:
    def __init__(self, alpha=1.0):
        self.alpha = alpha

    def fit(self, X, sample_weight=None):
        return self


@pytest.mark.parametrize("arg_name", ["alpha", "beta", "gamma"])
def test_is_argument_returns_true_for_a_parameter(arg_name):
    assert is_argument(_function, arg_name) is True


@pytest.mark.parametrize("arg_name", ["delta", "Alpha", ""])
def test_is_argument_returns_false_for_a_missing_parameter(arg_name):
    # ``**kwargs`` does not make every name a parameter.
    assert is_argument(_function, arg_name) is False


def test_is_argument_inspects_classes_and_bound_methods():
    assert is_argument(_Model, "alpha") is True
    assert is_argument(_Model().fit, "sample_weight") is True
    assert is_argument(_Model().fit, "eval_set") is False
    # Neither a class nor a bound method shows ``self``.
    assert is_argument(_Model, "self") is False
    assert is_argument(_Model().fit, "self") is False
