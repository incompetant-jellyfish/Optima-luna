import pandas as pd
from src.pairing import rank_pairs


def test_pairing_radius_topn_and_cost():
    frame = pd.DataFrame({
        "cell_id": [1, 2, 3], "x": [0, 1000, 9000], "y": [0, 0, 0],
        "lat": [-85, -85, -85], "lon": [0, .03, .27], "slope_mean": [2, 4, 5],
        "landing_score": [.9, .8, .3], "resource_score": [.2, .95, .99],
        "landing_confidence": [.6, .8, .7], "resource_confidence": [.8, .9, .7],
    })
    pairs = rank_pairs(frame, radius_km=3, top_n=10)
    assert len(pairs) == 2
    assert (pairs.distance_km <= 3).all()
    assert (pairs.route_cost >= 0).all()
    assert set(pairs.landing_cell_id).issubset({1, 2})
    assert (pairs.landing_cell_id != pairs.ice_cell_id).all()
    first_pair = pairs.iloc[0]
    expected_confidence = (frame.set_index("cell_id").loc[first_pair.landing_cell_id, "landing_confidence"]
                           + frame.set_index("cell_id").loc[first_pair.ice_cell_id, "resource_confidence"]) / 2
    assert abs(first_pair.confidence - expected_confidence) < 1e-12


def test_pairing_empty_when_no_nearby_resource():
    frame = pd.DataFrame({"cell_id": [1, 2], "x": [0, 50000], "y": [0, 0],
        "lat": [-85, -85], "lon": [0, 1.6], "slope_mean": [2, 2],
        "landing_score": [.9, .8], "resource_score": [.8, .9]})
    result = rank_pairs(frame, radius_km=1)
    assert result.empty
    assert list(result.columns) == ["landing_cell_id", "ice_cell_id", "distance_km", "route_cost",
                                    "landing_score", "resource_score", "confidence", "combined_score"]
