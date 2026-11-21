import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from src.explain import linear_contributions


def test_linear_contributions_reconstruct_prediction():
    model = LinearRegression().fit([[0, 0], [1, 2], [2, 1]], [1, 4, 4])
    row = pd.DataFrame([[3, 2]], columns=["a", "b"])
    contributions = linear_contributions(model, row, ["a", "b"])
    assert np.isclose(contributions.attrs["prediction"], model.predict(row)[0])
