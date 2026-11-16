from pathlib import Path
import pandas as pd
import pytest
from smart_green_ai.evaluate_light_holdout import evaluate
from smart_green_ai.simulate import generate


def test_missing_watering_history_blocks_evaluation_before_loading_models(tmp_path):
    data = generate(2)
    data['light_raw'] = 1000
    data['light_saturated'] = False
    data['minutes_since_water'] = float('nan')
    path = tmp_path/'unreviewed.csv'
    data.to_csv(path, index=False)
    with pytest.raises(ValueError, match='No eligible windows'):
        evaluate(path, tmp_path/'no_models', tmp_path/'output')
    assert not (tmp_path/'output').exists()
