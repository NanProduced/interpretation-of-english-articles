"""Pytest configuration for backend tests.

This module provides:
1. Marker enforcement: ensures all tests are tagged with at least one topic marker
2. Shared fixtures and hooks for test organization
"""

from __future__ import annotations

import pytest

THEME_MARKERS = {
    "auth",
    "dict",
    "tasks",
    "workflow",
    "schema",
    "postprocess",
    "prompt",
    "infra",
    "regression",
}

BUILTIN_MARKERS = {
    "parametrize",
    "skip",
    "xfail",
    "usefixtures",
    "filterwarnings",
    "tryfirst",
    "trylast",
    "anyio",
    "asyncio",
}


def pytest_collection_modifyitems(config, items):
    """
    Ensure all collected tests have at least one theme marker.

    This hook runs after test collection and checks that every test
    is tagged with at least one marker from THEME_MARKERS.

    If any tests are missing theme markers:
    - They are reported as warnings
    - They are also tagged with a special 'unmarked' marker for easy filtering

    To enforce strict mode (fail on unmarked tests), set the environment
    variable PYTEST_ENFORCE_MARKERS=1 or pass --enforce-markers.
    """
    unmarked_items = []
    marked_items = []

    for item in items:
        item_markers = {m.name for m in item.iter_markers()}
        theme_markers_found = item_markers & THEME_MARKERS

        if not theme_markers_found:
            unmarked_items.append(item)
            item.add_marker(pytest.mark.unmarked)
        else:
            marked_items.append(item)

    if unmarked_items:
        unmarked_paths = sorted({item.fspath for item in unmarked_items})
        unmarked_count = len(unmarked_items)
        file_count = len(unmarked_paths)

        config.issue_config_time_warning(
            pytest.PytestWarning(
                f"\n"
                f"{'='*80}\n"
                f"WARNING: Found {unmarked_count} test(s) in {file_count} file(s) "
                f"without theme markers!\n"
                f"\n"
                f"Affected files:\n"
                + "\n".join(f"  - {path}" for path in unmarked_paths)
                + "\n\n"
                f"Required: Each test file must have at least one theme marker:\n"
                f"  {sorted(THEME_MARKERS)}\n"
                f"\n"
                f"Add 'pytestmark = pytest.mark.<marker>' at the module level,\n"
                f"or use @pytest.mark.<marker> on individual test classes/functions.\n"
                f"{'='*80}"
            ),
            stacklevel=2,
        )

        enforce_markers = (
            config.getoption("--enforce-markers", default=False)
            or config.getini("enforce_markers")
        )

        if enforce_markers:
            pytest.exit(
                f"Exiting due to unmarked tests. "
                f"Use `pytest -m unmarked` to see them, "
                f"or remove --enforce-markers to continue."
            )


def pytest_addoption(parser):
    """Add custom command-line options."""
    group = parser.getgroup("marker enforcement")
    group.addoption(
        "--enforce-markers",
        action="store_true",
        default=False,
        help="Fail the test run if any tests are missing theme markers",
    )
    parser.addini(
        "enforce_markers",
        type="bool",
        default=False,
        help="If True, fail the test run if any tests are missing theme markers",
    )


def pytest_configure(config):
    """Register additional markers and configure test environment."""
    config.addinivalue_line(
        "markers",
        "unmarked: Tests without a theme marker (auto-added by conftest.py)",
    )
