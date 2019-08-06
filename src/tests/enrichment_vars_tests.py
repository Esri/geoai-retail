import pandas as pd

from ba_data_paths import ba_data

def test_fields_dataframe():
    enrich_vars = ba_data.enrich_vars_dataframe
    assert(isinstance(enrich_vars, pd.DataFrame))
