import os

import sys
sys.path.append(os.path.abspath('../src/geoai_retail'))
import enrich

raw_gdb = r'../data/raw/raw.gdb'
geo_fc = os.path.join(raw_gdb, 'blocks')
geo_id_fld = 'GEOID'

vars_csv = '../data/raw/enrichment_variables.csv'

enrich.using_csv_variable_file(
    input_feature_class=geo_fc,
    path_to_csv_variable_file=vars_csv,
    output_feature_class=r'../data/interim/interim.gdb/blocks_enriched'
)
