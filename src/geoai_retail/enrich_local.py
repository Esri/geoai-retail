from glob import glob
import logging
import math
import os
import queue
import threading
import multiprocessing

import arcpy
import pandas as pd

from ba_data_paths import ba_data
from geoai_retail.utils import get_logger, blow_chunks

# get a logger to track issues
logger = get_logger('DEBUG', './enrich_local.log')


def _get_enrich_var_df(enrich_template_fc: str) -> pd.DataFrame:
    """Get the enrichment variable dataframe."""
    # get a dataframe of all the available enrichment fields
    ba_flds_df = ba_data.get_enrich_vars_dataframe(drop_duplicates=False)

    # get the list of fields from the enrichment template feature class
    fc_enrich_flds = [f.name.upper() for f in arcpy.ListFields(enrich_template_fc)]

    # filter dataframe to only fields in the template feature class
    return ba_flds_df[ba_flds_df['enrich_field_name'].str.upper().isin(fc_enrich_flds)]


def _get_enrich_var_lst(enrich_template_fc: str) -> list:
    """Get the enrichment variable list properly formatted for the Enrich Layer tool."""
    enrich_df = _get_enrich_var_df(enrich_template_fc)

    # from the filtered dataframe, get just the enrich variable names as a list
    return list(enrich_df['enrich_str'].values)


def _enrich_wrapper(enrich_var_lst: list, feature_class_to_enrich: str, output_enriched_feature_class: str,
                    enrich_threshold: int = 500) -> str:
    """Wrapper around Enrich function to make it work"""
    # ensure using local ba_data
    ba_data.set_to_usa_local()

    # ensure the path is being used for the input feature class since it could be a layer
    enrich_fc = arcpy.Describe(feature_class_to_enrich).catalogPath
    out_gdb = os.path.dirname(output_enriched_feature_class)

    # since the Enrich tool pukes with too much ba_data, get the count and batch the process if necessary
    feature_count = int(arcpy.management.GetCount(enrich_fc)[0])
    if feature_count > enrich_threshold:

        # create a list of individual query statements for each feature
        oid_list = [r[0] for r in arcpy.da.SearchCursor(enrich_fc, 'OID@')]
        oid_fld = arcpy.Describe(enrich_fc).OIDFieldName
        query_lst = [f'{oid_fld} = {oid}' for oid in oid_list]

        # break the list into chunks to select features in chunks up to the enrich threshold
        oid_chunk_lst = blow_chunks(query_lst, enrich_threshold)
        query_chunk_lst = [' OR '.join(chunk) for chunk in oid_chunk_lst]

        # list to put all the chunk processed enrichment feature classes
        enriched_chunk_lst = []

        logger.debug(f'Splitting the enrich task into {len(query_chunk_lst)} chunks.')

        # iterate the query chunks and create the chunked analysis areas
        for enrich_idx, query_chunk in enumerate(query_chunk_lst):

            logger.debug(f'Starting to enrich {enrich_idx+1}/{len(query_chunk_lst)}')

            # extract out a temporary dataset into memory for this loop
            tmp_features = arcpy.analysis.Select(
                in_features=feature_class_to_enrich,
                out_feature_class=os.path.join(out_gdb, f'in_enrich_chunk_{enrich_idx:04d}'),
                where_clause=query_chunk
            )[0]

            # enrich just these features
            enrich_fc = arcpy.ba.EnrichLayer(
                in_features=tmp_features,
                out_feature_class=os.path.join(out_gdb, f'tmp_enrich{enrich_idx:04d}'),
                variables=enrich_var_lst
            )[0]

            # delete the temporary input ba_data
            arcpy.management.Delete(tmp_features)

            # add this iteration to the enriched chunks
            enriched_chunk_lst.append(enrich_fc)

            logger.debug(f'Finished enriching {enrich_idx + 1}/{len(query_chunk_lst)}')

        # combine all the chunked outputs together
        enrich_fc = arcpy.management.Merge(enriched_chunk_lst, output_enriched_feature_class)

        # take out the trash
        for fc in enriched_chunk_lst:
            arcpy.management.Delete(fc)

    else:
        enrich_fc = arcpy.ba.EnrichLayer(
            in_features=enrich_fc,
            out_feature_class=output_enriched_feature_class,
            variables=enrich_var_lst
        )[0]

    return enrich_fc


def enrich_from_enriched(enrich_template_feature_class: str, feature_class_to_enrich: str,
                         output_enriched_feature_class: str) -> str:
    """
    Enrich a new dataset using a previously enriched dataset as a template.
    :param enrich_template_feature_class: String path to a previously enriched feature class.
    :param feature_class_to_enrich: Feature class to be enriched.
    :param output_enriched_feature_class: String path to where the newly enriched feature class will be saved.
    :return: String path to the newly enriched feature class.
    """
    # ensure the path is being used for the input feature class since it could be a layer
    tmpl_fc = arcpy.Describe(enrich_template_feature_class).catalogPath

    # get the enrich variables and combine into semicolon separated string
    enrich_var_lst = _get_enrich_var_lst(tmpl_fc)

    return _enrich_wrapper(enrich_var_lst, feature_class_to_enrich, output_enriched_feature_class)


def enriched_fields_to_csv(enrich_template_feature_class: str, output_csv_file: str) -> str:
    """
    Save a dataframe for the variables from the enriched dataset to a dataframe.
    :param enrich_template_feature_class: String path to a previously enriched feature class.
    :param output_csv_file: String path to where the CSV file will be saved
    :return: String path to the output CSV file.
    """
    # get the dataframe for the enriched fields in the template feature class
    enrich_df = _get_enrich_var_df(enrich_template_feature_class)

    # save to the csv
    enrich_df.to_csv(output_csv_file)

    return output_csv_file


def enrich_from_fields_table(enrich_table: str, feature_class_to_enrich: str,
                             output_enriched_feature_class: str) -> str:
    """
    Enrich the input features using a saved enrichment table.
    :param enrich_table: Pandas Dataframe or string path to saved CSV file with same schema.
    :param feature_class_to_enrich: String path to feature class to be enriched.
    :param output_enriched_feature_class: String path to location where the enriched feature class will be saved.
    :return: String path to output enriched feature class.
    """
    # handle the input, whether a CSV file or a dataframe
    if isinstance(enrich_table, str) and enrich_table.endswith('.csv'):
        enrich_tbl = enrich_table.read_csv(enrich_table)
    elif isinstance(enrich_table, pd.DataFrame):
        enrich_tbl = enrich_table
    else:
        raise Exception('enrich_table must be either a CSV file or a Pandas Dataframe')

    # create the enrich string formatted for input into the Enrich tool
    enrich_var_lst = list(enrich_tbl['enrich_str'].values)

    return _enrich_wrapper(enrich_var_lst, feature_class_to_enrich, output_enriched_feature_class)


def enrich_all(feature_class_to_enrich: str, output_enriched_feature_class: str) -> str:
    """
    Enrich the input features with all available local variables.
    :param feature_class_to_enrich: String path to feature class to be enriched.
    :param output_enriched_feature_class: String path to location where the enriched feature class will be saved.
    :return: String path to output enriched feature class.
    """
    enrich_tbl = ba_data.enrich_vars_dataframe
    enrich_var_lst = list(enrich_tbl['enrich_str'].values)
    return _enrich_wrapper(enrich_var_lst, feature_class_to_enrich, output_enriched_feature_class)