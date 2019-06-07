from sklearn.base import BaseEstimator, TransformerMixin
import numpy as np
import pandas as pd
import arcpy
from arcgis.features import GeoAccessor


class BaseTransformer(BaseEstimator, TransformerMixin):
    """
    Transformer class to save putting the fit method into all the transformers below.
    """
    def fit(self, X, y=None):
        return self


class CalculateMarketPenetration(BaseTransformer):

    def __init__(self, customer_count_field, total_population_field):
        """
        Calculate the market penetration based on a measured metric over a metric to standardize by. This commonly is a
        measured customer count from human movement data plotting home locations. This customer count is then divided by
        a metric to standardize by, typically either total population or household count.
        :param customer_count_field: Field containing the customer count per feature.
        :param total_population_field: Field containing the total population against which the customer count will be
            normalized to calculate the market penetration.
        """
        self.count_field = customer_count_field
        self. total_pop_field = total_population_field

    def transform(self, X, y=None):
        X['market_penetration'] = X[self.count_field] / X[self.total_pop_field]
        mkt_pen_df = X[(X['market_penetration'] != np.inf) & (X['market_penetration'] > 0)].copy()
        return mkt_pen_df


class DemographicFeatureClassToDataframe(BaseTransformer):

    def __init__(self, output_alias_table, demographic_polygon_id_field='ID'):
        """
        Load a polygon feature class enriched from ArcGIS. Since the field names are nearly incomprehensible when the
        analysis is complete, this transformer requires specifying an output location for a CSV output file to save the
        field alias names for use later in interpreting results.
        :param output_alias_table: Output CSV with field names and field aliases for use later when interpreting
            results.
        :param demographic_polygon_id_field: Field with unique identifier to use as the index to tie everything
            together.
        """
        self.alias_table = output_alias_table
        self.id_fld = demographic_polygon_id_field

    def transform(self, X, y=None):

        # first, get and save the alias table for later...because you'll need it
        alias_df = pd.DataFrame([(field.name, field.aliasName) for field in arcpy.ListFields(X)],
                                columns=['name', 'alias'])
        alias_df.to_csv(self.alias_table)

        # next, load up the data into a Spatially Enabled Dataframe
        bg_df = GeoAccessor.from_featureclass(X)

        # since these columns mostly just get in the way, get rid of them
        drop_cols = [col for col in bg_df.columns if col in ['OBJECTID', 'NAME', 'aggregationMethod']]
        bg_df.drop(drop_cols, inplace=True, axis=1)

        # set the index to the id column
        bg_df.set_index(self.id_fld, inplace=True, drop=True)

        return bg_df


class EsriLocatedStoresFeatureClassToDataframe(BaseTransformer):

    def __init__(self, unique_location_id_field='LOCNUM', store_class_field='CONAME'):
        """
        Load the feature class into a Spatially Enabled Data Frame, and purge the fields to just what is useful.
        :param unique_location_id_field: Usually LOCNUM, but if using something different, specify here.
        :param store_class_field: Usually the CONAME field, but if wanting to classify by NAICS, this could be
            different.
        """
        self.store_id_fld = unique_location_id_field
        self.store_class_fld = store_class_field

    def transform(self, X, y=None):
        # load the stores
        store_df = GeoAccessor.from_featureclass(X)

        # distill the fields down to what is useful for analysis
        store_df = store_df[[self.store_id_fld, self.store_class_fld, 'SHAPE']].copy()

        # rename the columns for consistency
        store_df.columns = ['store_id', 'store_class', 'SHAPE']

        # set the index to the store id
        store_df.set_index('store_id', inplace=True, drop=True)

        return store_df


class StoreClassifyByCount(BaseTransformer):

    def __init__(self, store_count_threshold=3):
        """
        Classify stores based on the count in the market being studied based on the count of the store brand. This is
        useful especially in  markets with a large number of one off brands - "mom and pop" stores. The output
        combines all the stores brands containing more than the specified threshold into a mega class OTHER.
        :param store_count_threshold: Number of stores for which if a brand is at or below this number of storefronts,
            will be aggregated into a single OTHER class of stores.
        """
        self.threshold = store_count_threshold

    def transform(self, X, y=None):
        # count column in variable
        count_column = 'class_count'

        # save the original in a new class - possibly useful later for visualization and labeling
        X['store_class_original'] = X['store_class']

        # get a summary of counts by store class - usually the name
        X.reset_index(inplace=True)
        store_count_df = X[['store_class', 'store_id']].groupby('store_class').count()
        store_count_df.columns = [count_column]

        # join the store count to the original data
        store_count_df = X.join(store_count_df, on='store_class')

        # substitute OTHER for all brands at or below the threshold
        store_count_df.loc[store_count_df[count_column] <= self.threshold, 'store_class'] = 'OTHER'

        # filter the fields and reorganize a bit
        store_count_df.set_index('store_id', inplace=True, drop=True)
        return store_count_df[['store_class', 'store_class_original', 'SHAPE']].copy()


