"""
Purpose:        Geoenrichment is notoriously a gigantic pain to reproduce. This module provides some functionality
                I have created to stramline this process a little.
Author:         Joel McCune (https://github.com/knu2xs)
DOB:            05 Jun 2019
"""

import pandas as pd
import arcpy
from arcgis.gis import GIS
from arcgis.geoenrichment import Country
import math
import os

# column ID list, it only needs to be populated once, so located here
col_id_lst = None


class EnrichColumn(object):
    """
    Object consolidating much of the overhead work to clean up and get all the information needed to be able to
    perform enrichment for each enrichment column both locally and when using enrichment services.
    """

    def __init__(self, name, alias):
        self.name = name
        self.alias = alias
        self.is_enrich = False
        self.category_id = None
        self.variable_name = None

        self.set_col_id_lst()
        self._check_field()

    def set_col_id_lst(self):
        """
        Populate column ID list if it has not been already.
        :return:
        """
        global col_id_lst
        if col_id_lst is None:
            gis = GIS()
            usa = Country.get('US')
            collections_df = usa.data_collections
            collections_df.reset_index(inplace=True)
            col_id_lst = [v.lower() for v in collections_df['dataCollectionID'].unique()]
            col_id_lst.sort()

    def _get_category(self):
        global col_id_lst
        df = pd.DataFrame(columns=['candidate', 'seg_count'])
        df['candidate'] = [col_id for col_id in col_id_lst if col_id + '_' in self.name]
        df['seg_count'] = df['candidate'].apply(lambda val: len(val.split('_')))
        maxidx = df['seg_count'].idxmax()
        return df.iloc[maxidx]['candidate']

    def _check_field(self):
        global col_id_lst

        # check the field status against all the collection ids
        for col_id in col_id_lst:
            if col_id + '_' in self.name.lower():
                self.is_enrich = True
                self.category_id = col_id
                self.variable_name = self.name.replace(self.category_id + '_', '')
                break

    @property
    def local_enrich_name(self):
        return '.'.join([self.category_id, self.variable_name])

    @property
    def rest_enrich_name(self):
        return '_'.join([self.category_id, self.variable_name])

    @property
    def as_dict(self):
        self_dict = self.__dict__
        self_dict['local_enrich_name'] = self.local_enrich_name
        self_dict['rest_enrich_name'] = self.rest_enrich_name
        return self_dict


def _enrich_using_enrich_dataframe(enrich_df, in_fc, out_fc):
    """
    Function consolidating the steps for enriching from an enrich DataFrame
    :param enrich_df: Enrich dataframe created using scripts in this module.
    :param in_fc: String path to the feature class to be enriched.
    :param out_fc: String path to where the output feature class will be stored.
    :return: String path to the output enriched Feature Class.
    """
    name_field_column = 'variable_name'
    analysis_field_column = 'local_enrich_name'
    enrich_threshold = 15000  # roughly the maximum number of features the enrich tool has reliably handled for me
    select_threshold = 1000   # roughly the maximum number of features I've been able to select at a time

    #  any potential duplicate variables
    enrich_df.drop_duplicates(name_field_column, keep='first', inplace=True)

    # combine the enrich variables in a string to be used as an input parameter
    enrich_string = enrich_df[analysis_field_column].str.cat(sep=';')

    # ensure the path is being used for the input feature class since it could be a layer
    in_pth = arcpy.Describe(in_fc).catalogPath

    # since the Enrich tool pukes with too much data, get the count and batch the process
    feature_count = int(arcpy.management.GetCount(in_pth)[0])

    if feature_count > enrich_threshold:

        # create a list of individual query statements for each feature
        oid_list = [r[0] for r in arcpy.da.SearchCursor(in_pth, 'OID@')]
        oid_fld = arcpy.Describe(in_pth).OIDFieldName
        query_lst = [f'{oid_fld} = {oid}' for oid in oid_list]

        # break the list into chunks
        query_chunk_count = math.ceil(feature_count / select_threshold)
        oid_chunk_lst = [query_lst[idx * select_threshold: (idx + 1) * select_threshold]
                         for idx in range(query_chunk_count)]
        query_chunk_lst = [' OR '.join(chunk) for chunk in oid_chunk_lst]

        # create a layer to speed up the iterative process
        in_lyr = arcpy.management.MakeFeatureLayer(in_pth)[0]

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
                        arcpy.management.SelectLayerByAttribute(in_lyr, selection_type='NEW_SELECTION',
                                                                where_clause=query)

                    # otherwise, add to the selection
                    else:
                        arcpy.management.SelectLayerByAttribute(in_lyr, selection_type='ADD_TO_SELECTION',
                                                                where_clause=query)

            # run enrichment for chunk
            enrich_chunk_fc = arcpy.ba.EnrichLayer(
                in_features=in_lyr,
                out_feature_class=os.path.join(arcpy.env.scratchGDB, 'enrich_{:04d}'.format(enrich_idx)),
                variables=enrich_string
            )[0]

            # add the enriched chunk to the list
            enriched_chunk_lst.append(enrich_chunk_fc)

            # ensure features deselected
            arcpy.management.SelectLayerByAttribute(in_lyr, selection_type='CLEAR_SELECTION')

        # combine all the chunked outputs together
        enrich_fc = arcpy.management.Merge(enriched_chunk_lst, out_fc)

    else:
        # run enrichment
        enrich_fc = arcpy.ba.EnrichLayer(
            in_features=in_pth,
            out_feature_class=out_fc,
            variables=enrich_string
        )[0]

    return enrich_fc


