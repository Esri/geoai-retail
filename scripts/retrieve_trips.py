# minimal module imports
from arcgis.features import GeoAccessor, GeoSeriesAccessor
from arcgis.features import FeatureLayer
from arcgis.geometry import Geometry
import pandas as pd
import os
import importlib

# import arcpy if available
if importlib.util.find_spec("arcpy") is not None:
    import arcpy

import sys

sys.path.append('../src')

app_id = 'c9fa4c15-b9ab-46d4-bcd9-a3eb33dd0ff8'
hash_token = '919745fda981ddccb3ffc4f07863480e624cfa3d'

raw_gdb = os.path.abspath(r'../ba_data/raw/raw.gdb')
int_gdb = os.path.abspath(r'../ba_data/interim/interim.gdb')

dest_fc = os.path.join(int_gdb, 'pdx_businesses_home_goods')
dest_id_fld = 'LOCNUM'
origin_fc = os.path.join(raw_gdb, 'block_groups')
origin_id_fld = 'ID'

from inrix import TAZ

taz = TAZ(app_id, hash_token)

df_pop_cent = GeoAccessor.from_featureclass(dest_fc)

row = df_pop_cent.iloc[0]
geom = row.SHAPE
locnum = row.LOCNUM

def get_dest_df(geom, locnum):
    dest_df = taz.get_trip_destination_spatial_dataframe(geom.y, geom.x, '100m')
    if dest_df is not None:
        dest_df = dest_df[['travelDistanceMiles', 'travelTimeMinutes', 'SHAPE']].copy()
        dest_df.columns = ['travel_distance_miles', 'travel_time_minutes', 'SHAPE']
        dest_df['store_locnum'] = locnum
        return dest_df
    else:
        return None

