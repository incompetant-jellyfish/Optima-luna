# Acknowledgements

## Libraries

| Name | Purpose | Link | Licence |
|---|---|---|---|
| NumPy | Arrays and maths | https://numpy.org | BSD-3-Clause |
| pandas | Per-cell tables | https://pandas.pydata.org | BSD-3-Clause |
| PyArrow | Parquet files | https://arrow.apache.org | Apache-2.0 |
| pyproj | Polar stereographic projection | https://pyproj4.github.io/pyproj | MIT |
| PyYAML | Config file | https://pyyaml.org | MIT |
| SciPy | Resampling, spatial search | https://scipy.org | BSD-3-Clause |
| scikit-learn | Baseline model, metrics, MLP | https://scikit-learn.org | BSD-3-Clause |
| joblib | Persist trained sklearn model artifacts (scikit-learn dependency) | https://joblib.readthedocs.io | BSD-3-Clause |
| rasterio | Reading raster data (GDAL) | https://rasterio.readthedocs.io | BSD-3-Clause |
| Streamlit | Dashboard | https://streamlit.io | Apache-2.0 |
| Plotly | Interactive charts | https://plotly.com/python | MIT |
| pytest | Tests | https://pytest.org | MIT |

## Coordinate reference sources

| Name | Purpose | Link | Notes |
|---|---|---|---|
| NASA Lunar Surface Data Book, ACD-50044 Rev A, Appendix A2.1, Table A2-2 | Representative Shackleton Rim and Malapert Massif coordinates for validation | https://ntrs.nasa.gov/citations/20230007818 | Published feature-point coordinates; not certified landing coordinates |
| USGS/IAU Gazetteer of Planetary Nomenclature, Mons Malapert (Feature 16338) | Cross-check of the named Mons Malapert centre and feature boundary | https://planetarynames.wr.usgs.gov/Feature/16338 | Planetographic, east-positive longitude; approximate boundary |
| NASA Artemis III candidate-region announcement | Confirms Malapert Massif is among the candidate regions discussed by NASA | https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/ | Historical candidate-region context, not current site selection |

## Measurement datasets

Listed with download notes in [docs/DATA.md](docs/DATA.md). Add each measurement product
here only when actually downloaded and used, including its version, citation and licence/terms.
