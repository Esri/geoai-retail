import os
from pathlib import Path

from ba_tools import preprocessing, utils
from sklearn.pipeline import Pipeline

# so we know what is going on
logger = utils.get_logger(loglevel='INFO', logfile='get_master.log')

# variable declarations
data = Path(r'../data').absolute()
data_raw = data/'raw'
data_int = data/'interim'

gdb_raw = data_raw/'raw.gdb'
gdb_int = data_int/'interim.gdb'

# customize the three six variables below to match your data
origin_fc = str(gdb_int/'origin_geography')
origin_id_fld = 'origin_id'

location_fc = str(gdb_int/'location')
location_id_fld = 'dest_id'

location_competition_fc = str(gdb_int/'location_competition')
location_competition_id_fld = 'comp_dest_id'

# this pipeline is based based on origin areas, brand locations, and competition locations
pipe = Pipeline([
    ('load_geos', preprocessing.OriginGeographyFeatureClassToDataframe(origin_id_fld, logger=logger)),
    ('enrich', preprocessing.AddDemographicsToOriginDataframe(
        origin_geography_layer=origin_fc,
        geography_id_field=origin_id_fld,
        interim_data_directory=data_int,
        logger=logger
    )),
    ('near_locations', preprocessing.AddNearestLocationsToOriginDataframe(
        origin_geography_layer=origin_fc,
        origin_id_field=origin_id_fld,
        location_layer=location_fc,
        location_id_field=location_id_fld,
        destination_count=6,
        interim_data_directory=data_int,
        logger=logger
    )),
    ('comp_locations', preprocessing.AddNearestCompetitionLocationsToOriginDataframe(
        origin_geography_layer=origin_fc,
        origin_id_field=origin_id_fld,
        competition_location_layer=location_competition_fc,
        competition_location_id_field=location_competition_id_fld,
        destination_count=6,
        interim_data_directory=data_int,
        logger=logger
    ))
])

# execute the pipeline
master_df = pipe.fit_transform(origin_fc)

# save the results
master_df.to_csv(data_int/'master_train.csv')