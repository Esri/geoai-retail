"""
    Licensing
 
    Copyright 2020 Esri
 
    Licensed under the Apache License, Version 2.0 (the "License"); You
    may not use this file except in compliance with the License. You may
    obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
 
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
    implied. See the License for the specific language governing
    permissions and limitations under the License.
 
    A copy of the license is available in the repository's
    LICENSE file.
"""

import os
import sys
from pathlib import Path

from ba_tools import preprocessing
from sklearn.pipeline import Pipeline

# facilitate using local {{cookiecutter.support_library}} package resources
sys.path.insert(0, os.path.abspath('../src'))
import {{cookiecutter.support_library}}

# variable declarations
data = Path(os.path.abspath(r'../data'))
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
