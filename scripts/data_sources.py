import os

raw_gdb = '../ba_data/raw/raw.gdb'
raw_gdb = os.path.abspath(raw_gdb)

origin_customer_areas = os.path.join(raw_gdb, 'block_groups')
destination_store_locations = os.path.join(raw_gdb, 'coffee')

