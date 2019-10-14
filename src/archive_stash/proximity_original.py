import arcpy
import os
import pandas as pd
from arcgis.features import GeoAccessor
import uuid
from datetime import datetime
import calendar

arcpy.env.overwriteOutput = True


# utility function to increment datetime by one month
def add_one_month(orig_date):
    # advance year and month by one month
    new_year = orig_date.year
    new_month = orig_date.month + 1
    # note: in datetime.date, months go from 1 to 12
    if new_month > 12:
        new_year += 1
        new_month -= 12

    last_day_of_month = calendar.monthrange(new_year, new_month)[1]
    new_day = min(orig_date.day, last_day_of_month)

    return orig_date.replace(year=new_year, month=new_month, day=new_day)

# help the layer to be at least a little self aware...
@property
def get_count(self):
    return int(arcpy.management.GetCount(self)[0])
arcpy._mp.Layer.count = get_count


def get_max_near_dist(stores_layer):
    """
    Get the maximum geodesic distance between stores.
    """
    # create a location for temporary ba_data
    temp_table = r'in_memory\near_table_{}'.format(uuid.uuid4().hex)

    # if only one location, cannot generate a near table, and default to 120 miles
    if int(arcpy.management.GetCount(stores_layer)[0]) <= 1:
        max_near_dist = 120 * 1609.34

    else:
        # use arcpy to get a table of all distances between stores
        near_tbl = arcpy.analysis.GenerateNearTable(
            in_features=stores_layer,
            near_features=stores_layer,
            out_table=temp_table,
            method="GEODESIC"
        )[0]

        # get the maximum near distance, which will be in meters
        meters = max([row[0] for row in arcpy.da.SearchCursor(near_tbl, 'NEAR_DIST')])

        # remove the temporty table to ensure not stuff lying around and consuming RAM
        arcpy.management.Delete(temp_table)

        # get the maximum near distance (in meters)
        max_near_dist = meters * 0.00062137

    return max_near_dist


def get_store_open_date_list(target_lyr, target_open_date_fld):
    """
    Get a list of open dates for the stores.
    :param target_lyr: Feature layer of stores.
    :param target_open_date_fld: Open date for each store.
    :return: List of open dates.
    """
    open_dt_lst = list(set(r[0] for r in arcpy.da.SearchCursor(target_lyr, target_open_date_fld)))
    open_dt_lst.sort()
    return open_dt_lst


def get_store_open_year_month_list(target_lyr, target_open_date_field):
    """
    For doing analysis by open month, get a list of unique year and month tuples of the open dates.
    :param target_lyr: Feature layer of stores.
    :param target_open_date_field: Open date for each store.
    :return: List of tuples comprised of integer year and integer month with store openings.
    """
    open_dt_lst = get_store_open_date_list(target_lyr, target_open_date_field)
    open_ym_lst = list(set((dt.year, dt.month) for dt in open_dt_lst))
    open_ym_lst.sort()
    return open_ym_lst


