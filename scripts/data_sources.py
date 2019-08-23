import os

raw_gdb = '../data/raw/raw.gdb'
raw_gdb = os.path.abspath(raw_gdb)

origin_customer_areas = os.path.join(raw_gdb, 'block_groups')
origin_customer_area_id_field = 'ID'

destination_store_locations = os.path.join(raw_gdb, 'coffee')
destination_store_id_field = 'LOCNUM'

