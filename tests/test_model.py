import numpy as np
import pandas as pd
from src.model import make_pseudo_labels, spatial_block_groups


def test_pseudo_label_scores_are_bounded_and_confidence():
    n = 30
    frame = pd.DataFrame({"x": np.arange(n) * 1000., "y": np.zeros(n),
                          "slope_mean": np.linspace(0, 12, n), "roughness": np.ones(n),
                          "illum_frac": np.linspace(0, 1, n), "earth_los_frac": np.ones(n),
                          "ice_cpr": np.linspace(0, 1, n), "hydration_depth": np.ones(n),
                          "psr_frac": np.linspace(0, 1, n), "temp_max": np.linspace(150, 30, n),
                          "crater_density": np.ones(n)})
    result = make_pseudo_labels(frame)
    assert result.landing_score.between(0, 1).all()
    assert result.resource_score.between(0, 1).all()
    assert result.landing_confidence.between(0, 1).all()


def test_spatial_block_group_is_shared_within_block():
    frame = pd.DataFrame({"x": [100, 200, 10100], "y": [100, 200, 100]})
    groups = spatial_block_groups(frame, block_size_m=1000)
    assert groups[0] == groups[1]
    assert groups[0] != groups[2]


def test_training_spatial_holdouts_and_ensemble(tmp_path):
    from src.model import train_models
    rng = np.random.default_rng(5)
    n_side = 24
    xx, yy = np.meshgrid(np.arange(n_side) * 1000., np.arange(n_side) * 1000.)
    n = xx.size
    slope = rng.uniform(0, 10, n)
    illum = rng.uniform(0, 1, n)
    psr = rng.uniform(0, 1, n)
    frame = pd.DataFrame({
        "cell_id": np.arange(n), "x": xx.ravel(), "y": yy.ravel(), "lat": -85., "lon": 0.,
        "slope_mean": slope, "roughness": rng.uniform(0, 4, n),
        "boulder_density": rng.uniform(0, 20, n), "illum_frac": illum,
        "earth_los_frac": rng.uniform(0, 1, n), "ice_cpr": psr + rng.normal(0, .1, n),
        "hydration_depth": psr + rng.normal(0, .1, n), "psr_frac": psr,
        "temp_max": 160 - 100 * psr + rng.normal(0, 3, n),
        "crater_density": rng.uniform(0, 10, n),
    })
    predictions, metrics = train_models(frame, mask_rate=.1, ensemble_size=3,
                                        block_size_m=3000, output_dir=tmp_path)
    assert "landing_score" in predictions and "resource_score" in predictions
    assert "confidence" in predictions
    assert predictions.landing_score.between(0, 1).all()
    assert predictions.resource_score.between(0, 1).all()
    assert "landing_score/mlp" in metrics
    item = metrics["landing_score/mlp"]
    assert item["train_spatial_blocks"] > 0
    assert item["test_r2"] is not None
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "landing_score_mlp.joblib").exists()


def test_synthetic_coverage_is_zero_even_when_values_exist():
    from src.model import make_pseudo_labels
    frame = pd.DataFrame({
        "slope_mean": [2., 3.], "roughness": [1., 1.], "boulder_density": [1., 1.],
        "illum_frac": [.8, .9], "earth_los_frac": [.7, .8],
        "ice_cpr": [.9, .8], "hydration_depth": [.2, .1], "psr_frac": [.9, .8],
        "temp_max": [40., 50.], "crater_density": [4., 5.],
    })
    for name in frame.columns:
        frame[f"{name}_cov"] = False
    result = make_pseudo_labels(frame)
    assert result.landing_score.notna().all()
    assert result.resource_score.notna().all()
    assert (result.landing_confidence == 0).all()
    assert (result.resource_confidence == 0).all()


def test_synthetic_values_do_not_inflate_confidence():
    from src.model import make_pseudo_labels
    frame = pd.DataFrame({
        "slope_mean": [2., 3.], "roughness": [1., 1.], "boulder_density": [1., 1.],
        "illum_frac": [.8, .9], "earth_los_frac": [.7, .8],
        "ice_cpr": [.9, .8], "hydration_depth": [.2, .1], "psr_frac": [.9, .8],
        "temp_max": [40., 50.], "crater_density": [4., 5.],
    })
    for name in frame.columns:
        frame[f"{name}_cov"] = False
    result = make_pseudo_labels(frame)
    assert result.landing_score.notna().all()
    assert result.resource_score.notna().all()
    assert (result.landing_confidence == 0).all()
    assert (result.resource_confidence == 0).all()


def test_layer_masking_hides_complete_columns():
    from src.model import _mask_features
    frame = pd.DataFrame({f"f{i}": np.arange(100, dtype=float) for i in range(8)})
    masked = _mask_features(frame, np.random.default_rng(123), 0.5)
    hidden = [column for column in frame if masked[column].isna().all()]
    assert hidden  # fixed seed should drop at least one complete layer
    assert len(hidden) < len(frame.columns)