def get_centroid_local(origin_areas_fc, origin_areas_id_fld, centroid_weighting_fc=None):
    """
    Calculate the centroids for origin polygons, optionally using a weighting feature class.
    :param origin_areas_fc: Feature Layer or String path to feature class
        Feature layer or path to feature class for geographies used as origins for analysis.
    :param origin_areas_id_fld: String
        String field name containing unique identifier for contributing geographic areas.
    :param centroid_weighting_fc: String path to point feature class
        Path to point feature class to be used to weight centroid calculation for routing points. Typicaly this will be
        a block point centroid feature class.
    :return: Feature layer with centroid points.
    """
    # get the geometry type of the origin_areas_feature class, typically a polygon
    areas_geom = arcpy.Describe(origin_areas_fc).shapeType

    # if the geometry is not a point or multipoint and a centroid weighting feature class is not provided
    if not (areas_geom == 'Point' or areas_geom == 'Multipoint') and not centroid_weighting_fc:

        # get the centroid geometry
        geog_fc = arcpy.management.FeatureToPoint(
            origin_areas_fc,
            os.path.join(arcpy.env.scratchGDB, 'temp_geog_{}'.format(uuid.uuid4().hex)),
            'INSIDE'
        )[0]

        # make a layer to work with
        origin_lyr = arcpy.management.MakeFeatureLayer(geog_fc)[0]

    # if the geometry is not a point or multipoint, and a centroid weighting feature class is provided
    elif not (areas_geom == 'Point' or areas_geom == 'Multipoint') and centroid_weighting_fc:

        # ensure the geometry type is a point, and if not, make it points
        weighting_geom = arcpy.Describe(centroid_weighting_fc).shapeType
        if weighting_geom != 'Point':
            weighting_fc = arcpy.management.FeatureToPoint(centroid_weighting_fc, 'in_memory/weighting_points')[0]

        # get the area ids on the weighting feature class points
        areas_id_fc = arcpy.analysis.Identity(weighting_fc, origin_areas_fc, 'in_memory/temp_points')[0]

        # calculate the weighted center for the centroid feature class
        origin_lyr = arcpy.stats.MeanCenter(areas_id_fc, 'in_memory/temp_centroids', Case_Field=origin_areas_id_fld)[0]

        # otherwise, if points, simply create the feature layer
    else:
        origin_lyr = arcpy.management.MakeFeatureLayer(origin_areas_fc)[0]

    return origin_lyr


