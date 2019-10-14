import importlib
import logging
import math
import os
import re
import warnings

from arcgis.features import GeoAccessor, FeatureLayer
from arcgis.geometry import Geometry
from arcgis.gis import GIS
from arcgis.env import active_gis
import numpy as np
import pandas as pd


def clean_columns(column_list):
    """
    Little helper to clean up column names quickly.
    :param column_list: List of column names.
    :return: List of cleaned up column names.
    """
    def _scrub_col(column):
        no_spc_char = re.sub(r'[^a-zA-Z0-9_\s]', '', column)
        no_spaces = re.sub(r'\s', '_', no_spc_char)
        return re.sub(r'_+', '_', no_spaces)
    return [_scrub_col(col) for col in column_list]


def get_dataframe(in_features, gis=None):
    """
    Get a spatially enabled dataframe from the input features provided.
    :param in_features: Spatially Enabled Dataframe | String path to Feature Class | String url to Feature Service
        | String Web GIS Item ID
        Resource to be evaluated and converted to a Spatially Enabled Dataframe.
    :param gis: Optional GIS object instance for connecting to resources.
    """

    # if already a Spatially Enabled Dataframe, mostly just pass it straight through
    if isinstance(in_features, pd.DataFrame) and in_features.spatial.validate() is True:
        df = in_features

    # if a csv previously exported from a Spatially Enabled Dataframe, get it in
    elif isinstance(in_features, str) and os.path.exists(in_features) and in_features.endswith('.csv'):
        df = pd.read_csv(in_features)
        df['SHAPE'] = df['SHAPE'].apply(lambda geom: Geometry(eval(geom)))

        # this almost always is the index written to the csv, so taking care of this
        if df.columns[0] == 'Unnamed: 0':
            df = df.set_index('Unnamed: 0')
            del (df.index.name)

    # create a Spatially Enabled Dataframe from the direct url to the Feature Service
    elif isinstance(in_features, str) and in_features.startswith('http'):

        # submitted urls can be lacking a few essential pieces, so handle some contingencies with some regex matching
        regex = re.compile(r'((^https?://.*?)(/\d{1,3})?)\?')
        srch = regex.search(in_features)

        # if the layer index is included, still clean by dropping any possible trailing url parameters
        if srch.group(3):
            in_features = f'{srch.group(1)}'

        # ensure at least the first layer is being referenced if the index was forgotten
        else:
            in_features = f'{srch.group(2)}/0'

            # if the layer is unsecured, a gis is not needed, but we have to handle differently
        if gis is not None:
            df = FeatureLayer(in_features, gis).query(out_sr=4326, as_df=True)
        else:
            df = FeatureLayer(in_features).query(out_sr=4326, as_df=True)

    # create a Spatially Enabled Dataframe from a Web GIS Item ID
    elif isinstance(in_features, str) and len(in_features) == 32:

        # if publicly shared on ArcGIS Online this anonymous gis can be used to access the resource
        if gis is None:
            gis = GIS()
        itm = gis.content.get(in_features)
        df = itm.layers[0].query(out_sr=4326, as_df=True)

    # create a Spatially Enabled Dataframe from a local feature class
    elif isinstance(in_features, str):
        df = GeoAccessor.from_featureclass(in_features)

    # sometimes there is an issue with modified or sliced dataframes with the SHAPE column not being correctly
    #    recognized as a geometry column, so try to set it as the geometry...just in case
    elif isinstance(in_features, pd.DataFrame) and 'SHAPE' in in_features.columns:
        in_features.spatial.set_geometry('SHAPE')
        df = in_features

        if df.spatial.validate() is False:
            raise Exception('Could not process input features for get_dataframe function. Although the input_features '
                            'appear to be in a Pandas Dataframe, the SHAPE column appears to not contain valid '
                            'geometries. The Dataframe is not validating using the *.spatial.validate function.')

    else:
        raise Exception('Could not process input features for get_dataframe function.')

    # ensure the universal spatial column is correctly being recognized
    df.spatial.set_geometry('SHAPE')

    return df


def add_metric_by_origin_dest(parent_df, join_df, join_metric_fld, fill_na_value=None):
    """
    Add a field to an already exploded origin to multiple destination table. The table must follow the standardized
        schema, which it will if created using the proximity functions in this package.
    :param parent_df: Parent destination dataframe the metric will be added onto.
    :param join_df: Dataframe containing matching origin id's, destination id's, and the metric to be added.
    :param join_metric_fld: The column containing the metric to be added.
    :param fill_na_value: Optional - String or integer to fill null values with. If not used, null values will not be
        filled.
    :return: Dataframe with the ba_data added onto the original origin to multiple destination table.
    """
    # ensure everything is matching field types so the joins will work
    origin_dtype = parent_df['origin_id'].dtype
    dest_dtype = parent_df['destination_id_01'].dtype
    join_df['origin_id'] = join_df['origin_id'].astype(origin_dtype)
    join_df['destination_id'] = join_df['destination_id'].astype(dest_dtype)

    # for the table being joined to the parent, set a multi-index for the join
    join_df_idx = join_df.set_index(['origin_id', 'destination_id'])

    # get the number of destinations being used
    dest_fld_lst = [col for col in parent_df.columns if col.startswith('destination_id_')]

    # initialize the dataframe to iteratively receive all the ba_data
    combined_df = parent_df

    # for every destination
    for dest_fld in dest_fld_lst:
        # create a label field with the label name with the destination id
        out_metric_fld = f'{join_metric_fld}{dest_fld[-3:]}'

        # join the label field onto the parent dataframe
        combined_df = combined_df.join(join_df_idx[join_metric_fld], on=['origin_id', dest_fld])

        # rename the label column using the named label column with the destination id
        combined_df.columns = [out_metric_fld if col == join_metric_fld else col for col in combined_df.columns]

        # if filling the null values, do it
        if fill_na_value is not None:
            combined_df[out_metric_fld].fillna(fill_na_value, inplace=True)

    return combined_df


