import logging
import os
import uuid

import arcpy

from geoai_retail import enrich_local as enrich
from ba_data_paths import ba_data

enrich_template_fc = './test_data.gdb/block_groups_enrich_template'
block_groups_fc = './test_data.gdb/block_groups'
blocks_fc = './test_data.gdb/blocks'

interim_gdb = os.path.abspath('../../ba_data/interim/interim.gdb')

arcpy.env.overwriteOutput = True


def get_logger(loglevel='WARNING', logfile=None):
    log = logging.getLogger(__name__)
    log.setLevel(loglevel)

    c_handler = logging.StreamHandler()
    if logfile is None:
        f_handler = logging.FileHandler(f'{__name__}_logfile.log')
    else:
        f_handler = logging.FileHandler(logfile)

    for handler in [c_handler, f_handler]:
        handler.setLevel('DEBUG')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        log.addHandler(handler)

    return log


def get_first_feature(fc):
    first_oid = [val for val in arcpy.da.SearchCursor(fc, 'OID@')][0][0]
    sql_str = f'{arcpy.Describe(fc).OIDFieldName} = {first_oid}'
    return arcpy.analysis.Select(fc, 'memory/first_feature', sql_str)[0]


def flush_enrich_output(gdb: str) -> bool:
    arcpy.env.workspace = gdb
    fc_lst = [os.path.join(gdb, fc) for fc in arcpy.ListFeatureClasses('enrich_*')]
    if len(fc_lst):
        for fc in fc_lst:
            arcpy.Delete_management(fc)
    return True


if __name__ == '__main__':

    logger = get_logger('DEBUG')

    flush_enrich_output(interim_gdb)

    enrich_var_df = ba_data.enrich_vars_dataframe
    collections = enrich_var_df['collection_name'].unique()
    single_block = get_first_feature(block_groups_fc)

    successful_collections = []
    unsuccessful_collections = []

    for collection in collections:

        coll_var_df = enrich_var_df[enrich_var_df['collection_name'] == collection]

        logger.debug(f'Starting to enrich collection {collection}.')
        try:
            out_path = os.path.join(interim_gdb, f'enrich_{collection.split(".")[0]}')
            enrich.enrich_from_fields_table(coll_var_df, single_block, out_path)
            logger.debug(f'Successfuly enriched collection {collection}.')
            successful_collections.append(collection)
        except Exception as e:
            logger.exception(f'Failed to enrich collection {collection}.')
            unsuccessful_collections.append(collection)

    if len(successful_collections):
        logger.info('Successful collections {}'. format(', '.join(successful_collections)))

    if len(unsuccessful_collections):
        logger.info('UNSuccessful collections {}'.format(', '.join(unsuccessful_collections)))
    else:
        logger.info('NO UNSuccessful collections - life is good!')