def solve_closest_local(network_dataset, target_fc, target_id_fld, origin_areas_fc, origin_areas_id_fld,
                        destination_count=1, maximum_near_distance=False, centroid_weighting_fc=None):
    """
    Solve for nearest store location(s) to contributing geographies, typically census areas.
    :param network_dataset: String path to ArcGIS Network Dataset
        Path to ArcGIS Network dataset to perform routing against.
    :param target_fc: Feature Layer or String path to feature class
        Feature layer or path to feature class containing stores to be used as destinations.
    :param target_id_fld: String
        String field name containing unique identifier for each store location.
    :param origin_areas_fc: Feature Layer or String path to feature class
        Feature layer or path to feature class for geographies used as origins for analysis.
    :param origin_areas_id_fld: String
        String field name containing unique identifier for contributing geographic areas.
    :param destination_count: Integer - optional - default 1
        Number of destinations to find describing the
    :param maximum_near_distance: Boolean - optional - default None
        Whether or not to use the maximum near distance between stores to constrain the analysis area to speed up
        processing. This typically is not used on the first iteration when solving for store networks spanning
        a time series of open dates, but rather is used after the first run for revising the dataset on subsequent runs.
    :param centroid_weighting_fc: String path to point feature class
        Path to point feature class to be used to weight centroid calculation for routing points. Typicaly this will be
        a block point centroid feature class.
    :return: String
        Path to solved routes Feature Class.
    """

    # get the geometry type of the origin_areas_feature class, typically a polygon
    areas_geom = arcpy.Describe(origin_areas_fc).shapeType

    # if the geometry is not a point or multipoint and a centroid weighting feature class is not provided
    if not (areas_geom == 'Point' or areas_geom == 'Multipoint') and not centroid_weighting_fc:

        # get the centroid geometry
        geog_fc = arcpy.management.FeatureToPoint(
                origin_areas_fc,
                os.path.join(arcpy.env.scratchGDB, 'temp_geog_{}'.format(uuid.uuid4().hex)),
                'INSIDE'
        )[0]

        # make a layer to work with
        geog_lyr = arcpy.management.MakeFeatureLayer(geog_fc)[0]

    # if the geometry is not a point or multipoint, and a centroid weighting feature class is provided
    elif not (areas_geom == 'Point' or areas_geom == 'Multipoint') and centroid_weighting_fc:

        # ensure the geometry type is a point, and if not, make it points
        weighting_geom = arcpy.Describe(centroid_weighting_fc).shapeType
        if weighting_geom != 'Point':
            weighting_fc = arcpy.management.FeatureToPoint(centroid_weighting_fc, 'in_memory/weighting_points')[0]

        # get the area ids on the weighting feature class points
        areas_id_fc = arcpy.analysis.Identity(weighting_fc, origin_areas_fc, 'in_memory/temp_points')[0]

        # calculate the weighted center for the centroid feature class
        geog_lyr = arcpy.stats.MeanCenter(areas_id_fc, 'in_memory/temp_centroids', Case_Field=origin_areas_id_fld)[0]

    # otherwise, if points, simply create the feature layer
    else:
        geog_lyr = arcpy.management.MakeFeatureLayer(origin_areas_fc)[0]

    # if the maximum near distance is desired
    if maximum_near_distance:

        # get the maximum near distance
        max_dist = get_max_near_dist(target_fc)

        # create the network analysis layer
        na_lyr = arcpy.na.MakeClosestFacilityAnalysisLayer(
                network_data_source=network_dataset,
                layer_name=None,
                travel_mode="Driving Distance",
                travel_direction="TO_FACILITIES",
                cutoff=max_dist,
                number_of_facilities_to_find=destination_count,
                line_shape="NO_LINES",
                accumulate_attributes="Miles;TravelTime"
        )[0]

        # select the contributing geographies only within the search distance to speed up add locations
        arcpy.management.SelectLayerByLocation(
            in_layer=geog_lyr,
            overlap_type='WITHIN_A_DISTANCE',
            select_features=target_fc,
            search_distance='{} miles'.format(max_dist)
        )

    # if no max near dist
    else:

        # create the network analysis layer
        na_lyr = arcpy.na.MakeClosestFacilityAnalysisLayer(
            network_data_source=network_dataset,
            layer_name=None,
            travel_mode="Driving Distance",
            travel_direction="TO_FACILITIES",
            number_of_facilities_to_find=destination_count,
            line_shape="NO_LINES",
            accumulate_attributes="Miles;TravelTime"
        )[0]

        # ensure nothing is selected in the contributing areas
        arcpy.SelectLayerByAttribute_management(geog_lyr, "CLEAR_SELECTION")

    # get a dictionary of all the layer resource names
    na_lyr_dict = arcpy.na.GetNAClassNames(na_lyr)

    # add the stores as destinations to the analysis layer
    arcpy.na.AddLocations(
            in_network_analysis_layer=na_lyr,
            sub_layer=na_lyr_dict['Facilities'],
            in_table=target_fc,
            field_mappings="Name {} #;".format(target_id_fld),
            search_tolerance="5000 Meters",
            match_type="MATCH_TO_CLOSEST",
            append=False
    )

    # now, add area centroids to the analysis layer
    arcpy.na.AddLocations(
        in_network_analysis_layer=na_lyr,
        sub_layer=na_lyr_dict['Incidents'],
        in_table=geog_lyr,
        field_mappings="Name {} #;".format(origin_areas_id_fld),
        search_tolerance="5000 Meters",
        match_type="MATCH_TO_CLOSEST",
        append=False
    )

    # run the solve, and get comfortable
    arcpy.na.Solve(na_lyr)

    # return the routes path
    return arcpy.Describe(na_lyr_dict['CFRoutes']).catalogPath

        
def get_area_id_for_target_points(target_fc, area_fc, area_id_fld, target_id_fld, return_data_frame=False):
    """
    Get the containing area ID for the target points.
    :param target_fc:
    :param area_fc: 
    :param area_id_fld: 
    :param target_id_fld: 
    :param return_data_frame: 
    :return: 
    """
    # run intersect to get the containing geographic area id for every store point
    fc_name = 'target_intersect_{}'.format(uuid.uuid4().hex)
    stores_with_geog = arcpy.analysis.Intersect([target_fc, area_fc], os.path.join(arcpy.env.scratchGDB, fc_name))

    # use a dataframe to clean up the output tabular ba_data
    stores_geog_df = GeoAccessor.from_featureclass(stores_with_geog)
    stores_geog_df = stores_geog_df[[target_id_fld, area_id_fld, 'SHAPE']].copy()
    stores_geog_df.columns = ['target_id', 'area_target_id', 'SHAPE']

    # return results in desired format
    if return_data_frame:
        return stores_geog_df
    else:
        fc_name = 'target_w_area_id_{}'.format(uuid.uuid4().hex)
        return stores_geog_df.spatial.to_featureclass(os.path.join(arcpy.env.scratchGDB, fc_name))


