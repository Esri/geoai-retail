import os

from arcgis.features import GeoAccessor
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


def _enrich_wrapper(enrich_var_lst:list, feature_class_to_enrich:str, id_field:str=None,
                    input_feature_class_fields_in_output:bool=False, return_geometry:bool=False,
                    enrich_threshold:int=1000) -> pd.DataFrame:
    """Wrapper around Enrich function to make it work"""
    # ensure using local ba_data
    ba_data.set_to_usa_local()

    # if an ID field is provided, use it, but if not, use the OID field
    id_fld = id_field if id_field else arcpy.Describe(feature_class_to_enrich).OIDFieldName

    # ensure the path is being used for the input feature class since it could be a layer
    enrich_fc = arcpy.Describe(feature_class_to_enrich).catalogPath
    out_gdb = arcpy.env.scratchGDB

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

            # write the run result to the output geodatabase
            enrich_fc = arcpy.ba.EnrichLayer(
                in_features=tmp_features,
                out_feature_class=os.path.join(out_gdb, f'enrich_fc_{enrich_idx:04d}'),
                variables=';'.join(enrich_var_lst)
            )[0]

            # delete the temporary input ba_data
            arcpy.management.Delete(tmp_features)

            # add this iteration to the enriched chunks
            enriched_chunk_lst.append(enrich_fc)

            logger.debug(f'Finished enriching {enrich_idx + 1}/{len(query_chunk_lst)}')

        # combine all the chunked outputs together
        enrich_fc = arcpy.management.Merge(enriched_chunk_lst, os.path.join(out_gdb, 'enriched_data'))

        # take out the trash
        for fc in enriched_chunk_lst:
            arcpy.management.Delete(fc)

    else:
        enrich_fc = arcpy.ba.EnrichLayer(
            in_features=enrich_fc,
            out_feature_class=os.path.join(out_gdb, 'enriched_data'),
            variables=';'.join(enrich_var_lst)
        )[0]

    # convert the output to a Spatially Enabled Dataframe
    enrich_df = GeoAccessor.from_featureclass(enrich_fc)

    # remove the temporary data
    arcpy.management.Delete(enrich_fc)

    # start putting together a list of fields to drop for cleanup
    drop_fld_lst = ['aggregationMethod']

    # if only desiring the enrich variables in the output
    if not input_feature_class_fields_in_output:
        drop_fld_lst.extend([f.name for f in arcpy.ListFields(feature_class_to_enrich)
                             if f.name != id_fld and f.name.upper() != 'SHAPE'])

    # if geometry is not desired as an output
    if not return_geometry:
        drop_fld_lst.append('SHAPE')

    # ensure the columns to drop are actually in the dataframe
    drop_fld_lst = [col for col in drop_fld_lst if col in list(enrich_df.columns)]

    # clean up the dataframe fields
    enrich_df.drop(drop_fld_lst, axis=1, inplace=True)

    return enrich_df


def enrich_from_enriched(enrich_template_feature_class:str, feature_class_to_enrich:str, id_field:str=None,
                         input_feature_class_fields_in_output:bool=False, return_geometry:bool=False) -> pd.DataFrame:
    """
    Enrich a new dataset using a previously enriched dataset as a template.
    :param enrich_template_feature_class: String path to a previously enriched feature class.
    :param feature_class_to_enrich: Feature class to be enriched.
    :param id_field: Optional field uniquely identifying every area to be enriched. If not provided, the OBJECTID will
        be used.
    :param input_feature_class_fields_in_output: Optional boolean indicating if the attribute fields from the original
        feature class should be retained in the output.
    :return: Spatially Enabled Dataframe.
    """
    # ensure the path is being used for the input feature class since it could be a layer
    tmpl_fc = arcpy.Describe(enrich_template_feature_class).catalogPath

    # get the enrich variables and combine into semicolon separated string
    enrich_var_lst = _get_enrich_var_lst(tmpl_fc)

    return _enrich_wrapper(enrich_var_lst, feature_class_to_enrich, id_field, input_feature_class_fields_in_output,
                           return_geometry)


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


