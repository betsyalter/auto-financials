from pathlib import Path

_ROOT_CACHE = None

def get_project_root() -> Path:
    """
    Return the repo root (folder containing 'kpi_refresh_system').
    Caches result for speed.
    """
    global _ROOT_CACHE
    if _ROOT_CACHE is not None:
        return _ROOT_CACHE

    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "kpi_refresh_system").exists():
            _ROOT_CACHE = parent
            return parent
    # Fallback to two levels up
    _ROOT_CACHE = here.parents[2]
    return _ROOT_CACHE

def resolve_path(*parts: str) -> Path:
    """Join parts onto project root."""
    return get_project_root().joinpath(*parts)