def get_nearest_dataframe(network_dataset, target_fc, target_id_fld, area_fc, area_id_fld, destination_count=1,
                          max_near_dist=True, centroid_weighting_fc=None):

    # create a network route features
    routes_feature_layer = solve_closest_local(
        network_dataset=network_dataset,
        target_fc=target_fc,
        target_id_fld=target_id_fld,
        origin_areas_fc=area_fc,
        origin_areas_id_fld=area_id_fld,
        maximum_near_distance=max_near_dist,
        centroid_weighting_fc=centroid_weighting_fc
    )

    # if more than one destination was specified
    if destination_count > 1:

        # get the ba_data frame with facility rank from the route solution
        df_raw = pd.DataFrame(
            data=[r for r in arcpy.da.SearchCursor(
                routes_feature_layer,
                ['FacilityRank', 'Name', 'Total_TravelTime', 'Total_Miles']
            )],
            columns=['rank', 'name', 'proximity_time', 'proximity_miles']
        )

        # create a contributing and target geograhic id field from the name
        id_pairs = df_raw['name'].str.split('-')
        df_raw['area_contrib_id'] = id_pairs.apply(lambda v: v[0].strip().replace('Location ', ''))
        df_raw['area_target_id'] = id_pairs.apply(lambda v: v[1].strip().replace('Location ', ''))

        # zero out the distance and time if the geographic id is the same
        df_raw['proximity_time'] = df_raw.apply(lambda r: 0 if r[4] == r[5] else r[2], axis=1)
        df_raw['proximity_miles'] = df_raw.apply(lambda r: 0 if r[4] == r[5] else r[3], axis=1)

        # save variable names to use for organizing ba_data
        row_lst = ['proximity_time', 'proximity_miles', 'area_target_id']
        unique_col = 'rank'
        index_col = 'area_contrib_id'

        # # start creating the output dataframe with the unique value s
        df = pd.DataFrame(df_raw[index_col].unique(), columns=[index_col])

        # iterate all the unique values in the column to expand
        for unique_val in df_raw[unique_col].unique():

            # filter the dataframe to only the values we are going to work with
            df_filtered = df_raw[df_raw[unique_col] == unique_val]

            # create a temporary dataframe to begin building
            df_temp = df_filtered[index_col].to_frame()

            for row in row_lst:
                # create a new column name from the unique value and the original row name
                new_name = "{}_{}".format(row, unique_val)

                # filter the ba_data in the column with the unique value
                df_temp[new_name] = df_filtered[row].values

            # set the index to the geographic contributing id for joining
            df_temp.set_index(index_col, inplace=True)

            # join the temporary dataframe to the master
            df = df.join(df_temp, on=index_col)

    # if only one target destination
    else:

        # create a dataframe from just the columns we want to work with - not a Spatially Enabled Data Frame
        df = pd.DataFrame(
            data=[r for r in arcpy.da.SearchCursor(
                routes_feature_layer,
                ['Name', 'Total_TravelTime', 'Total_Miles']
            )],
            columns=['name', 'proximity_time', 'proximity_miles']
        )

        # create a contributing and target geographic id field from the name
        id_pairs = df['name'].str.split('-')
        df['area_contrib_id'] = id_pairs.apply(lambda v: v[0].strip().replace('Location ', ''))
        df['target_id'] = id_pairs.apply(lambda v: v[1].strip().replace('Location ', ''))

        # zero out the distance and time if the geographic id is the same
        df['proximity_time'] = df.apply(lambda r: 0 if r[3] == r[4] else r[1], axis=1)
        df['proximity_miles'] = df.apply(lambda r: 0 if r[3] == r[4] else r[2], axis=1)

        # drop the now unneeded name column
        df.drop('name', axis=1, inplace=True)

    return df


