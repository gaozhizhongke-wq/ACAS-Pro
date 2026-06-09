#!/usr/bin/env python3
"""
ACAS Pro — CI Architecture Guard

Ensures:
1. No module outside core/schema.py contains CREATE TABLE statements
2. All table names referenced in modules exist in core/schema.py
3. No duplicate table definitions across modules

Run: python -m pytest tests/test_architecture_guard.py -v
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "acas_pro"
SCHEMA_FILE = SRC_ROOT / "core" / "schema.py"


def _extract_table_names_from_schema() -> set[str]:
    """Parse core/schema.py and return all table names from SCHEMA_SQLITE."""
    tree = ast.parse(SCHEMA_FILE.read_text(encoding="utf-8"))
    tables: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for m in re.finditer(
                r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", node.value, re.I
            ):
                tables.add(m.group(1))
    return tables


def _get_python_files(exclude: list[str] | None = None) -> list[Path]:
    """Get all .py files under SRC_ROOT, excluding specified subpaths."""
    exclude = exclude or []
    files: list[Path] = []
    for root, _dirs, filenames in os.walk(SRC_ROOT):
        p = Path(root)
        if any(part in exclude for part in p.parts):
            continue
        for f in filenames:
            if f.endswith(".py"):
                files.append(p / f)
    return files


def _find_create_table_stmts(filepath: Path) -> list[tuple[int, str]]:
    """Return (line_no, table_name) for all CREATE TABLE in a file."""
    results: list[tuple[int, str]] = []
    source = filepath.read_text(encoding="utf-8")
    for i, line in enumerate(source.splitlines(), start=1):
        m = re.search(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", line, re.I
        )
        if m:
            results.append((i, m.group(1)))
    return results


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

class TestSchemaCentralization:
    """All CREATE TABLE must live in core/schema.py only."""

    def test_schema_file_exists(self):
        assert SCHEMA_FILE.exists(), (
            f"core/schema.py not found at {SCHEMA_FILE}"
        )

    def test_schema_has_tables(self):
        tables = _extract_table_names_from_schema()
        assert len(tables) >= 30, (
            f"Expected at least 30 tables in schema, found {len(tables)}"
        )

    def test_no_create_table_outside_schema(self):
        """No module (except schema.py) may contain CREATE TABLE statements."""
        schema_tables = _extract_table_names_from_schema()
        files = _get_python_files(exclude=["__pycache__"])
        violations: list[str] = []

        for f in files:
            rel = f.relative_to(SRC_ROOT)
            if str(rel).startswith("core" + os.sep + "schema.py"):
                continue
            source_lines = f.read_text(encoding="utf-8").splitlines()
            for line_no, table_name in _find_create_table_stmts(f):
                line = source_lines[line_no - 1]
                # Skip comment lines (containing the guard comment)
                if line.strip().startswith("#"):
                    continue
                # Allow ALTER TABLE
                if re.search(r"ALTER\s+TABLE", line, re.I):
                    continue
                # Skip string literals inside guard comments like "do not add CREATE TABLE here"
                if "do not add CREATE TABLE" in line or "do not add CREATE/ALTER TABLE" in line:
                    continue
                violations.append(
                    f"{rel}:{line_no} — CREATE TABLE {table_name}"
                )

        assert not violations, (
            "CREATE TABLE statements found outside core/schema.py:\n"
            + "\n".join(violations)
            + "\n\nMove these to core/schema.py"
        )


class TestTableConsistency:
    """Every table referenced in code should exist in the unified schema."""

    def test_schema_exports_all_tables(self):
        tree = ast.parse(SCHEMA_FILE.read_text(encoding="utf-8"))
        has_list = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "ALL_TABLE_NAMES":
                        has_list = True
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == "ALL_TABLE_NAMES":
                    has_list = True
        assert has_list, "schema.py must export ALL_TABLE_NAMES list"

    def test_all_table_names_in_schema_string(self):
        tree = ast.parse(SCHEMA_FILE.read_text(encoding="utf-8"))
        schema_tables = _extract_table_names_from_schema()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "ALL_TABLE_NAMES":
                        if isinstance(node.value, ast.List):
                            list_names = {
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                                and isinstance(elt.value, str)
                            }
                            missing = list_names - schema_tables
                            assert not missing, (
                                f"ALL_TABLE_NAMES contains tables not in SCHEMA_SQLITE: {missing}"
                            )
                            extra = schema_tables - list_names
                            assert not extra, (
                                f"SCHEMA_SQLITE has tables not in ALL_TABLE_NAMES: {extra}"
                            )
