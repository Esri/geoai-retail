import os
from pathlib import Path

from ba_tools import preprocessing
from sklearn.pipeline import Pipeline

# variable declarations
data = Path(os.path.abspath(r'../data'))
data_raw = data/'raw'
data_int = data/'interim'

gdb_raw = data_raw/'raw.gdb'
gdb_int = data_int/'interim.gdb'

# customize the three six variables below to match your data
origin_fc = str(gdb_raw/'origin_block_groups')
origin_id_fld = str('ID')

location_fc = str(gdb_raw/'locations')
location_id_fld = 'LOCNUM'

location_competition_fc = str(gdb_raw/'location_competition')
location_competition_id_fld = 'LOCNUM'

# this pipeline is based based on origin areas, brand locations, and competition locations
pipe = Pipeline([
    ('load_geos', preprocessing.OriginGeographyFeatureClassToDataframe(origin_id_fld)),
    ('enrich', preprocessing.AddDemographicsToOriginDataframe(
        origin_geography_layer=origin_fc,
        geography_id_field=origin_id_fld,
        interim_data_directory=data_int
     )),
    ('near_locations', preprocessing.AddNearestLocationsToOriginDataframe(
        origin_geography_layer=origin_fc,
        origin_id_field=origin_id_fld,
        location_layer=location_fc,
        location_id_field=location_id_fld,
        destination_count=6,
        interim_data_directory=data_int
    )),
    ('comp_locations', preprocessing.AddNearestCompetitionLocationsToOriginDataframe(
        origin_geography_layer=origin_fc,
        origin_id_field=origin_id_fld,
        competition_location_layer=location_competition_fc,
        competition_location_id_field=location_competition_id_fld,
        destination_count=6,
        interim_data_directory=data_int
    ))
])

# execute the pipeline
master_df = pipe.fit_transform(origin_fc)

# save the results
master_df.to_csv(data_int/'master_train.csv')