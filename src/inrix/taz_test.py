# minimal module imports
from arcgis.features import GeoAccessor, GeoSeriesAccessor
from arcgis.features import FeatureLayer
from arcgis.geometry import Geometry
from ba_data_paths import ba_data
import pandas as pd
import os
import importlib
from pathlib import Path
from inrix.utilities import TAZ

# import arcpy if available
if importlib.util.find_spec("arcpy") is not None:
    import arcpy

import sys

sys.path.append('../src')

app_id = 'c9fa4c15-b9ab-46d4-bcd9-a3eb33dd0ff8'
hash_token = '919745fda981ddccb3ffc4f07863480e624cfa3d'

data_dir = Path(os.path.abspath('../../data'))

interim_dir = data_dir / 'interim'
interim_gdb = interim_dir / 'interim.gdb'

raw_dir = data_dir / 'raw'
raw_gdb = raw_dir / 'raw.gdb'

nearest_stores_csv = interim_dir / 'closest_store.csv'
nearest_comp_csv = interim_dir / 'closest_competition.csv'

origin_fc = str(raw_gdb / 'sea_block_group')
origin_id_fld = 'ID'

dest_fc = str(raw_gdb / 'sea_ace')
dest_fc_fld = 'LOCNUM'

comp_fc = raw_gdb / 'sea_ace_comp'
comp_id_fld = 'LOCNUM'

taz = TAZ(app_id, hash_token)


def get_dest_df(geom, locnum):
    dest_df = taz.get_trip_destination_spatial_dataframe(geom.y, geom.x, '100m')
    if dest_df is not None:
        dest_df = dest_df[['travelDistanceMiles', 'travelTimeMinutes', 'SHAPE']].copy()
        dest_df.columns = ['travel_distance_miles', 'travel_time_minutes', 'SHAPE']
        dest_df['store_locnum'] = locnum
        dest_df['x'] = dest_df.SHAPE.apply(lambda geom: geom.x)
        dest_df['y'] = dest_df.SHAPE.apply(lambda geom: geom.y)
        return dest_df
    else:
        return None

df_pop_cent = GeoAccessor.from_featureclass(dest_fc)

for idx, (locnum, geom) in df_pop_cent[['LOCNUM', 'SHAPE']].iterrows():
    new_df = get_dest_df(geom, locnum)
    if new_df is not None:
        if idx == 0:
            dest_df = new_df
        else:
            dest_df = dest_df.append(new_df)

dest_df.to_csv(interim_dir / 'raw_trips_sea_ace.csv')
dest_df.spatial.to_featureclass(interim_gdb / 'raw_trips_sea_ace')

