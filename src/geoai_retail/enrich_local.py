from glob import glob
import math
import os

import arcpy
import pandas as pd

from ba_data_paths import ba_data

# get the path to the installed documentation where the variable information is stored
ba_xls_search_string = search_string = os.path.join(ba_data.usa_data_path,
                                                    'Documentation\\*_BA_Desktop_Variable_and_Report_List.xlsx')
ba_xls = glob(search_string)[0]


def _read_ba_xls_sheet(sheet):
    """Get documented variables into a complete list from a sheet in the documentation workbook."""
    # read the sheet in the workbook
    df = pd.read_excel(ba_xls, sheet_name=sheet, usecols=[1, 2, 3, 4, 5], header=5)

    # account for some naming inconsistencies
    df.columns = ['category_description' if col == 'Category' or col == 'Category Name' else col for col in df.columns]

    # replace spaces with underscores and lowercase everything
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]

    return df


def _get_enrich_var_df(enrich_template_fc):
    """Get the enrichment variable dataframe."""
    # get a dataframe of all the available enrichment fields
    ba_flds_df = ba_data.fields_dataframe

    # get the list of fields from the enrichment template feature class
    fc_enrich_flds = [f.name.upper() for f in arcpy.ListFields(enrich_template_fc)]

    # filter dataframe to only fields in the template feature class
    return ba_flds_df[ba_flds_df['enrich_field_name'].str.upper().isin(fc_enrich_flds)]


def _get_enrich_var_lst(enrich_template_fc):
    """Get the enrichment variable list properly formatted for the Enrich Layer tool."""
    enrich_df = _get_enrich_var_df(enrich_template_fc)

    # from the filtered dataframe, get just the enrich variable names as a list
    return list(enrich_df['enrich_str'].values)


def _enrich_wrapper(enrich_var_lst, feature_class_to_enrich, output_enriched_feature_class):
    """Wrapper around Enrich function to make it work"""
    enrich_threshold = 15000  # roughly the maximum number of features the enrich tool has reliably handled for me
    select_threshold = 1000  # roughly the maximum number of features I've been able to select at a time

    # get the enrich variables and combine into semicolon separated string
    enrich_string = ';'.join(enrich_var_lst)

    # ensure the path is being used for the input feature class since it could be a layer
    enrich_fc = arcpy.Describe(feature_class_to_enrich).catalogPath

    # since the Enrich tool pukes with too much data, get the count and batch the process
    feature_count = int(arcpy.management.GetCount(enrich_fc)[0])

    if feature_count > enrich_threshold:

        # create a list of individual query statements for each feature
        oid_list = [r[0] for r in arcpy.da.SearchCursor(enrich_fc, 'OID@')]
        oid_fld = arcpy.Describe(enrich_fc).OIDFieldName
        query_lst = [f'{oid_fld} = {oid}' for oid in oid_list]

        # break the list into chunks
        query_chunk_count = math.ceil(feature_count / select_threshold)
        oid_chunk_lst = [query_lst[idx * select_threshold: (idx + 1) * select_threshold]
                         for idx in range(query_chunk_count)]
        query_chunk_lst = [' OR '.join(chunk) for chunk in oid_chunk_lst]

        # create a layer to speed up the iterative process
        enrich_lyr = arcpy.management.MakeFeatureLayer(enrich_fc)[0]

        # calculate the number of selections it is going to take for each enrichment chunk
        select_count_per_chunk = math.floor(enrich_threshold / select_threshold)

        # list to put all the chunk processed enrichment feature classes
        enriched_chunk_lst = []

        # iteratively enrich subsets of the whole dataset
        for enrich_idx in range(math.ceil(feature_count / enrich_threshold)):

            # iteratively select features up to the enrich threshold
            for select_idx in range(select_count_per_chunk):

                # ensure there are queries left
                if len(query_chunk_lst):

                    # get a query
                    query = query_chunk_lst.pop()

                    # if the first query, make a new query
                    if select_idx == 0:
                        arcpy.management.SelectLayerByAttribute(enrich_lyr, selection_type='NEW_SELECTION',
                                                                where_clause=query)

                    # otherwise, add to the selection
                    else:
                        arcpy.management.SelectLayerByAttribute(enrich_lyr, selection_type='ADD_TO_SELECTION',
                                                                where_clause=query)

            # run enrichment for chunk
            enrich_chunk_fc = arcpy.ba.EnrichLayer(
                in_features=enrich_lyr,
                out_feature_class=os.path.join(arcpy.env.scratchGDB, 'enrich_{:04d}'.format(enrich_idx)),
                variables=enrich_string
            )[0]

            # add the enriched chunk to the list
            enriched_chunk_lst.append(enrich_chunk_fc)

            # ensure features deselected
            arcpy.management.SelectLayerByAttribute(enrich_lyr, selection_type='CLEAR_SELECTION')

        # combine all the chunked outputs together
        enrich_fc = arcpy.management.Merge(enriched_chunk_lst, output_enriched_feature_class)

    else:
        # run enrichment
        enrich_fc = arcpy.ba.EnrichLayer(
            in_features=enrich_fc,
            out_feature_class=output_enriched_feature_class,
            variables=enrich_string
        )[0]

    return enrich_fc


def enrich_from_enriched(enrich_template_feature_class, feature_class_to_enrich, output_enriched_feature_class):
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


def enriched_fields_to_csv(enrich_template_feature_class, output_csv_file):
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


def enrich_from_fields_table(enrich_table, feature_class_to_enrich, output_enriched_feature_class):
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
