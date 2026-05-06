"""Association rule mining over LLM behavior features.

The task brief explicitly asks for FP-Growth on the prompt/response feature
matrix. We turn each row of ``behavior_features.csv`` into an itemset of
``key=value`` tokens and look for rules whose right-hand side describes a
failure outcome — for example ``{level=L3, has_noise=1} -> {error_category=calculation_collapse}``.

If ``mlxtend`` is not installed we fall back to a frequent-itemset table so the
pipeline still produces something useful.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd


_DEFAULT_FEATURE_COLS: tuple[str, ...] = (
    "model",
    "level",
    "noise_label",
    "noise_keyword_hit",
    "noise_keyword_present",
    "criticality",
    "has_formula",
    "uses_coordinate",
    "ai_judgment",
    "is_correct",
    "is_uncertain",
    "error_category",
)

_OUTCOME_PREFIXES: tuple[str, ...] = (
    "is_correct=",
    "is_uncertain=",
    "ai_judgment=",
    "error_category=",
)


def _row_to_items(row: pd.Series, columns: Iterable[str]) -> list[str]:
    items: list[str] = []
    for col in columns:
        if col not in row or pd.isna(row[col]):
            continue
        value = row[col]
        if isinstance(value, bool):
            value = int(value)
        items.append(f"{col}={value}")
    return items


def build_transactions(
    features: pd.DataFrame,
    columns: Iterable[str] = _DEFAULT_FEATURE_COLS,
) -> list[list[str]]:
    columns = [c for c in columns if c in features.columns]
    return [_row_to_items(row, columns) for _, row in features.iterrows()]


def _frequent_itemset_fallback(
    transactions: list[list[str]],
    min_support: float,
    max_len: int,
) -> pd.DataFrame:
    from collections import Counter
    from itertools import combinations

    n = len(transactions) or 1
    counter: Counter[frozenset[str]] = Counter()
    for items in transactions:
        unique = sorted(set(items))
        for size in range(1, max_len + 1):
            for combo in combinations(unique, size):
                counter[frozenset(combo)] += 1
    rows = [
        {"itemsets": tuple(sorted(items)), "support": count / n, "size": len(items)}
        for items, count in counter.items()
        if count / n >= min_support
    ]
    return pd.DataFrame(rows).sort_values("support", ascending=False).reset_index(drop=True)


def mine_rules(
    features: pd.DataFrame,
    min_support: float = 0.10,
    min_confidence: float = 0.60,
    max_len: int = 4,
    columns: Iterable[str] = _DEFAULT_FEATURE_COLS,
    outcome_prefixes: Iterable[str] = _OUTCOME_PREFIXES,
) -> dict[str, pd.DataFrame]:
    """Run FP-Growth (or a fallback) and surface outcome-focused rules.

    Returns a dict with:

    - ``frequent_itemsets``: support of frequent ``key=value`` itemsets.
    - ``rules``: full association rules (if mlxtend is available).
    - ``outcome_rules``: subset whose consequent describes correctness, judgment,
      uncertainty or failure mode — the rules most useful for the report.
    """
    transactions = build_transactions(features, columns=columns)
    if not transactions:
        empty = pd.DataFrame()
        return {"frequent_itemsets": empty, "rules": empty, "outcome_rules": empty}

    try:
        from mlxtend.frequent_patterns import association_rules, fpgrowth
        from mlxtend.preprocessing import TransactionEncoder
    except ImportError:
        frequent = _frequent_itemset_fallback(transactions, min_support, max_len)
        empty = pd.DataFrame()
        return {"frequent_itemsets": frequent, "rules": empty, "outcome_rules": empty}

    encoder = TransactionEncoder()
    matrix = encoder.fit(transactions).transform(transactions)
    onehot = pd.DataFrame(matrix, columns=encoder.columns_)

    frequent = fpgrowth(onehot, min_support=min_support, use_colnames=True, max_len=max_len)
    if frequent.empty:
        empty = pd.DataFrame()
        return {"frequent_itemsets": frequent, "rules": empty, "outcome_rules": empty}

    rules = association_rules(frequent, metric="confidence", min_threshold=min_confidence)
    rules = rules.copy()
    rules["antecedents"] = rules["antecedents"].apply(lambda items: tuple(sorted(items)))
    rules["consequents"] = rules["consequents"].apply(lambda items: tuple(sorted(items)))

    prefixes = tuple(outcome_prefixes)
    mask = rules["consequents"].apply(
        lambda items: len(items) == 1 and items[0].startswith(prefixes)
    )
    outcome_rules = rules[mask].sort_values(
        ["lift", "confidence", "support"], ascending=False
    ).reset_index(drop=True)

    frequent = frequent.copy()
    frequent["itemsets"] = frequent["itemsets"].apply(lambda items: tuple(sorted(items)))
    frequent = frequent.sort_values("support", ascending=False).reset_index(drop=True)

    return {
        "frequent_itemsets": frequent,
        "rules": rules.reset_index(drop=True),
        "outcome_rules": outcome_rules,
    }