def enrich_from_fields_table(enrich_table:str, feature_class_to_enrich:str, id_field:str=None,
                         input_feature_class_fields_in_output:bool=False, return_geometry:bool=False) -> pd.DataFrame:
    """
    Enrich the input features using a saved enrichment table.
    :param enrich_table: Pandas Dataframe or string path to saved CSV file with same schema.
    :param feature_class_to_enrich: String path to feature class to be enriched.
    :param id_field: Optional field uniquely identifying every area to be enriched. If not provided, the OBJECTID will
        be used.
    :param input_feature_class_fields_in_output: Optional boolean indicating if the attribute fields from the original
        feature class should be retained in the output.
    :return: Spatially Enabled Dataframe.
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

    return _enrich_wrapper(enrich_var_lst, feature_class_to_enrich, id_field, input_feature_class_fields_in_output,
                           return_geometry)


def enrich_by_collection(enrich_collection:str, feature_class_to_enrich:str, id_field:str=None,
                         input_feature_class_fields_in_output:bool=False, return_geometry:bool=False) -> pd.DataFrame:
    """
    Enrich the input features with all available local variables.
    :param enrich_collection: Collection name to use for enrichment.
    :param feature_class_to_enrich: String path to feature class to be enriched.
    :param id_field: Optional field uniquely identifying every area to be enriched. If not provided, the OBJECTID will
        be used.
    :param input_feature_class_fields_in_output: Optional boolean indicating if the attribute fields from the original
        feature class should be retained in the output.
    :return: String path to output enriched feature class.
    """
    # get the full dataframe of available variables
    vars_df = ba_data.enrich_vars_dataframe

    # convert everything to uppercase for comparisons - so a mismatch is not due simply to mismatched case
    vars_df['collection_name'] = vars_df['collection_name'].str.upper()
    enrich_collection = enrich_collection.upper()

    # check to ensure the provided collection is available
    collections = vars_df['collection_name'].unique()
    if enrich_collection not in vars_df['collection_name'].unique():
        raise Exception(f'The provided enrich_collection, {enrich_collection}, does not appear to be one of the locally'
                        f'available collections for enrichment. The available collections are {collections}')

    # get a list of the variables just in this collection
    enrich_vars = vars_df[vars_df['collection_name'] == enrich_collection]['enrich_str'].values

    # enrich, yo
    return _enrich_wrapper(enrich_vars, feature_class_to_enrich, id_field, input_feature_class_fields_in_output,
                           return_geometry)


def enrich_all(feature_class_to_enrich:str, id_field:str=None,
               input_feature_class_fields_in_output:bool=False, return_geometry:bool=False) -> pd.DataFrame:
    """
    Enrich the input features with all available local variables.
    :param feature_class_to_enrich: String path to feature class to be enriched.
    :param id_field: Optional field uniquely identifying every area to be enriched. If not provided, the OBJECTID will
        be used.
    :param input_feature_class_fields_in_output: Optional boolean indicating if the attribute fields from the original
        feature class should be retained in the output.
    :return: Spatially Enabled Dataframe
    """
    # set the location where temporary output will be saved, the Scratch GeoDatabase
    output_gdb = arcpy.env.scratchGDB
    arcpy.env.workspace = output_gdb

    # if an ID field is provided, use it, but if not, use the OID field
    id_fld = id_field if id_field else arcpy.Describe(feature_class_to_enrich).OIDFieldName

    # since there can be issues with enriching using all variables at once, we enrich by collection.
    # this not only chunks up the process, but also makes debugging issues much easier as well
    fail_lst = []

    # enrich by collection with the ability to overcome failed collections
    collection_lst = ba_data.enrich_vars_dataframe['collection_name'].unique()
    for idx, collection in enumerate(ba_data.enrich_vars_dataframe['collection_name'].unique()):
        try:
            coll_enrich_df = enrich_by_collection(collection, feature_class_to_enrich, id_field,
                                                  input_feature_class_fields_in_output, return_geometry)
            # if the first one, create and configure the seed Spatially Enabled Dataframe
            if idx == 0:
                enrich_df = coll_enrich_df.copy()

                # if there is an id_field provided, do not need the 'OBJECTID' column
                if id_field and 'OBJECTID' in enrich_df.columns:
                    enrich_df.drop('OBJECTID', axis=1, inplace=True)

                logger.info(f'Success, {collection} collection created as seed dataframe from '
                            f'with {len(enrich_df.columns)} columns - {idx + 1}/{len(collection_lst)}')

            else:
                # create a dataframe from the enriched feature class and add only new fields onto the master dataframe
                add_df = coll_enrich_df.copy()
                new_cols = add_df.columns.difference(enrich_df.columns)
                add_df.set_index(id_fld, drop=True, inplace=True)
                enrich_df = enrich_df.merge(add_df[new_cols], on=id_fld, right_index=True)

                logger.info(f'Success, {collection} collection added with {len(new_cols)} new columns to the combined '
                            f'dataframe, now with {len(enrich_df.columns)} columns - {idx + 1}/{len(collection_lst)}')

        except Exception as e:
            fail_lst.append(collection)
            logger.exception(f'Fail - {collection}\ne')

    # set the index
    enrich_df.set_index(id_fld, drop=True, inplace=True)

    return enrich_df
