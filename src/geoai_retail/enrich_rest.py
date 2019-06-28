import tempfile
import uuid
import os
from typing import List, Any, Union

import pandas as pd
import numpy as np
from collections import namedtuple
from functools import reduce
from arcgis import geoenrichment
from arcgis.features import FeatureSet
from arcgis.gis import GIS
import requests
import math
import json

import sys

from pandas import DataFrame

sys.path.append('./')
import utils

# location to store temp files if necessary
csv_file_prefix = 'temp_enrich'
temp_file_root = os.path.join(tempfile.gettempdir(), csv_file_prefix)


def get_online_variable_list(variable_list_to_lookup, gis, exclude_five_year_projections=True):
    """
    From an input variable list derived from a dataset already enriched, use ArcGIS Online to look up a list of enrichment
        variables to use for performing enrichment on another new dataset.
    :param variable_list_to_lookup: List of field/column names from an dataset already enriched.
    :param exclude_five_year_projections: Boolean to indicate if to consider the future year (five year projection) variables.
    """
    # get the data available in the USA
    usa = geoenrichment.Country.get('USA')
    enrich_df = usa.data_collections

    # if excluding the five year projections, drop them out
    if exclude_five_year_projections:
        five_year_out = str(
            np.max([int(val) for val in enrich_df['vintage'].unique() if pd.notna(val) and not '-' in val]))
        enrich_df = enrich_df[enrich_df['vintage'] != five_year_out].copy()

    # slice off the variable name in a separate column
    enrich_df['variable_name'] = enrich_df['analysisVariable'].apply(lambda val: val.split('.')[1])

    # drop any variable name duplicates
    enrich_df = enrich_df.drop_duplicates('variable_name')

    # flag variables we want to use for enriching the new data
    var_match = enrich_df['variable_name'].apply(lambda var_name: var_name in variable_list_to_lookup)

    # create a list of the analysis variables usable for enrichment
    return list(enrich_df[var_match]['analysisVariable'].values)


def get_enrichment_alias_dataframe(variable_list_to_lookup, gis):

    # make sure we have a GIS object
    assert isinstance(gis, GIS)

    # get the data available in the USA
    usa = geoenrichment.Country.get('USA')
    enrich_df = usa.data_collections

    # slice off the variable name in a separate column
    enrich_df['variable_name'] = enrich_df['analysisVariable'].apply(lambda val: val.split('.')[1])

    # drop any variable name duplicates
    enrich_df = enrich_df.drop_duplicates('variable_name')

    # flag variables from the input
    var_match = enrich_df['variable_name'].apply(lambda var_name: var_name in variable_list_to_lookup)

    # create a dataframe of just the matching variables
    alias_df = enrich_df[var_match]

    # filter out only needed columns
    alias_df = alias_df[['variable_name', 'analysisVariable', 'alias']]

    # rename columns
    alias_df.columns = ['variable_name', 'enrichment_name', 'alias_name']

    return alias_df.reset_index(drop=True)


def get_enrich_limits(gis):
    # get the limitations for the enrichment service
    limits_resp = gis._con.get(f'{gis.properties.helperServices.geoenrichment.url}/Geoenrichment/ServiceLimits')

    # extract out and reformat the limits
    limits_lst = limits_resp['serviceLimits']['value']
    limits_dict = {itm['paramName']: itm['value'] for itm in limits_lst}

    # save the values into a named tuple
    EnrichLimits = namedtuple('EnrichLimits', ['max_record_count', 'max_collections', 'max_fields', 'max_study_areas'])
    enrich_limits = EnrichLimits(limits_dict['maxRecordCount'], limits_dict['maximumDataCollections'],
                                 limits_dict['maximumOutFieldsNumber'], limits_dict['maximumStudyAreasNumber'])
    return enrich_limits


def _enrich_to_csv(geo_df, var_lst, gis):
    temp_csv = f'{temp_file_root}_{uuid.uuid4().hex}.csv'
    enrich_df = _enrich_wrapper(geo_df, var_lst, gis)
    enrich_df.to_csv(temp_csv)
    return temp_csv


def _enrich_wrapper(geo_df, variable_lst, gis):
    max_collections = get_enrich_limits(gis).max_collections

    var_df = pd.DataFrame([[var] + var.split('.') for var in variable_lst],
                          columns=['enrich_var', 'collection', 'var_name'])
    collections = var_df.collection.unique()
    collection_cnt = collections.size

    # pre-cook the feature set json for making enrich rest requests
    study_areas = geo_df.spatial.to_featureset().to_json

    # since this process can span a long time, ensure token is current
    gis._con.relogin()

    def _enrich_short(enrich_vars):

        # convert the enrich_vars to string as well
        analysis_vars = '[' + ','.join(enrich_vars) + ']'

        # build the request payload
        payload = json.dumps({
            'studyAreas': study_areas,
            'analysisVariables': analysis_vars,
            'returnGeometry': 'false',
            'token': gis._con.token,
            'f': 'json'
        })

        # post using requests because gis._con.post cannot seem to handle it
        resp = requests.post(f'{gis.properties.helperServices.geoenrichment.url}/Geoenrichment/Enrich', json=payload)
        resp
        return resp

    if collection_cnt > max_collections:

        var_df_blocks = [var_df[var_df['collection'].isin(collections[idx:idx + max_collections])]
                         for idx in range(0, collection_cnt, max_collections)]

        enrich_var_blocks = [list(var_blk['enrich_var'].values) for var_blk in var_df_blocks]

        enrich_df_lst = [_enrich_short(enrich_block) for enrich_block in enrich_var_blocks]

        enrich_df = reduce(lambda left, right: pd.merge(left, right), enrich_df_lst)

    else:
        enrich_df = _enrich_short(variable_lst)

    return enrich_df


def enrich(input_data, input_data_id_col, variable_list, gis):
    # get the data into a dataframe
    geo_df = utils.get_dataframe(input_data)

    # get the limitations on the enrichment rest endpoint, and scale the analysis based on this
    enrich_limits = get_enrich_limits(gis)
    max_study_areas = enrich_limits.max_study_areas  # since the service so frequently has issues

    # if necessary, batch the analysis based on the size of the input data, and the number of destinations per origin
    if len(geo_df.index) > max_study_areas:

        # process each batch, and save the results to a temp file in the temp directory
        enrich_csv_list = [_enrich_to_csv(geo_df.iloc[idx:idx + max_study_areas], variable_list, gis)
                           for idx in range(0, len(geo_df.index), max_study_areas)]

        # load all the temporary files into dataframes and combine them into a single dataframe
        enrich_df = pd.concat([pd.read_csv(enrich_csv) for enrich_csv in enrich_csv_list])

        # clean up the temp files
        for csv_file in enrich_csv_list:
            os.remove(csv_file)

    else:
        enrich_df = _enrich_wrapper(geo_df, variable_list, gis)

    # get a list of just the columns requested
    col_lst = [input_data_id_col] + [var.split('.')[1] for var in variable_list]

    return enrich_df[col_lst].copy()
