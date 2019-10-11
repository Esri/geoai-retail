# import modules
import itertools
import os
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from arcgis.features import GeoAccessor
import arcpy

if sys.version_info > (3, 0):
    import winreg
else:
    import _winreg as winreg


class BA_Data:

    def __init__(self):
        arcpy.env.overwriteOutput = True

    @staticmethod
    def _get_child_keys(key_path):
        """
        Get the full path of first generation child keys under the parent key listed.
        :param key_path: Path to the parent key in registry.
        :return: List of the full path to child keys.
        """
        # open the parent key
        parent_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)

        # variables to track progress and store results
        error = False
        counter = 0
        key_list = []

        # while everything is going good
        while not error:

            try:
                # get the child key in the iterated position
                child_key = winreg.EnumKey(parent_key, counter)

                # add the located key to the list
                key_list.append('{}\\{}'.format(key_path, child_key))

                # increment the counter
                counter += 1

            # when something blows up...typically because no key is found
            except Exception as e:

                # switch the error flag to true, stopping the iteration
                error = True

        # give the accumulated list back
        return key_list

    def _get_first_child_key(self, key_path, pattern):
        """
        Based on the pattern provided, find the key with a matching string in it.
        :param key_path: Full string path to the key.
        :param pattern: Pattern to be located.
        :return: Full path of the first key path matching the provided pattern.
        """
        # get a list of paths to keys under the parent key path provided
        key_list = self._get_child_keys(key_path)

        # iterate the list of key paths
        for key in key_list:

            # if the key matches the pattern
            if key.find(pattern):
                # pass back the provided key path
                return key

    @property
    def _usa_key(self):
        """
        Get the key for the current ba_data installation of Business Analyst ba_data.
        :return: Key for the current ba_data installation of Business Analyst ba_data.
        """
        return self._get_first_child_key(r'SOFTWARE\WOW6432Node\Esri\BusinessAnalyst\Datasets', 'USA_ESRI')

    @property
    def _usa_dataset(self) -> str:
        """
        Return the value needed for setting the environment.
        :return: String value needed for setting the BA Data Environment setting.
        """
        return f'LOCAL;;{os.path.basename(self._usa_key)}'

    def set_to_usa_local(self):
        """
        Set the environment setting to ensure using locally installed local ba_data.
        :return: Boolean indicating if ba_data correctly enriched.
        """
        try:
            arcpy.env.baDataSource = self._usa_dataset
            return True
        except:
            return False

    def _get_business_analyst_key_value(self, locator_key):
        """
        In the Business Analyst key, get the value corresponding to the provided locator key.
        :param locator_key: Locator key.
        :return: Key value.
        """
        # open the key to the current installation of Business Analyst ba_data
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self._usa_key)

        # query the value of the locator key
        return winreg.QueryValueEx(key, locator_key)[0]

    @property
    def usa_locator(self) -> str:
        """
        Path to the address locator installed with Business Analyst USA ba_data.
        :return: String directory path to the address locator installed with Business Analyst USA ba_data.
        """
        return self._get_business_analyst_key_value('Locator')

    @property
    def usa_network_dataset(self) -> str:
        """
        Path to the network dataset installed with Business Analyst USA ba_data.
        :return: String directory path to the network dataset installed with Business Analyst USA ba_data.
        """
        return self._get_business_analyst_key_value('StreetsNetwork')

    @property
    def usa_data_path(self) -> str:
        """
        Path where the Business Analyst USA ba_data is located.
        :return: String directory path to where the Business Analyst USA ba_data is installed.
        """

        return self._get_business_analyst_key_value('DataInstallDir')

    def _create_demographic_layer(self, feature_class_name, layer_name=None):
        """
        Esri Business Analyst standard geography layer with ID and NAME fields.
        :param feature_class_path: Name of the feature class.
        :param layer_name: Output layer name.
        :return: Feature Layer
        """
        # get the path to the geodatabase where the Esri demographics reside
        demographic_dir = os.path.join(self.usa_data_path, 'Data', 'Demographic Data')
        gdb_name = [d for d in os.listdir(demographic_dir) if re.match(r'USA_ESRI_\d{4}\.gdb', d)][0]
        gdb_path = os.path.join(demographic_dir, gdb_name)
        fc_path = os.path.join(gdb_path, feature_class_name)

        # create layer map
        visible_fields = ['Shape', 'ID', 'NAME']

        def _eval_visible(field_name):
            if field_name in visible_fields:
                return 'VISIBLE'
            else:
                return 'HIDDEN'

        field_map_lst = [' '.join([f.name, f.name, _eval_visible(f.name), 'NONE']) for f in arcpy.ListFields(fc_path)]
        field_map = ';'.join(field_map_lst)

        # create and return the feature layer
        if layer_name:
            lyr = arcpy.management.MakeFeatureLayer(fc_path, layer_name, field_info=field_map)[0]
        else:
            lyr = arcpy.management.MakeFeatureLayer(fc_path, field_info=field_map)[0]
        return lyr

    @property
    def layer_block_group(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst Census Block Group layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('BlockGroups_bg', 'block_groups')

    @property
    def layer_cbsa(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst CBSA layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('CBSAs_cb', 'cbsas')

    @property
    def layer_census_tract(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst Census Tract layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('CensusTracts_tr', 'census_tracts')

    @property
    def layer_congressional_district(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst Congressional District layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('CongressionalDistricts_cd', 'congressional_districts')

    @property
    def layer_county(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst county layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('Counties_cy', 'counties')

    @property
    def layer_county_subdivisions(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst county subdivision layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('CountySubdivisions_cs', 'county_subdivision')

    @property
    def layer_dma(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst DMA layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('DMAs_dm', 'dmas')

    @property
    def layer_places(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst Census Places layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('Places_pl', 'places')

    @property
    def layer_states(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst US States layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('States_st', 'states')

    @property
    def layer_postal_code(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst postal code (zip) layer with ID and NAME fields.
        :return: Feature Layer
        """
        return self._create_demographic_layer('ZIPCodes_zp', 'postal_codes')

    @property
    def layer_block_points(self) -> arcpy._mp.Layer:
        """
        Esri Business Analyst block points layer - useful for calculating weighted centroids.
        :return: Feature Layer
        """
        return self._create_demographic_layer()

    @property
    def layer_blocks(self) -> arcpy._mp.Layer:
        """
        US Census Blocks layer
        :return: Feature Layer
        """
        census_gdb = os.path.join(self.usa_data_path, 'Data', 'UserData', 'census.gdb')

        # check to see if the data has benn downloaded - since so big (>3GB), this is problematic to do automatically
        if arcpy.Exists(os.path.join(census_gdb, 'Block')):
            blocks_fc = os.path.join(census_gdb, 'Block')
        elif arcpy.Exists(os.path.join(census_gdb, 'block')):
            blocks_fc = os.path.join(census_gdb, 'block')
        else:
            raise FileNotFoundError(f"The blocks feature class, which should be located at "
                                    f"{os.path.join(census_gdb, 'blocks')} does not appear to exist. You can download "
                                    f"this from "
                                    f"https://www2.census.gov/geo/tiger/TGRGDB18/tlgdb_2018_a_us_block.gdb.zip. Once "
                                    f"downloaded, extract the archive and place the Blocks feature class in "
                                    f"{census_gdb}.")

        # when initially downloaded from the US Census, the ID field is GEOID, but change this to be consistent
        if 'GEOID' in [f.name for f in arcpy.ListFields(blocks_fc)]:
            arcpy.management.AlterField(blocks_fc, field='GEOID', new_field_name='ID', new_field_alias='ID')

        return self._create_demographic_layer(blocks_fc, 'blocks')

    @property
    def layer_businesses(self):
        """Business layer"""
        fc_businesses = os.path.join(self.usa_data_path, r'Data\Business Data\BA_BUS_2018.gdb\us_businesses')
        return arcpy.management.MakeFeatureLayer(fc_businesses)[0]

    def get_business_layer_by_code(self, naics_codes:[int, str, list]=None,
                                   sic_codes:[int, str, list]=None) -> arcpy._mp.Layer:
        """
        Get business layer by NAICS and SIC code.
        :param naics_code:
        :param sic_code:
        :return: Layer with definition query applied filtering to just the NAICS and SIC codes provided.
        """

        def _get_where_clause(field_name:str, codes:[int, str, list]) -> [str, list]:
            if codes is None:
                return None
            elif isinstance(codes, list) or isinstance(codes, np.array):
                codes = [f"{field_name} = '{cd}'" for cd in codes]
                return ' OR '.join(codes)
            else:
                if not isinstance(codes, str):
                    return str(codes)
                else:
                    return codes

        if naics_codes is None and sic_codes is None:
            raise Exception('Either NAICS or SIC codes must be provided.')

        if naics_codes and sic_codes is None:
            sql = _get_where_clause('NAICS', naics_codes)

        if naics_codes is None and sic_codes:
            sql = _get_where_clause('SIC', sic_codes)

        if naics_codes and sic_codes:
            sql = f'{_get_where_clause("NAICS", naics_codes)} OR {_get_where_clause("SIC", sic_codes)}'

        lyr_bus = self.layer_businesses
        lyr_bus.definitionQuery = sql

        return lyr_bus

    def get_business_layer_by_name(self, business_name:str) -> arcpy._mp.Layer:
        """
        Get businesses layer by name.
        :param business_name: String, partial or complete, of the business name.
        :return: Layer of Businesses
        """
        lyr_bus = self.layer_businesses
        lyr_bus.definitionQuery = f"CONAME LIKE '%{business_name.upper()}%'"
        return lyr_bus

    def get_business_competitor_layer(self, business_layer:[arcpy._mp.Layer, str]) -> arcpy._mp.Layer:
        """
        Get a layer of competitors from a existing business layer.
        :param business_layer:
        :return:
        """
        # get a list of NAICS codes in the original business layer to use for selecting businesses
        naics_code_lst = set(r[0] for r in arcpy.da.SearchCursor(business_layer, 'NAICS'))
        naics_sql = ' OR '.join(f"NAICS = '{naics}'" for naics in naics_code_lst)

        # get a list of existing business ids and use for exclusion
        existing_locnum_lst = [r[0] for r in arcpy.da.SearchCursor(business_layer, 'LOCNUM')]
        existing_sql = ' AND '.join([f"LOCNUM <> '{locnum}'" for locnum in existing_locnum_lst])

        # combine the naics selection and locnum exclusion
        sql = f"{naics_sql} AND ({existing_sql})"

        # create the layer and apply the query
        comp_lyr = ba_data.layer_businesses
        comp_lyr.definitionQuery = sql

        return comp_lyr

    def _get_data_collection_dir(self):
        """Helper function to retrieve location to find the ba_data collection files"""
        dataset_config_file = os.path.join(self.usa_data_path, 'dataset_config.xml')
        config_tree = ET.parse(dataset_config_file)
        config_root = config_tree.getroot()
        config_dir = config_root.find('./data_collections').text
        return os.path.join(self.usa_data_path, config_dir)

    def _get_out_field_name(self, ge_field_name):
        """Helper function to create field names to look for when trying to enrich from previously enriched ba_data."""
        out_field_name = ge_field_name.replace(".", "_")

        # if string starts with a set of digits, replace them with Fdigits
        out_field_name = re.sub(r"(^\d+)", r"F\1", out_field_name)

        # cut to first 64 characters
        return out_field_name[:64]

    def _get_coll_df(self, coll_file):
        """
        Get a dataframe of fields installed locally with Business Analyst in a single collection.
        :param coll_file: String name of the collection xml file to scan.
        :return: Pandas Dataframe of fields with useful combinations for analysis.
        """
        # crack open the xml file and get started
        coll_tree = ET.parse(os.path.join(self._get_data_collection_dir(), coll_file))
        coll_root = coll_tree.getroot()

        # field list to populate with property tuples
        fld_lst = []

        def _is_hidden(field_ele):
            """Helper to determine if hidden fields."""
            if 'HideInDataBrowser' in field_ele.attrib and field_ele.attrib['HideInDataBrowser'] == 'True':
                return True
            else:
                return False

        # collect any raw scalar fields
        uncalc_ele_fields = coll_root.find('./Calculators/Demographic/Fields')
        if uncalc_ele_fields:
            fld_lst.append([(field_ele.attrib['Name'], field_ele.attrib['Alias'])
                           for field_ele in uncalc_ele_fields.findall('Field')
                            if not _is_hidden(field_ele)])

        # collect any calculated field types
        calc_ele_fields = coll_root.find('./Calculators/Demographic/CalculatedFields')
        if calc_ele_fields:

            # since there are two types of calcualted fields, account for this
            for field_type in ['PercentCalc', 'Script']:
                single_fld_lst = [(field_ele.attrib['Name'], field_ele.attrib['Alias'])
                                  for field_ele in calc_ele_fields.findall(field_type)
                                  if not _is_hidden(field_ele)]
                fld_lst.append(single_fld_lst)

        # combine the results of both uncalculated and calculated fields located into single result
        field_lst = list(itertools.chain.from_iterable(fld_lst))

        if len(field_lst):
            # create a dataframe with the field information
            coll_df = pd.DataFrame(field_lst, columns=['name', 'alias'])

            # using the collected information, create the really valuable fields
            coll_df['collection_name'] = coll_file.split('.')[0]
            coll_df['enrich_str'] = coll_df.apply(lambda row: f"{row['collection_name']}.{row['name']}", axis='columns')
            coll_df['enrich_field_name'] = coll_df['enrich_str'].apply(lambda val: self._get_out_field_name(val))

            return coll_df

        else:
            return None

    def get_enrich_vars_dataframe(self, drop_duplicates:bool=True) -> pd.DataFrame:
        collection_dir = self._get_data_collection_dir()

        # get a complete list of collection files
        coll_xml_lst = [coll_file for coll_file in os.listdir(collection_dir) if coll_file != 'EnrichmentPacksList.xml']

        # get the necessary properties from the collection xml files
        coll_df_lst = [self._get_coll_df(coll_file) for coll_file in coll_xml_lst]
        coll_df = pd.concat([df for df in coll_df_lst if df is not None])

        if drop_duplicates:
            coll_df.drop_duplicates('name', inplace=True)

        coll_df.sort_values('enrich_str')

        coll_df.reset_index(drop=True, inplace=True)

        return coll_df

    @property
    def enrich_vars_dataframe(self) -> pd.DataFrame:
        return self.get_enrich_vars_dataframe()

    @property
    def enrich_vars(self) -> list:
        return list(self.enrich_vars_dataframe['enrich_str'].values)


# create instance of ba_data for use
ba_data = BA_Data()


@property
def to_sdf(self) -> pd.DataFrame:
    # convert the layer to a spatially enabled dataframe
    df = GeoAccessor.from_featureclass(self)

    # get rid of the object id field and return the dataframe
    return df.drop('OBJECTID', axis=1)


# now, monkeypatch this onto the layer object
arcpy._mp.Layer.sdf = to_sdf