class SummarizeInrixTripsByOriginAndDestination(BaseTransformer):
    """
    The trips all start in a location and end in a location. Based on a unique id contained in a field for each,
    summarize the distance, time traveled, and count of trips.
    """

    def __init__(self, origin_id_field='origin_id', destination_id_field='destination_id'):
        """
        :param origin_id_field: Field containing unique identifier for each start location.
        :param destination_id_field: Field containing value uniquely identifying each ending location.
        """
        self.origin_id_fld = origin_id_field
        self.dest_id_fld = destination_id_field

    def transform(self, X, y=None):
        """
        :param X: Trips output with columns for trip distance, trip time, destination id, and origin id.
        :return: Dataframe with two level index of origin_id and destination_id.
        """
        # get a measure of centrality, in this case, the median - may revise later to inner-quartile mean
        trip_center_df = X.groupby([self.origin_id_fld, self.dest_id_fld]).median()

        # get the trip count
        count_column = [col for col in X.columns if col not in [self.origin_id_fld, self.dest_id_fld]][0]
        trip_count_df = X[[self.origin_id_fld, self.dest_id_fld, count_column]].groupby([self.origin_id_fld, self.dest_id_fld]).count()
        trip_count_df.columns = ['trip_count']

        # combine the dataframes for a complete summary table
        trip_stats_df = trip_center_df.join(trip_count_df)
        trip_stats_df.reset_index(inplace=True)

        # if the OBJECTID field is still in there, get rid of it
        if 'OBJECTID' in trip_stats_df.columns:
            trip_stats_df.drop('OBJECTID', inplace=True, axis=1)

        return trip_stats_df


class AddStoresDataframeToTripsDataframe(BaseTransformer):

    def __init__(self, store_dataframe, store_origin_id_field='origin_id', store_destination_id_field='destination_id'):
        """
        Add the store dataframe to the trips dataframe and set the index to both the origin and destination fields.
        :param store_dataframe: Store dataframe.
        :param store_origin_id_field: Origin ID field in the stores dataframe.
        :param store_destination_id_field: Destination ID field in the stores dataframe.
        """
        self.store_df = store_dataframe
        self.origin_id_fld = store_origin_id_field
        self.dest_id_fld = store_destination_id_field

    def transform(self, X, y=None):
        # standardize the origin and destination id fields
        if 'origin_id' not in X.columns:
            X['origin_id'] = X[self.origin_id_fld]
        if 'destination_id' not in X.columns:
            X['destination_id'] = X[self.dest_id_fld]

        # if the store index is numeric and the join field is a string
        if self.store_df.index.is_numeric() and X['destination_id'].apply(type).eq(str).all():

            # convert the join field to the matching numeric type of the index
            X['destination_id'] = X['destination_id'].astype(self.store_df.index.dtype)

        # if the destination is numeric and the store index is a string
        elif not X['destination_id'].apply(type).eq(str).all() and not self.store_df.index.is_numeric():

            # convert the index to the numeric data type of the join field
            self.store_df.index = self.store_df.index.astype(X['destination_id'].dtype)

        # join the data frames together
        join_df = X.join(self.store_df, on=self.dest_id_fld)

        # convert both the origin and destination columns to numeric to avoid issues later
        for fld in [self.origin_id_fld, self.dest_id_fld]:
            join_df[fld] = join_df[fld].astype('int64')

        return join_df


