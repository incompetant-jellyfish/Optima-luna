"""Smoke test for the dashboard: runs headless with Streamlit's AppTest.

Checks the demo path works end to end in SYNTHETIC mode: no exceptions, banner shown,
sliders re-rank, picking a site works, and the fallback uses the shared grid's cell_ids.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.grid import build_grid

APP = str(Path(__file__).resolve().parent.parent / "app" / "main.py")
FEATURES = Path(__file__).resolve().parent.parent / "data" / "processed" / "features.parquet"


@pytest.fixture(scope="module")
def at():
    app = AppTest.from_file(APP, default_timeout=120)
    app.run()
    return app


def test_runs_without_exceptions(at):
    assert not at.exception


@pytest.mark.skipif(FEATURES.exists(), reason="real features.parquet present")
def test_synthetic_banner_shown(at):
    assert any("SYNTHETIC" in e.value for e in at.error)


def test_weight_slider_reranks(at):
    before = list(at.dataframe[0].value.cell_id)
    at.slider(key="w_landing_slope_mean").set_value(0.0)
    at.slider(key="w_landing_illum_frac").set_value(1.0)
    at.run()
    assert not at.exception
    assert list(at.dataframe[0].value.cell_id) != before


def test_site_pick(at):
    ids = list(at.dataframe[0].value.cell_id)
    at.session_state["site_pick"] = ids[2]
    at.run()
    assert not at.exception
    assert at.session_state["selected_cell"] == ids[2]


def test_top_cells_exist_on_shared_grid(at):
    grid_ids = set(build_grid()["cell_id"])
    assert set(at.dataframe[0].value.cell_id) <= grid_ids
