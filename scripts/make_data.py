import os.path
from pathlib import Path

from ba_tools.analysis import get_master_csv

# this creates some path objects to make working with default data locations easier
data_dir = Path(os.path.abspath('../data'))
int_dir = data_dir/'interim'
raw_dir = data_dir/'raw'
raw_gdb = raw_dir/'raw.gdb'

# set the variables in this section
origin_geography_layer = str(raw_gdb/'sea_block_group')
origin_id_field = 'ID'

brand_location_layer = str(raw_gdb/'sea_ace')
brand_id_field = 'LOCNUM'

competitor_location_layer = str(raw_gdb/'sea_ace_comp')
competitor_id_field = 'LOCNUM'

output_csv_file = int_dir/'master_data.csv'

# this is where the work gets done
get_master_csv(origin_geography_layer, origin_id_field, brand_location_layer, brand_id_field, 
               competitor_location_layer, competitor_id_field, output_csv_file, destination_count=6, 
               overwrite_intermediate=False, logger=None)