def _get_enrich_dataframe_from_enriched_feature_class(input_enriched_feature_class):
    """
    From an already enriched feature class, get a DataFrame describing the enrichment variables used.
    :param input_enriched_feature_class: String path to already enriched feature class.
    :return: DataFrame with enriched variables.
    """

    # get a list of enrich field objects
    fc_fields = [EnrichColumn(f.name, f.aliasName) for f in arcpy.ListFields(input_enriched_feature_class)]

    # filter out just valid enrichment fields
    enrichment_fields = [fld for fld in fc_fields if fld.is_enrich]

    # create a dataframe from all the enrichment fields
    df = pd.DataFrame([f.as_dict for f in enrichment_fields])

    # drop the is_enrich column
    df.drop(['is_enrich'], axis=1, inplace=True)

    # remove any duplicate enrichment variables
    df.drop_duplicates('variable_name', inplace=True)

    return df


def using_csv_variable_file(input_feature_class, path_to_csv_variable_file, output_feature_class):
    """
    Enrich a feature class using variables from a previosuly saved csv file.
    :param input_feature_class: String path to feature class to be enriched.
    :param path_to_csv_variable_file: Path for where to find CSV file defining variables for enrichment.
    :param output_feature_class: String path where enriched features will be saved.
    :return: String path to enriched feature class.
    """
    # read the saved enrich variable feature class and remove any potential duplicate variables
    enrich_var_df = pd.read_csv(path_to_csv_variable_file)

    # perform enrichment
    return _enrich_using_enrich_dataframe(enrich_var_df, input_feature_class, output_feature_class)


def using_existing_enriched_feature_class_as_template(template_feature_class, input_feature_class_to_enrich,
                                                      output_enriched_feature_class):
    """
    Enrich a feature class using a previously enriched feature class as a template.
    :param template_feature_class: Feature Class to be used as a template for enrichment.
    :param input_feature_class_to_enrich: Feature Class to inherit enrichment.
    :param output_enriched_feature_class: Output enriched Feature Class
    :return: String path to enriched Feature Class
    """
    # get a dataframe of enrichment variables
    enrich_df = _get_enrich_dataframe_from_enriched_feature_class(template_feature_class)

    # perform enrichment
    return _enrich_using_enrich_dataframe(enrich_df, input_feature_class_to_enrich, output_enriched_feature_class)


def export_enrichment_csv_variable_file(enriched_feature_class, output_csv_variable_file):
    """
    Create a variable list CSV file from an enriched feature class.
    :param enriched_feature_class: Enriched feature class to inspect.
    :param output_csv_variable_file: Output CSV variable file to be created.
    :return: String path to output CSV file.
    """
    # create the dataframe
    enrich_df = _get_enrich_dataframe_from_enriched_feature_class(enriched_feature_class)

    # save the dataframe as a CSV file
    enrich_df.to_csv(output_csv_variable_file)

    return output_csv_variable_file
