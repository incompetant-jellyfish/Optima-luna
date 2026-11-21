"""Phase 3 acceptance: monotonicity, missing-data reweighting, constraints."""

import numpy as np
import pandas as pd
import pytest

from src.config import load_config
from src.constraints import failed_constraints, landing_mask
from src.scoring import contributions, default_weights, normalise, score, weighted

CFG = load_config()


def make_frame(n=50, seed=0, real=True):
    """Small hand-made features table with every scored feature present."""
    rng = np.random.default_rng(seed)
    cols = {f: rng.uniform(0, 1, n) for f in CFG["features"]}
    cols["slope_mean"] = rng.uniform(0, 20, n)
    cols["roughness"] = rng.uniform(0, 10, n)
    cols["boulder_density"] = rng.uniform(0, 80, n)
    cols["temp_max"] = rng.uniform(40, 300, n)
    df = pd.DataFrame(cols)
    df.insert(0, "cell_id", np.arange(n))
    for f in CFG["features"]:
        df[f"{f}_cov"] = real
    return df


# ---- monotonicity -----------------------------------------------------------------
def test_steeper_slope_never_raises_landing_score():
    df = make_frame()
    for f in CFG["features"]:
        if f != "slope_mean":
            df[f] = df[f].iloc[0]                       # everything equal except slope
    df["slope_mean"] = np.linspace(0, 20, len(df))
    s = score(df)["landing_score"].to_numpy()
    assert np.all(np.diff(s) <= 1e-12)
    assert s[0] > s[-1]


@pytest.mark.parametrize("group", ["landing", "resource"])
def test_every_feature_moves_score_in_its_direction(group):
    spec = CFG["scoring"][group]
    for f, s in spec.items():
        df = make_frame(n=40, seed=1)
        for other in CFG["features"]:
            if other != f:
                df[other] = df[other].iloc[0]
        df[f] = np.linspace(df[f].min(), df[f].max(), len(df))
        out = score(df)[f"{group}_score"].to_numpy()
        steps = np.diff(out)
        if s["direction"] == "higher":
            assert np.all(steps >= -1e-12), f
        else:
            assert np.all(steps <= 1e-12), f


# ---- missing data -------------------------------------------------------------------
def test_missing_layer_is_reweighted_not_guessed():
    df = make_frame()
    norm = normalise(df)
    w = default_weights()["landing"]
    full, _ = weighted(norm, w, df)

    norm_missing = norm.copy()
    norm_missing.loc[0, "illum_frac"] = np.nan
    s, _ = weighted(norm_missing, w, df)
    rest = {f: v for f, v in w.items() if f != "illum_frac"}
    expected = sum(norm.loc[0, f] * v for f, v in rest.items()) / sum(rest.values())
    assert np.isclose(s[0], expected)
    assert np.allclose(s[1:], full[1:])                # other cells untouched


def test_confidence_counts_only_real_data():
    df = make_frame(real=True)
    assert np.allclose(score(df)["confidence"], 1.0)

    df.loc[0, "illum_frac"] = np.nan                    # missing -> lower confidence
    df.loc[1, "ice_cpr_cov"] = False                    # synthetic -> lower confidence
    out = score(df)
    w = default_weights()
    tot_l, tot_r = sum(w["landing"].values()), sum(w["resource"].values())
    assert np.isclose(out.loc[0, "landing_confidence"], 1 - w["landing"]["illum_frac"] / tot_l)
    assert np.isclose(out.loc[1, "resource_confidence"], 1 - w["resource"]["ice_cpr"] / tot_r)
    assert np.isfinite(out.loc[0, "landing_score"])     # still scored from the rest

    synth = make_frame(real=False)
    assert np.allclose(score(synth)["confidence"], 0.0)


def test_all_layers_missing_gives_nan_score():
    df = make_frame()
    for f in CFG["scoring"]["landing"]:
        df.loc[3, f] = np.nan
    assert np.isnan(score(df).loc[3, "landing_score"])


def test_scores_in_unit_interval():
    out = score(make_frame(n=200, seed=4))
    for c in ["landing_score", "resource_score", "confidence"]:
        assert out[c].between(0, 1).all()


def test_contributions_sum_to_score():
    df = make_frame()
    norm = normalise(df)
    w = default_weights()["landing"]
    s, _ = weighted(norm, w, df)
    assert np.isclose(contributions(norm.loc[5], w).sum(), s[5])


# ---- constraints ----------------------------------------------------------------------
def test_constraints_mask():
    lim = CFG["constraints"]["slope_mean_max_deg"]
    df = pd.DataFrame({"slope_mean": [lim - 1, lim + 1, np.nan],
                       "roughness": [0.0, 0.0, 0.0], "boulder_density": [0.0, 0.0, np.nan]})
    assert landing_mask(df).tolist() == [True, False, True]   # NaN never fails a cell
    assert failed_constraints(df.loc[1]) == ["slope_mean"]
