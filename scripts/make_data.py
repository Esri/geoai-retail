import os

import arcpy

from geoai_retail.enrich_local import enrich_all
from geoai_retail.utils import get_logger
from scripts.data_sources import origin_customer_areas

# create a logger to save into the same directory
logger = get_logger('DEBUG', './make_data.log')
logger.__name__ = 'make_data'

# ensure the directory tree exists to put the ba_data
interim_dir = os.path.abspath('../ba_data/interim')
interim_gdb = os.path.join(interim_dir, 'interim.gdb')
enrich_all_out = os.path.join(interim_gdb, f'{os.path.basename(origin_customer_areas)}_enrich_all')

if not os.path.exists(interim_dir):
    os.makedirs(interim_dir)
    logger.info('Created interim ba_data directory.')

if not arcpy.Exists(interim_gdb):
    arcpy.management.CreateFileGDB(interim_gdb)
    logger.info('Created interim File Geodatabase.')

# enrich all contributing origin geographies with all available demographics
if not arcpy.Exists(enrich_all_out):
    try:
        logger.info(f'Starting to enrich {origin_customer_areas}.')
        enrich_all(origin_customer_areas, enrich_all_out)
        logger.info(f'Successfully enriched origin geographies. The output is located at {enrich_all_out}.')

    except Exception as e:
        logger.error(f'Failed to enrich {origin_customer_areas}. \n{e}')

else:
    logger.info(f'Enriched origin geographies already exist at {enrich_all_out}')
