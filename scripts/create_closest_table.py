import sys
import os
from arcgis.gis import GIS
sys.path.append(os.path.abspath('../src/geoai_retail'))
sys.path.append(os.path.abspath('../notebooks'))
import config
from proximity_rest import *
import utils

gdb = r'D:\projects\geoai-retail\data\raw\raw.gdb'
dest_fc = os.path.join(gdb, 'coffee')
dest_id_fld = 'LOCNUM'
origin_fc = os.path.join(gdb, 'blocks')
origin_id_fld = 'GEOID'
dest_count = 4

ent_gis = GIS(config.ent_url, username=config.ent_user, password=config.ent_pass)


origin_df = utils.get_dataframe(origin_fc)
origin_df = origin_df.iloc[:2500].copy()
origin_df.spatial.set_geometry('SHAPE')

closest_df = closest_dataframe_from_origins_destinations(origin_df, origin_id_fld, dest_fc, dest_id_fld, ent_gis)

closest_df.to_csv('../data/interim/closest_test.csv')
print('Success!')
