import os
import pandas as pd
from arcgis.gis import GIS

import sys
sys.path.append(os.path.abspath('../src/geoai_retail'))
sys.path.append(os.path.abspath('../notebooks'))
import utils
import config
from enrich_rest import enrich, get_online_variable_list

ent_gis = GIS(config.ent_url, username=config.ent_user, password=config.ent_pass)

raw_gdb = r'../data/raw/raw.gdb'
geo_fc = os.path.join(raw_gdb, 'blocks')
geo_id_fld = 'GEOID'

vars_csv = '../data/raw/enrichment_variables.csv'

geo_df = utils.get_dataframe(geo_fc)
geo_df = geo_df[[geo_id_fld, 'SHAPE']].copy()
geo_df.spatial.set_geometry('SHAPE')

vars_df = pd.read_csv(vars_csv, index_col=0)
vars_df['variable_name'] = vars_df['variable_name'].str.upper()
vars_df.drop_duplicates('variable_name')
var_lst = list(vars_df['variable_name'].values)
enrich_lst = get_online_variable_list(var_lst, ent_gis)

enrich_df = enrich(geo_df, geo_id_fld, enrich_lst, ent_gis)

enrich_df.to_csv('../data/interim/enrich_blocks.csv')
