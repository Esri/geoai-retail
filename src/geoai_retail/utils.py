from arcgis.features import GeoAccessor, FeatureLayer
from arcgis.geometry import Geometry
from arcgis.gis import GIS
import pandas as pd
import os
import re


def get_dataframe(in_features, gis=None):
    """
    Get a spatially enabled dataframe from the input features provided.
    :param in_features: Spatially Enabled Dataframe | String path to Feature Class | String url to Feature Service
        | String Web GIS Item ID
        Resource to be evaluated and converted to a Spatially Enabled Dataframe.
    :param gis: Optional GIS object instance for connecting to resources.
    """
    # if already a Spatially Enabled Dataframe, mostly just pass it straight through
    if isinstance(in_features, pd.DataFrame) and in_features.spatial.validate() == True:
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

    else:
        raise Exception('Could not process input features for get_dataframe function.')

    # ensure the universal spatial column is correctly being recognized
    df.spatial.set_geometry('SHAPE')

    # index the spatial data for faster subsequnet analyses
    # df.spatial.sindex()

    return df


def add_metric_by_origin_dest(parent_df, join_df, join_metric_fld):
    """
    Add a field to an already exploded origin to multiple destination table. The table must follow the standardized
        schema, which it will if created using the proximity functions in this package.
    :param parent_df: Parent destination dataframe the metric will be added onto.
    :param join_df: Dataframe containing matching origin id's, destination id's, and the metric to be added.
    :param join_metric_fld: The column name containing the metric to be added.
    :return: Dataframe with the data added onto the original origin to multiple destination table.
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

    # initialize the dataframe to iteratively recieve all the data
    combined_df = parent_df

    # for every destination
    for dest_fld in dest_fld_lst:
        # create a label field with the label name with the destination id
        out_metric_fld = f'{join_metric_fld}{dest_fld[-3:]}'

        # join the label field onto the parent dataframe
        combined_df = combined_df.join(join_df_idx[join_metric_fld], on=['origin_id', dest_fld])

        # rename the label column using the named label column with the destination id
        combined_df.columns = [out_metric_fld if col == join_metric_fld else col for col in combined_df.columns]

    return combined_df