class AddPolygonOriginDataframeToInrixTripSummaryDataframe(BaseTransformer):

    def __init__(self, origin_dataframe, trip_origin_id_field='origin_id'):
        """
        Add the origin polygon dataframe, typically including demographics, to the Inrix origin and destination
        dataframe with trip summary statistics. This is creates highly redundant geometry, but when saved as a feature
        class, makes it very easy to calculate and visualize market penetration.
        :param origin_dataframe: Spatially Enabled Dataframe delineating the origin geographic areas for analysis.
        :param trip_origin_id_field: Field in the trip Dataframe to define the join between the origin dataframe and
            each trip summary.
        """
        self.origin_df = origin_dataframe
        self.trip_origin_id_fld = trip_origin_id_field

    def transform(self, X, y=None):
        # ensure the field to use for the join is of the right data type
        X[self.trip_origin_id_fld] = X[self.trip_origin_id_fld].astype(self.origin_df.index.dtype)

        # join the datafames together
        return X.join(self.origin_df, on=self.trip_origin_id_fld)


class AddBlockGroupDataframeToTripsDataframe(BaseTransformer):

    def __init__(self, block_group_dataframe, block_group_origin_id_field='origin_id',
                 block_group_destination_id_field='destination_id',
                 block_group_measurement_field='market_penetration'):
        """

        :param block_group_dataframe:
        :param block_group_origin_id_field:
        :param block_group_destination_id_field:
        :param block_group_measurement_field:
        """
        self.bg_df = block_group_dataframe
        self.origin_id_fld = block_group_origin_id_field
        self.dest_id_fld = block_group_destination_id_field
        self.measurment_fld = block_group_measurement_field

    def transform(self, X, y=None):
        # standardize the origin and destination id fields
        if 'origin_id' not in X.columns:
            X['origin_id'] = X[self.origin_id_fld]
            X.drop(self.origin_id_fld, inplace=True, axis=1)
        if 'destination_id' not in X.columns:
            X['destination_id'] = X[self.dest_id_fld]
            X.drop(self.dest_id_fld, inplace=True, axis=1)

        # distill the block group dataframe down to the measurement metric
        bg_df = self.bg_df[['origin_id', 'destination_id', self.measurment_fld]].copy()

        # ensure the id fields are numeric to avoid problems later on
        for fld in ['origin_id', 'destination_id']:
            X[fld] = X[fld].astype('int64')
            bg_df[fld] = bg_df[fld].astype('int64')

        # next, set both the dataframes to use the combination of both the origin and destination id fields
        X.set_index(['origin_id', 'destination_id'], inplace=True)
        bg_df.set_index(['origin_id', 'destination_id'], inplace=True)

        # finally, join the dataframes together
        join_df = X.join(bg_df)

        # flatten the index into columns
        join_df.reset_index(inplace=True)

        return join_df


