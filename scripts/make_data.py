import os

from ba_data_paths import ba_data
from geoai_retail.enrich_local import enrich_all
from geoai_retail.utils import get_logger
from geoai_retail.proximity_local import closest_dataframe_from_origins_destinations
from scripts.data_sources import origin_customer_areas, origin_customer_area_id_field, destination_store_locations, \
    destination_store_id_field

# create a logger to save into the same directory
logger = get_logger('DEBUG', '../data/interim/make_data.log')
logger.__name__ = 'make_data'

# ensure the directory tree exists to put the data
interim_dir = os.path.abspath('../data/interim')
enrich_all_out = os.path.join(interim_dir, 'origin_enrich_all.csv')
closest_out = os.path.join(interim_dir, 'closest.csv')

if not os.path.exists(interim_dir):
    os.makedirs(interim_dir)
    logger.info('Created interim data directory.')
else:
    logger.info('Interim data directory already exists.')

# enrich all contributing origin geographies with all available demographics
if not os.path.exists(enrich_all_out):
    try:
        logger.info(f'Starting to enrich {origin_customer_areas}.')
        enrich_df = enrich_all(origin_customer_areas, id_field=origin_customer_area_id_field)
        enrich_df.columns = ['origin_id' if c == origin_customer_area_id_field else c for c in enrich_df.columns]
        enrich_df.to_csv(enrich_all_out)
        logger.info(f'Successfully enriched origin geographies. The output is located at {enrich_all_out}.')

    except Exception as e:
        logger.error(f'Failed to enrich {origin_customer_areas}.\n{e}')

else:
    logger.info(f'Enriched origin geographies already exist at {enrich_all_out}.')

# create a nearest table for all locations
if not os.path.exists(closest_out):
    try:
        logger.info('Starting to find closest locations.')
        nearest_df = closest_dataframe_from_origins_destinations(
            origin_customer_areas, origin_customer_area_id_field, destination_store_locations,
            destination_store_id_field, network_dataset=ba_data.usa_network_dataset, destination_count=6
        )
        nearest_df.to_csv(closest_out)
        logger.info('Successfully solved closest locations.')

    except Exception as e:
        logger.error(f'Failed to solve closest.\n{e}')

else:
    logger.info(f'Closest solution already exists at {closest_out}.')