def rebalance_near_solution(open_datetime, network_dataset, previous_solve_df, target_fc,  target_id_fld,
                            target_open_date_fld, area_fc, area_id_fld, centroid_weighting_fc=None):

    # create a layer of stores open up to this date to use for calculating the maximum near distance
    # calculate the maximum distance between target locations to use for defining the analysis area around targets
    stores_open_to_date_query = f'{target_open_date_fld} <= {open_datetime}'
    stores_open_to_date_lyr = arcpy.management.MakeFeatureLayer(target_fc, stores_open_to_date_query)[0]
    max_near_dist = get_max_near_dist(stores_open_to_date_lyr)

    # create a layer of only the stores opening on the input open datetime month
    open_dt = pd.to_datetime(open_datetime)
    start_dt_str = open_dt.strftime('%Y-%m-%d')
    end_dt_str = add_one_month(open_dt).strftime('%Y-%m-%d')
    target_open_query = f'{target_open_date_fld} >= timestamp {start_dt_str} AND  \
                          {target_open_date_fld} <= timestamp {end_dt_str}'
    target_open_lyr = arcpy.management.MakeFeatureLayer(target_fc, target_open_query)[0]

    # use the stores opening on the input date to identify the areas needing to be considered based on the maximum
    # distance between targets to select the contributing areas surrounding the newly opened target locations
    current_area_lyr = arcpy.management.MakeFeatureLayer(area_fc)[0]
    arcpy.management.SelectLayerByLocation(current_area_lyr, 'WITHIN_A_DISTANCE_GEODESIC', target_open_lyr,
                                           f'{max_near_dist} miles')
    current_area_lyr = arcpy.management.CopyFeatures(current_area_lyr, f'in_memory/current_area_{uuid.uuid4().hex}')

    # get the target id's (if any) these contributing areas previously were allocated to
    current_area_id_lst = [r[0] for r in arcpy.da.SearchCursor(current_area_lyr, area_id_fld)]
    filtered_previous_solve_df = previous_solve_df[previous_solve_df['target_id'].isin(current_area_id_lst)]

    # from this filtered dataframe, get the stores previously participating in the analysis area
    previous_target_id_lst = list(filtered_previous_solve_df['target_id'].values)

    # now, create a layer of the previous target id's and the currently opening target id's
    open_target_id_lst = [r[0] for r in arcpy.da.SearchCursor(target_open_lyr, target_id_fld)]
    current_target_id_lst = previous_target_id_lst + open_target_id_lst
    current_target_id_query_lst = [f"{target_id_fld} = '{target_id}'" for target_id in current_target_id_lst]
    current_target_query = ' OR '.join(current_target_id_query_lst)
    current_target_lyr = arcpy.management.MakeFeatureLayer(target_fc, where_clause=current_target_query)[0]

    # add the area id's to the targets
    target_w_area_id = get_area_id_for_target_points(current_area_lyr, current_target_lyr, area_id_fld, target_id_fld)

    # create a dataframe of areas ids and target ids with distance metrics
    near_df = get_nearest_dataframe(
        network_dataset=network_dataset,
        target_fc=target_w_area_id,
        target_id_fld='target_id',
        area_fc=area_fc,
        area_id_fld=area_id_fld,
        destination_count=1,
        max_near_dist=True,
        centroid_weighting_fc=centroid_weighting_fc
    )

    # filter out the previous solve dataframe to exclude the updated origin areas
    unaffected_df = previous_solve_df[~previous_solve_df['area_contrib_id'].isin(near_df['area_contrib_id'])]

    # concatenate the unaffected and the new solve dataframe, and clean up the index
    current_solve_df = pd.concat([near_df, unaffected_df], sort=False)
    current_solve_df.reset_index(inplace=True, drop=True)

    return current_solve_df