def add_metric_by_dest(parent_df, join_df, join_id_fld, join_metric_fld, get_dummies=False, fill_na_value=None):
    """
    Add a field to an already exploded origin to multiple destination table. The table must follow the standardized
        schema, which it will if created using the proximity functions in this package.
    :param parent_df: Parent destination dataframe the metric will be added onto.
    :param join_df: Dataframe containing matching destination_id's, and the metric to be added.
    :param join_id_fld: Field to use for joining to the origin_id in the parent_df
    :param join_metric_fld: The column containing the metric to be added.
    :param get_dummies: Optional - Boolean indicating if make dummies should be run to explode out categorical values.
    :param fill_na_value: Optional - String or integer to fill null values with. If not used, null values will not be
        filled.
    :return: Dataframe with the ba_data added onto the original origin to multiple destination table.
    """
    # ensure everything is matching field types so the joins will work
    if parent_df['origin_id'].dtype == 'O':
        convert_dtype = str
    else:
        convert_dtype = parent_df['origin_id'].dtype
    join_df[join_id_fld] = join_df[join_id_fld].astype(convert_dtype)

    # for the table being joined to the parent set the index for the join
    join_df_idx = join_df.set_index(join_id_fld)

    # get the number of destinations being used
    dest_fld_lst = [col for col in parent_df.columns if col.startswith('destination_id_')]

    # initialize the dataframe to iteratively receive all the ba_data
    combined_df = parent_df

    # for every destination
    for dest_fld in dest_fld_lst:

        # create a label field with the label name with the destination id
        out_metric_fld = f'{join_metric_fld}{dest_fld[-3:]}'

        # join the label field onto the parent dataframe
        combined_df = combined_df.join(join_df_idx[join_metric_fld], on=dest_fld)

        # rename the label column using the named label column with the destination id
        combined_df.columns = [out_metric_fld if col == join_metric_fld else col for col in combined_df.columns]

        # if filling the null values, do it
        if fill_na_value is not None:
            combined_df[out_metric_fld].fillna(fill_na_value, inplace=True)

        # if get dummies...well, do it dummy!
        if get_dummies:
            combined_df = pd.get_dummies(combined_df, columns=[out_metric_fld])

    # if dummies were created, clean up column names
    if get_dummies:
        combined_df.columns = clean_columns(combined_df.columns)

    return combined_df


def add_normalized_columns_to_closest_dataframe(closest_df, closest_factor_fld_root, normalize_df, normalize_id_fld,
                                                normalize_fld, output_normalize_field_name, fill_na=None,
                                                drop_original_columns=False):
    """
    Normalize metrics in a dataframe by a demographic value for each geography - typically either total households or
        total population
    :param closest_df: Dataframe formatted from closest analysis with multiple destination locations.
    :param closest_factor_fld_root: The field room pattern to be normalized - the part of the name prefixing the _01
        numbering scheme.
    :param normalize_df: The dataframe containing the ba_data to be used in normalizing the metric.
    :param normalize_id_fld: The field in the dataframe with a geographic identifier able to be used to join the ba_data
        together.
    :param normalize_fld: The field with values to be used as the denominator when normalizing the ba_data.
    :param output_normalize_field_name: Field name to be used for the normalized output fields.
    :param fill_na: Optional - If the normalized fields are null, the value to fill in.
    :param drop_original_columns: Boolean - whether or not to drop the original columns.
    :return:
    """
    # get the ba_data type the normalize join field needs to be
    if closest_df['origin_id'].dtype == 'O':
        convert_dtype = str
    else:
        convert_dtype = closest_df['origin_id'].dtype

    # convert the normalize join field to this ba_data type, make this the index, and extract this single series out
    normalize_df[normalize_id_fld] = normalize_df[normalize_id_fld].astype(convert_dtype)
    normalize_df = normalize_df.set_index(normalize_id_fld)
    normalize_srs = normalize_df[normalize_fld]

    # join this series to the closest dataframe
    normalize_df = closest_df.join(normalize_srs, on='origin_id')

    # get a list of the fields we are going to normalize
    gross_factor_fld_lst = [col for col in normalize_df.columns if col.startswith(closest_factor_fld_root)]

    # for every field we are going to normalize, add a new normalized field
    for gross_fld in gross_factor_fld_lst:
        normalized_fld = gross_fld.replace(closest_factor_fld_root, output_normalize_field_name)
        normalize_df[normalized_fld] = normalize_df[gross_fld] / normalize_df[normalize_fld]

        # if a fill null value is provided, use it
        if fill_na is not None:
            normalize_df[normalized_fld].fillna(fill_na, inplace=True)

        # if the numerator is a value and the denominator is zero, the product is inf; we need zero
        normalize_df[normalized_fld] = normalize_df[normalized_fld].apply(
            lambda val: 0 if val == np.inf or val == -np.inf else val)

    # if we want to drop the columns, get rid of them
    if drop_original_columns:
        normalize_df.drop(columns=gross_factor_fld_lst, inplace=True)

    # we do not need the values we normalized by, so drop them
    normalize_df.drop(columns=normalize_fld, inplace=True)

    return normalize_df


