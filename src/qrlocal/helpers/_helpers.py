import importlib.util
import inspect
from collections.abc import Callable
from typing import Any


def is_installed(package_name: str) -> bool:
    """
    Check whether a given Python package is installed.

    Uses `importlib.util.find_spec` to determine if the specified package
    can be imported.

    Parameters
    ----------
    package_name : str
        The name of the package (e.g., "sklearn").

    Returns
    -------
    bool
        True if the package is installed, False otherwise.
    """
    return bool(importlib.util.find_spec(package_name))


def is_argument(__callable: "Callable[..., Any]", arg_name: str) -> bool:
    """
    Check if a given argument name is present in the callable's signature.

    This function checks whether the specified argument name is part of the
    parameters in the callable's signature. It can be used to verify if a
    function or method accepts a specific argument.

    Parameters
    ----------
    __callable : Callable
        The callable (function or method) whose signature is inspected.
    arg_name : str
        The name of the argument to check for in the callable's signature.

    Returns
    -------
    bool
        True if the argument name is found in the callable's parameters,
        False otherwise.
    """
    return arg_name in set(inspect.signature(__callable).parameters.keys())