def nearest_generator(target_lyr, target_open_date_fld, target_id_fld, area_lyr, area_id_fld, network_dataset,
                      use_entire_extent=True, centroid_weighting_fc=None):
    """
    Iteratively walk through the years by month and rebalance the contributing geography nearest solution every time
    the store count changes.
    :param target_lyr: String - required
        Path to the feature class containing the target locations (stores) for the nearest solution.
    :param target_open_date_fld: String - required
        Datetime field containing the open date.
    :param target_id_fld: String - required
        Field with the unique identifier for each target location.
    :param area_lyr: String path to ArcGIS Feature class - required
        Geographic layer with contributing areas - typically zip codes, block groups, etc.
    :param area_id_fld: String - required
        Name of field with unique ID for each geographic contributing area.
    :param network_dataset: String - required
        Path to an ArcGIS Network Dataset.
    :param use_entire_extent: Boolean - optional - default True
        Compute the entire extent of the input geographic areas. If false, will only include geographic areas within
        the distance equal to the furthest distance between stores.
    :param centroid_weighting_fc: String path to point feature class - optional - default None
        Path to a point feature class to weight the polygon centroids when creating the origin for the routes.
    :return:
    """
    # add the target area ids to the target feature class
    target_df_w_area_id = get_area_id_for_target_points(target_lyr, area_lyr, area_id_fld, target_id_fld, True)

    # create a dataframe from the target (stores) features, and add the area ids
    target_df = GeoAccessor.from_featureclass(target_lyr)
    target_df = target_df.join(target_df_w_area_id[['target_id', 'area_target_id']].set_index('target_id'),
                               on=target_id_fld)

    # set the open dates to the first of the month since only considering the month
    target_df[target_open_date_fld] = [datetime(dt.year, dt.month, 1) for dt in
                                       pd.DatetimeIndex(target_df[target_open_date_fld])]

    # get a list of unique open dates (by month and year) for processing
    open_dt_lst = target_df[target_open_date_fld].unique()
    open_dt_lst.sort()

    # the only way I could figure out to extract the year and month
    def get_dtidx(open_dt):
        dtidx = pd.DatetimeIndex([open_dt])
        return dtidx.year[0], dtidx.month[0]

    # if the first run, do not need to worry about difference between past and current stores
    open_dt = open_dt_lst[0]

    # get the year and month from the datetime
    year, month = get_dtidx(open_dt)

    print('{} Starting routing... {} {:02d}'.format(datetime.now().isoformat(), year, month))

    # filter the target_df to get only the target ids for analysis
    current_df = target_df[target_df[target_open_date_fld] <= open_dt]
    current_id_lst = current_df[target_id_fld]

    # create a layer with just the current stores
    query = ' OR '.join(["{} = '{}'".format(target_id_fld, val) for val in current_id_lst])
    current_target_lyr = arcpy.management.MakeFeatureLayer(target_lyr, where_clause=query)[0]

    # solve for nearest target to each area
    nearest_df = get_nearest_dataframe(
        network_dataset=network_dataset,
        target_fc=current_target_lyr,
        target_id_fld=target_id_fld,
        area_fc=area_lyr,
        area_id_fld=area_id_fld,
        max_near_dist=not use_entire_extent,
        centroid_weighting_fc=centroid_weighting_fc
    )

    # pass this first result back
    yield year, month, nearest_df

    # iterate the remaining opening open dates
    for open_dt in open_dt_lst[1:]:

        # get the year and month from the datetime
        year, month = get_dtidx(open_dt)

        # create the rebalanced nearest dataframe
        nearest_df = rebalance_near_solution(open_dt, network_dataset, nearest_df, target_lyr, target_id_fld,
                                             target_open_date_fld, area_lyr, area_id_fld)

        # return the result
        yield year, month, nearest_df


