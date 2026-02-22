from __future__ import annotations

from typing import Iterable, Tuple, List

from app.mediamanager.utils.pathing import normalize_windows_path


def normalize_roots(selected_roots: Iterable[str]) -> list[str]:
    # 1. Normalize and deduplicate
    unique = sorted({normalize_windows_path(r).rstrip("/") for r in selected_roots if r.strip()})
    
    # 2. Prune redundant subfolders (e.g. if A and A/B are both present, keep only A)
    pruned = []
    for i, root in enumerate(unique):
        is_sub = False
        for other in unique:
            if root == other:
                continue
            # If 'other' is a prefix of 'root' followed by a slash, 'root' is redundant
            if root.startswith(other + "/"):
                is_sub = True
                break
        if not is_sub:
            pruned.append(root)
            
    return sorted(pruned)


def build_scope_where(selected_roots: Iterable[str]) -> Tuple[str, List[str]]:
    """Build a parameterized SQL WHERE predicate for selected folder roots.

    Returns (predicate_sql, params).

    Behavior:
    - Empty selection -> ("0", []) (always false)
    - Each root contributes: (path = ? OR path LIKE ?)
      with params [root, f"{root}/%"]

    NOTE: This is intended for sqlite3 parameter substitution.
    """
    roots = normalize_roots(selected_roots)
    if not roots:
        return "0", []

    parts: list[str] = []
    params: list[str] = []
    for root in roots:
        parts.append("(path = ? OR path LIKE ?)")
        params.extend([root, f"{root}/%"])

    return " OR ".join(parts), params


# Back-compat for earlier callers/tests
def build_scope_where_clause(selected_roots: Iterable[str]) -> str:
    sql, params = build_scope_where(selected_roots)
    # For debug only: interpolate for readability.
    if sql == "0":
        return sql
    out = sql
    for p in params:
        out = out.replace("?", f"'{p.replace("'", "''")}'", 1)
    return out
