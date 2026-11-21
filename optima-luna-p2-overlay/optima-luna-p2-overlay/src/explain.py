"""Explain model predictions with transparent linear weights or local perturbation.

For Ridge/MLP models, a literal ``weight * normalised value`` decomposition is exact
only for a linear model with a compatible linear preprocessing transform. The helper
below therefore provides exact per-feature contributions for a fitted linear model;
for MLP predictions it reports transparent per-feature perturbation effects instead.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def linear_contributions(model, row: pd.Series | pd.DataFrame, feature_names: list[str] | None = None) -> pd.DataFrame:
    """Return exact additive contributions for a fitted single-output linear pipeline.

    Supports a sklearn Pipeline whose final estimator exposes ``coef_`` and whose
    preceding preprocessing stages can transform a one-row DataFrame. Contributions
    sum to the model output after accounting for the estimator intercept.
    """
    if isinstance(row, pd.Series):
        row = row.to_frame().T
    if len(row) != 1:
        raise ValueError("row must contain exactly one observation")
    estimator = model
    transformed_names = None
    if hasattr(model, "named_steps"):
        steps = list(model.named_steps.values())
        estimator = steps[-1]
        transformed = row
        for step in steps[:-1]:
            transformed = step.transform(transformed)
        # Include columns introduced by imputer missing-value indicators.
        first_step = steps[0]
        if hasattr(first_step, "get_feature_names_out"):
            try:
                transformed_names = list(first_step.get_feature_names_out(input_features=list(row.columns)))
            except (TypeError, ValueError):
                transformed_names = None
    else:
        transformed = np.asarray(row, dtype=float)
        transformed_names = list(row.columns)
    if not hasattr(estimator, "coef_"):
        raise TypeError("Exact weight × value attribution requires a linear estimator with coef_")
    weights = np.asarray(estimator.coef_, dtype=float).reshape(-1)
    values = np.asarray(transformed, dtype=float).reshape(-1)
    if len(weights) != len(values):
        raise ValueError("transformed feature count does not match model coefficient count")
    names = feature_names or transformed_names or [f"transformed_feature_{i}" for i in range(len(weights))]
    if len(names) != len(weights):
        names = transformed_names if transformed_names and len(transformed_names) == len(weights) else [f"transformed_feature_{i}" for i in range(len(weights))]
    contributions = weights * values
    result = pd.DataFrame({"feature": names, "transformed_value": values,
                           "weight": weights, "contribution": contributions})
    result = result.sort_values("contribution", key=np.abs, ascending=False).reset_index(drop=True)
    result.attrs["intercept"] = float(np.asarray(getattr(estimator, "intercept_", 0)).reshape(-1)[0])
    result.attrs["prediction"] = float(result.contribution.sum() + result.attrs["intercept"])
    return result


def perturbation_effects(model, row: pd.Series | pd.DataFrame, *, feature_names: list[str] | None = None,
                         scale: float = 1.0) -> pd.DataFrame:
    """Estimate one-feature-at-a-time prediction changes; not SHAP values."""
    if isinstance(row, pd.Series):
        row = row.to_frame().T
    if len(row) != 1:
        raise ValueError("row must contain exactly one observation")
    names = feature_names or list(row.select_dtypes(include=[np.number]).columns)
    base = float(model.predict(row)[0])
    rows = []
    for name in names:
        if name not in row:
            continue
        value = pd.to_numeric(row[name], errors="coerce").iloc[0]
        if not np.isfinite(value):
            continue
        changed = row.copy()
        changed.loc[changed.index[0], name] = value + scale
        delta = float(model.predict(changed)[0] - base)
        rows.append({"feature": name, "base_value": float(value), "perturbation": scale,
                     "prediction_delta": delta})
    return pd.DataFrame(rows).sort_values("prediction_delta", key=np.abs, ascending=False).reset_index(drop=True)
