import os
from pathlib import Path

# raw_gdb = Path(os.path.abspath('../data/raw/raw.gdb'))
# int_gdb = Path(os.path.abspath('../data/interim/interim.gdb'))
#
# origin_customer_areas = str(raw_gdb/'block_groups')
# origin_customer_area_id_field = 'ID'
#
# destination_store_locations = str(raw_gdb/'coffee_independent')
# destination_store_id_field = 'LOCNUM'
#
# destination_competition_locations = str(raw_gdb/'coffee_competition')
# destination_competition_id_field = 'LOCNUM'

_parent = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

raw_gdb = _parent/'data/raw/raw.gdb'
int_gdb = _parent/'data/interim/interim.gdb'

origin_customer_areas = str(raw_gdb/'sea_block_group')
origin_customer_area_id_field = 'ID'

destination_store_locations = str(raw_gdb/'sea_ace')
destination_store_id_field = 'LOCNUM'

destination_competition_locations = str(raw_gdb/'sea_ace_comp')
destination_competition_id_field = 'LOCNUM'