class CalculateOriginProximityMetricsByStoreClass(BaseTransformer):
    """
    Create a dataframe of destination locations with associated proximity metrics pivoted into discrete columns
    so there is only one record for each origin id.
    :param proximity_metric_fields: Fields with proximity metrics to be exploded into discrete columns by location.
    :param proximity_sort_field: Of the proximity fields, which one to use for sorting to determine the top locations.
    :param count_threshold: Number of store locations to consider for each brand - defaults to three (3)
    """

    def __init__(self, proximity_metric_fields, proximity_sort_field, measurement_metric_field,
                 count_threshold=3):
        self.proximity_metric_fields = proximity_metric_fields
        self.proximity_sort_field = proximity_sort_field
        self.measurement_metric_field = measurement_metric_field
        self.count_threshold = count_threshold

    @staticmethod
    def cleanup_column_name(column_name):
        column_name = (''.join(c for c in column_name if c.isalnum() or c == '_' or c == ' '))
        return column_name.replace(' ', '_')

    def get_single_origin_class_df(self, X, origin_id, store_class):

        # filter the dataframe based on just the store category (usually the store brand name) and the origin id
        trip_single_cat = X[(X['store_class'] == store_class) & (X['origin_id'] == origin_id)]

        # create a destination id to store class name series for looking up store names by destination id
        store_class_lookup = trip_single_cat[['destination_id', 'store_class']] \
            .drop_duplicates() \
            .set_index('destination_id')['store_class']

        # sort in descending order and only keep the count threshold
        trip_single_cat.sort_values(self.proximity_sort_field)

        # filter the fields to the relevant fields
        field_list = ['origin_id', 'destination_id'] + \
            self.proximity_metric_fields + \
            [self.measurement_metric_field]

        # only keep the three closest locations
        trip_single_cat = trip_single_cat[field_list][:self.count_threshold].copy()

        # pivot the table to get a single row for each origin id, and a new column for each destination id
        single_pvt_df = trip_single_cat.pivot_table(index='origin_id', columns='destination_id')

        # create column names comprised of the metric, store class name, and store class order
        column_lst = []
        for metric_name, destination_id, store_order in zip(single_pvt_df.columns.get_level_values(0),
                                                            single_pvt_df.columns.get_level_values(1),
                                                            single_pvt_df.columns.labels[1]):
            column_name = '{}_{}_{:02d}'.format(metric_name, store_class_lookup[destination_id],
                                                store_order + 1)
            column_lst.append(self.cleanup_column_name(column_name))

        # before applying the column names, get the destination ids
        dest_id_tuple_lst = [('dest_id_{}_{:02d}'.format(store_class_lookup[val], idx + 1), val)
                             for idx, val in enumerate(single_pvt_df.columns.levels[1])]

        # apply the column names
        single_pvt_df.columns = column_lst

        # now, add the destination id columns
        for dest_id_tuple in dest_id_tuple_lst:
            col_name = self.cleanup_column_name(dest_id_tuple[0])
            single_pvt_df[col_name] = dest_id_tuple[1]

        return single_pvt_df

    def get_single_orgin_df(self, X, origin_id):

        # get a dataframe of only the records for this origin id - starting location geographic area
        origin_df = X[X['origin_id'] == origin_id]

        # sort the values and get the top three for each store class
        origin_df = origin_df.sort_values(self.proximity_sort_field, ascending=False)
        focus_origin_df = origin_df.groupby('store_class').head(3)
        focus_origin_df = focus_origin_df.sort_values('store_class')

        # for every combination of store class (usually name) and the origin id, send this subset of data to get a
        # pivoted table of the nearest locations for every origin id
        for idx, (store_class) in enumerate(focus_origin_df['store_class'].unique()):

            # if the first pass, create the output dataframe, otherwise just add the results
            if idx < 1:
                out_df = self.get_single_origin_class_df(X, origin_id, store_class)
            else:
                single_pvt_df = self.get_single_origin_class_df(X, origin_id, store_class)
                assert isinstance(out_df, pd.DataFrame)
                out_df = out_df.join(single_pvt_df.copy())

        return out_df

    def transform(self, X, y=None):

        # iterate unique values of the origin ids and build up the rows
        for idx, origin_id in enumerate(X['origin_id'].unique()):

            if idx < 1:
                final_df = self.get_single_orgin_df(X, origin_id)
            else:
                single_df = self.get_single_orgin_df(X, origin_id)
                assert(isinstance(final_df, pd.DataFrame))
                final_df = pd.concat([final_df, single_df], sort=True)

        return final_df


class AddDemographicsToProximityMetrics(BaseTransformer):
    """
    Add the demogrpahics table back onto the output from calculating proximity metrics.
    :param demographics_dataframe: Dataframe with the geographic origin areas' origin_ids set as the index.
    :param spatial: Whether to return a spatial dataframe - default is True, return spatial dataframe
    :param index_as_string: Whether or not to return the index as a string, which is the default
    """

    def __init__(self, demographics_dataframe, spatial=True, index_as_string=True):
        self.demographics_df = demographics_dataframe
        self.spatial = spatial
        self.idx_str = index_as_string

    @staticmethod
    def int_to_str_id(val, max_len):
        str_val = str(val)
        zero_cnt = max_len - len(str_val)
        zero_str = zero_cnt * '0'
        out_str = f'{zero_str}{str_val}'
        return out_str

    def fit_transform(self, X, y=None):

        # set the index of the demographic dataframe to integer for the join
        self.demographics_df.index = self.demographics_df.index.astype('int64')

        # perform the join
        final_df = self.demographics_df.join(X)

        # if the index needs to be a string (default), convert it back
        if self.idx_str:
            max_len = final_df.index.astype('str').str.len().max()
            final_df.index = [self.int_to_str_id(val, max_len) for val in final_df.index]

        # name the index orgin_id for consistency
        final_df.index.rename('origin_id', inplace=True)

        # if a nonspatial output is desired (default) drop the column with the geometry
        if not self.spatial and 'SHAPE' in final_df.columns:
            final_df.drop('SHAPE', axis=1, inplace=True)

        # otherwise, set the geometry as the shape field
        else:
            final_df.spatial.set_geometry('SHAPE')

        # return the result
        return final_df