def add_store_name_category(df, store_name_column, location_count_threshold=1):
    """
    Add and calculate a store name column based on the count of the location name. This enables comparing a store
        brand recognition to the independent mom and pop locations for brand recognition, or avoidance to independents.
    :param df: Data frame with a column identifying the location brand or store name.
    :param store_name_column: Column in the dataframe containing the store names.
    :param location_count_threshold: Optional - Integer representing the store counts - default 1
    :return: Updated dataframe with a new column indicating the store name category including independent if the count
        of locations is at or below the location count threshold.
    """
    brand_name_cnt = df.groupby(store_name_column).count().ix[:, 0].sort_values(ascending=False).to_frame()
    brand_name_cnt.columns = ['count']
    brand_name_cnt.reset_index(inplace=True)

    brand_name_cnt['dest_name_category'] = brand_name_cnt.apply(
        lambda r: 'INDEPENDENT' if r['count'] <= location_count_threshold else r[store_name_column], axis=1)
    brand_name_cnt.set_index(store_name_column, inplace=True, drop=True)

    return df.join(brand_name_cnt['dest_name_category'], on=store_name_column)


class Environment:

    def __init__(self, gis=None):
        self.gis = self._check_gis(gis)
        self._installed_lst = []
        self._not_installed_lst = []
        self._arcpy_extensions = []

    def _check_gis(self, gis):
        if gis is None and active_gis is not None:
            return active_gis
        elif gis is None:
            return None
        elif isinstance(gis, GIS):
            return gis
        else:
            raise Exception('If passing in a GIS object instance, it must be a valid arcgis.gis.GIS object instance.')

    def has_package(self, package_name):
        if package_name in self._installed_lst:
            return True
        elif package_name in self._not_installed_lst:
            return False
        else:
            installed = True if importlib.util.find_spec(package_name) else False
            if installed:
                self._installed_lst.append(package_name)
            else:
                self._not_installed_lst.append(package_name)
        return installed

    @property
    def arcpy_extensions(self):
        if len(self._arcpy_extensions) > 0:
            return self._arcpy_extensions
        elif not self.has_package('arcpy'):
            warnings.warn('ArcPy is not available in your current environment.')
            return self._arcpy_extensions
        else:
            extension_lst = ['3D', 'Datareviewer', 'DataInteroperability', 'Airports', 'Aeronautical', 'Bathymetry',
                             'Nautical', 'GeoStats', 'Network', 'Spatial', 'Schematics', 'Tracking', 'JTX', 'ArcScan',
                             'Business', 'Defense', 'Foundation' ,'Highways', 'StreetMap']

            import arcpy
            for extension in extension_lst:
                if arcpy.CheckExtension(extension):
                    self._arcpy_extensions.append(extension)
            return self._arcpy_extensions

    def arcpy_checkout_extension(self, extension):
        if self.has_package('arcpy') and extension in self.arcpy_extensions:
            import arcpy
            arcpy.CheckOutExtension(extension)
            return True
        else:
            raise Exception(f'Cannot check out {extension}. It either is not licensed, not installed, or you are not '
                            f'using the correct reference.')


def get_logger(loglevel:str='WARNING', logfile:str=None) -> logging.Logger:
    """
    Make logging much easier by outputting directly to console and local logfile.
    :param loglevel: 'CRITICAL' | 'ERROR' | 'WARNING' | 'INFO' | 'DEBUG' - default 'WARNING'
    :param logfile: Optional path to where to save logfile.
    :return: Path to saved logfile.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(loglevel)

    c_handler = logging.StreamHandler()
    if logfile is None:
        f_handler = logging.FileHandler(f'{__name__}_logfile.log')
    else:
        f_handler = logging.FileHandler(logfile)

    for handler in [c_handler, f_handler]:
        handler.setLevel('DEBUG')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    return logger


def blow_chunks(iterable:iter, chunk_size:int) -> list:
    """
    Make it easier to chunk an iterable, typically a list, into a list containing sublists for processing.
    :param iterable: Any iterable of objects needing to be subdivided.
    :param chunk_size: Size of sublists to create.
    :return: List original objects in sublists defined by the size of the sublist.
    """
    return [iterable[i * chunk_size: (i + 1) * chunk_size] for i in range(math.ceil(len(iterable)/chunk_size))]
