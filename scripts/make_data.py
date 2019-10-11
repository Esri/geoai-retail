import os
from pathlib import Path

from ba_data_paths import ba_data
from geoai_retail.enrich import enrich_all
from geoai_retail.utils import get_logger
from geoai_retail.proximity import closest_dataframe_from_origins_destinations
from scripts.data_sources import origin_customer_areas, origin_customer_area_id_field, destination_store_locations, \
    destination_store_id_field, destination_competition_locations, destination_competition_id_field

# create a logger to save into the same directory
logger = get_logger('DEBUG', '../data/interim/make_data.log')
logger.__name__ = 'make_data'

# ensure the directory tree exists to put the data
interim_dir = Path(os.path.abspath('../data/interim'))
interim_dir.mkdir(parents=True, exist_ok=True)

enrich_all_out = interim_dir/'origin_enrich_all.csv'
closest_store_out = interim_dir/'closest_store.csv'
closest_competition_out = interim_dir/'closest_competition.csv'

# enrich all contributing origin geographies with all available demographics
if not enrich_all_out.exists():
    try:
        logger.info(f'Starting to enrich {origin_customer_areas}.')
        enrich_df = enrich_all(origin_customer_areas, id_field=origin_customer_area_id_field)
        enrich_df.columns = ['origin_id' if c == origin_customer_area_id_field else c for c in enrich_df.columns]
        enrich_df.to_csv(str(enrich_all_out))
        logger.info(f'Successfully enriched origin geographies. The output is located at {str(enrich_all_out)}.')

    except Exception as e:
        logger.error(f'Failed to enrich {origin_customer_areas}.\n{e}')

else:
    logger.info(f'Enriched origin geographies already exist at {str(enrich_all_out)}.')

# create a nearest table for all store locations
if not closest_store_out.exists():
    try:
        logger.info('Starting to find closest store locations.')
        nearest_df = closest_dataframe_from_origins_destinations(
            origin_customer_areas, origin_customer_area_id_field, destination_store_locations,
            destination_store_id_field, network_dataset=ba_data.usa_network_dataset, destination_count=6
        )
        nearest_df.to_csv(str(closest_store_out))
        logger.info('Successfully solved closest store locations.')

    except Exception as e:
        logger.error(f'Failed to solve closest stores.\n{e}')

else:
    logger.info(f'Closest store solution already exists at {str(closest_store_out)}.')

# create a nearest table for all competition locations
if not closest_competition_out.exists():
    try:
        logger.info('Starting to find closest competition locations')
        nearest_df = closest_dataframe_from_origins_destinations(
            origin_customer_areas, origin_customer_area_id_field, destination_competition_locations,
            destination_competition_id_field, network_dataset=ba_data.usa_network_dataset, destination_count=6
        )
        nearest_df.columns = [c.replace('proximity', 'proximity_competition') for c in nearest_df.columns]
        nearest_df.to_csv(str(closest_competition_out))
        logger.info('Successfully solved closest competition locations.')

    except Exception as e:
        logger.error(f'Failed to solve closest competition.\n{e}')

else:
    logger.info(f'Closest competition solution already exists at {str(closest_competition_out)}')
