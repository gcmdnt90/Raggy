"""Pure helpers for the administrative Knowledge Base file inventory."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path, PurePosixPath

_EXCLUDED_DIRECTORIES = {"chroma_db", "__pycache__", "prompts"}


def list_source_files(root: Path, supported_extensions: set[str]) -> list[Path]:
    """List every KB source recursively, excluding internal files."""
    root = root.resolve()
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in supported_extensions:
            continue
        relative = path.relative_to(root)
        if any(part.casefold() in _EXCLUDED_DIRECTORIES for part in relative.parts[:-1]):
            continue
        if len(relative.parts) == 1 and relative.name.casefold() == "readme.md":
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix().casefold())


def file_groups(root: Path, files: Iterable[Path]) -> dict[str, list[Path]]:
    """Group source files by their full relative parent directory."""
    root = root.resolve()
    groups: dict[str, list[Path]] = {}
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix().casefold()):
        parent = path.relative_to(root).parent.as_posix()
        group = "general" if parent == "." else parent
        groups.setdefault(group, []).append(path)
    return groups


def _safe_source_path(source: str) -> Path | None:
    normalized = source.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts:
        return None
    if any(part in ("", ".", "..") or ":" in part for part in path.parts):
        return None
    return Path(*path.parts)


def missing_indexed_sources(root: Path, indexed_sources: Iterable[str]) -> list[str]:
    """Return safe indexed source names whose original KB files are absent."""
    root = root.resolve()
    missing: set[str] = set()
    for source in indexed_sources:
        relative = _safe_source_path(source)
        if relative is None:
            continue
        target = (root / relative).resolve()
        if root not in target.parents or target.exists():
            continue
        missing.add(relative.as_posix())
    return sorted(missing, key=str.casefold)