def create_iterative_nearest_csv(output_dir, target_lyr, target_open_date_fld, target_id_fld, area_lyr,
                                 area_id_fld, network_dataset, use_entire_extent=True, centroid_weighting_fc=None):
    """
    Iteratively walk through the years by month and rebalance the contributing geography nearest solution every time
    the store count changes.
    :param output_dir: Output directory where the solution CSV files will be stored.
    :param target_lyr: Layer containing the target locations (stores) for the nearest solution.
    :param target_open_date_fld: Datetime field containing the open date.
    :param target_id_fld: Field with the unique identifier for each target location.
    :param area_lyr: Geographic layer with contributing areas - typically zip codes, block groups, etc.
    :param area_id_fld: Unique ID field used to identify the area by ID
    :param network_dataset: ArcGIS Transportation Network to be used for routing analysis.
    :param use_entire_extent: Boolean - optional - default True
        Compute the entire extent of the input geographic areas. If false, will only include geographic areas within
        the distance equal to the furthest distance between stores.
    :return:
    """
    # run the nearest generator to get the year, month and output dataframes, and save them to files
    for year, month, nearest_df in nearest_generator(target_lyr, target_open_date_fld, target_id_fld, area_lyr,
                                                     area_id_fld, network_dataset, use_entire_extent,
                                                     centroid_weighting_fc):

        # do something with the result, like save it to a CSV
        output_csv = os.path.join(output_dir, ('nearest_{}{:02d}.csv'.format(year, month)))
        nearest_df.to_csv(output_csv)

        # report completion
        print('{} - finished {} {:02d}'.format(datetime.now().isoformat(), year, month))


def create_iterative_area_feature_class(output_feature_class, target_lyr, target_open_date_fld, target_id_fld, area_lyr,
                                        area_id_fld, network_dataset, use_entire_extent=True,
                                        centroid_weighting_fc=None):
    """
    Iteratively walk through the years by month and rebalance the contributing geography nearest solution every time
    the store count changes.
    :param output_feature_class: Output feature class where the solution will be stored.
    :param target_lyr: Layer containing the target locations (stores) for the nearest solution.
    :param target_open_date_fld: Datetime field containing the open date.
    :param target_id_fld: Field with the unique identifier for each target location.
    :param area_lyr: Geographic layer with contributing areas - typically zip codes, block groups, etc.
    :param area_id_fld: Unique ID field used to identify the area by ID
    :param network_dataset: ArcGIS Transportation Network to be used for routing analysis.
    :param use_entire_extent: Boolean - optional - default True
        Compute the entire extent of the input geographic areas. If false, will only include geographic areas within
        the distance equal to the furthest distance between stores.
    :return: String path to the output feature class.
    """
    # create an instance of the nearest generator with all the parameters populated
    nearest_gen = nearest_generator(target_lyr, target_open_date_fld, target_id_fld, area_lyr, area_id_fld,
                                    network_dataset, use_entire_extent, centroid_weighting_fc)

    # helper function to create output spatially enabled dataframe
    def near_to_sedf(near_obj):

        # pull out the specific objects explicitly
        year = near_obj[0]
        month = near_obj[1]
        near_df = near_obj[2]

        # create a datetime object corresponding to the first day of the month and populate this into an open datetime col
        near_df['open_datetime'] = datetime(year, month, 1)

        # load the area feature class into a dataframe and format it for joining to the near dataframe
        area_df = GeoAccessor.from_featureclass(area_lyr)
        area_df = area_df[[area_id_fld, 'SHAPE']].copy()
        area_df.set_index(area_id_fld, inplace=True, drop=True)

        # join the area dataframe to the near dataframe so it gets geometry
        return near_df.join(area_df, 'area_contrib_id')

    # run the nearest generator once to get the first result, which will be used as a template for the subsequent
    # outputs created in later runs
    near_obj = next(nearest_gen)
    near_sdf = near_to_sedf(near_obj)

    # export to the target dataframe, creating the template for subsequent runs
    near_sdf.spatial.to_featureclass(output_feature_class)

    # now, since the nearest generator has already run once, run the remainder of the cycles
    for near_obj in nearest_gen:

        # create the near spatially enabled dataframe, and export it to a temporary feature class
        near_sdf = near_to_sedf(near_obj)
        temp_fc = f'in_memory/near_areas_{uuid.uuid4().hex}'
        near_sdf.spatial.to_featureclass(temp_fc)

        # now, append the new near features to the initial output
        arcpy.management.Append(temp_fc, output_feature_class)

    # once finished, return the path to the output feature class
    return output_feature_class

