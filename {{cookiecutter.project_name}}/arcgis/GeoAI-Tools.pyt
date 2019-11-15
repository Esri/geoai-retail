# -*- coding: utf-8 -*-
import os

from arcgis.features import GeoAccessor
import arcpy
from ba_tools import data, proximity

# ensure outputs can be overwritten
arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "GeoAI-Tools"
        self.alias = "GeoAI-Tools"

        # List of tool classes associated with this toolbox
        self.tools = [AddUsaGeographyLayer, GetBusinessesByCode, GetCompetitionByLayerLookup,
                      ExportDataForMachineLearning, GetNearestRoutingSolution]


class AddUsaGeographyLayer(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add USA Geography Layer"
        self.description = "Add USA Geography Layer"
        self.canRunInBackground = False
        self.category = "USA Data"

    def getParameterInfo(self):
        """Define parameter definitions"""
        lyr = arcpy.Parameter(
            name='ba_layer',
            displayName='Business Analyst Layer',
            direction='Input',
            datatype='GPString',
            parameterType='Required',
            enabled=True
        )
        lyr.filter.type = 'ValueList'
        lyr.filter.list = ['Block Group', 'Tract', 'Zip Code', 'County', 'Place/City', 'CBSA', 'DMA', 'State']
        params = [lyr]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        lyr_name = parameters[0].valueAsText

        if lyr_name == 'Block Group':
            out_lyr = data.layer_block_group
        elif lyr_name == 'Tract':
            out_lyr = data.layer_census_tract
        elif lyr_name == 'Zip Code':
            out_lyr = data.layer_postal_code
        elif lyr_name == 'County':
            out_lyr = data.layer_county
        elif lyr_name == 'Place/City':
            out_lyr = data.layer_places
        elif lyr_name == 'CBSA':
            out_lyr = data.layer_cbsa
        elif lyr_name == 'DMA':
            out_lyr = data.layer_dma
        elif lyr_name == 'State':
            out_lyr = data.layer_states

        out_lyr.name = str(lyr_name)

        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprx_map = aprx.activeMap
        aprx_map.addLayer(out_lyr)

        return out_lyr


class GetBusinessesByCode(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Get Businesses by NAICS or SIC Code"
        self.description = "Get Business Feature Class by NAICS or SIC Code."
        self.canRunInBackground = False
        self.category = "USA Data"

    def getParameterInfo(self):
        """Define parameter definitions"""
        code_type = arcpy.Parameter(
            name='code_type',
            displayName='Code Type',
            direction='Input',
            datatype='GPString',
            parameterType='Required',
            enabled=True
        )
        code_type.filter.type = 'ValueList'
        code_type.filter.list = ['NAICS', 'SIC']

        code = arcpy.Parameter(
            name='code',
            displayName='Business Category Code',
            direction='Input',
            datatype='GPString',
            parameterType='Required',
            enabled=True
        )
        aoi_lyr = arcpy.Parameter(
            name='aoi_layer',
            displayName='Area of Interest',
            direction='Input',
            datatype=['GPFeatureLayer', 'DEFeatureClass'],
            parameterType='Required',
            enabled=True
        )
        params = [code_type, code, aoi_lyr]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # retrieve the parameters
        code_type = parameters[0].valueAsText
        code = parameters[1].valueAsText.strip()
        aoi_lyr = parameters[2].value

        # check the Code to ensure it will work
        if not str(code).isnumeric():
            raise Exception('Business Category Code must be numeric')
        elif code_type == 'NAICS' and not len(code) == 8:
            raise Exception('NAICS Code must be eight digits')
        elif code_type == 'SIC' and not len(code) == 6:
            raise Exception('SIC Code  must be six digits')

        # get the businesses layer
        business_lyr = data.layer_businesses

        # get the businesses by naics code
        naics_fc = arcpy.analysis.Select(
            in_features=business_lyr,
            out_feature_class='memory/naics_fc',
            where_clause=f"{code_type} = '{code}'"
        )

        # get a reference to the current project, map and geodatabase
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprx_map = aprx.activeMap
        gdb = aprx.defaultGeodatabase

        # clip the naics features by the area of interest
        out_fc = arcpy.analysis.Clip(
            in_features=naics_fc,
            clip_features=aoi_lyr,
            out_feature_class=os.path.join(gdb, f'businesses_{code}'),
        )[0]

        # create a layer from the output businesses
        out_lyr = arcpy.management.MakeFeatureLayer(out_fc, f'Businesses - NAICS {code}')[0]

        # add the layer to the map
        aprx_map.addLayer(out_lyr)

        return out_lyr


class GetCompetitionByLayerLookup(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Get Competitors by Layer Lookup"
        self.description = "Get Competitors Based on NAICS and SIC Codes in an Existing Layer"
        self.canRunInBackground = False
        self.category = "USA Data"

    def getParameterInfo(self):
        """Define parameter definitions"""
        business_lyr = arcpy.Parameter(
            name='business_layer',
            displayName='Business Layer',
            direction='Input',
            datatype=['GPFeatureLayer', 'DEFeatureClass'],
            parameterType='Required',
            enabled=True
        )
        aoi_lyr = arcpy.Parameter(
            name='aoi_layer',
            displayName='Area of Interest',
            direction='Input',
            datatype=['GPFeatureLayer', 'DEFeatureClass'],
            parameterType='Required',
            enabled=True
        )
        params = [business_lyr, aoi_lyr]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # retrieve the parameters
        in_business_lyr = parameters[0].value
        aoi_lyr = parameters[1].value

        # get the businesses layer
        business_lyr = data.get_business_competitor_layer(in_business_lyr)

        # get a reference to the current project, map and geodatabase
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprx_map = aprx.activeMap
        gdb = aprx.defaultGeodatabase

        # clip the naics features by the area of interest
        out_fc = arcpy.analysis.Clip(
            in_features=business_lyr,
            clip_features=aoi_lyr,
            out_feature_class=os.path.join(gdb, f'businesses_competition'),
        )[0]

        # create a layer from the output businesses
        out_lyr = arcpy.management.MakeFeatureLayer(out_fc, f'Businesses - Competition')[0]

        # add the layer to the map
        aprx_map.addLayer(out_lyr)

        return out_lyr


class ExportDataForMachineLearning(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Export Data for Machine Learning"
        self.description = "Export data for machine learning data preparation pipeline."
        self.canRunInBackground = False

        # get a reference to the current project, map and geodatabase
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        self.aprx_map = aprx.activeMap
        self.gdb = aprx.defaultGeodatabase

    def getParameterInfo(self):
        """Define parameter definitions"""
        loc_lyr = arcpy.Parameter(
            name='loc_lyr',
            displayName='Brand Location Layer',
            direction='Input',
            datatype='GPFeatureLayer',
            parameterType='Optional',
            enabled=True
        )
        loc_lyr.filter.list = ['Point']

        loc_id_fld = arcpy.Parameter(
            name='loc_id_fld',
            displayName='Origin Geography ID Field',
            direction='Input',
            datatype='Field',
            parameterType='Optional',
            enabled=False
        )
        loc_id_fld.parameterDependencies = [loc_lyr.name]

        comp_loc_lyr = arcpy.Parameter(
            name='comp_loc_lyr',
            displayName='Competition Location Layer',
            direction='Input',
            datatype='GPFeatureLayer',
            parameterType='Optional',
            enabled=True
        )
        comp_loc_lyr.filter.list = ['Point']

        comp_id_fld = arcpy.Parameter(
            name='comp_id_fld',
            displayName='Competition ID Field',
            direction='Input',
            datatype='Field',
            parameterType='Optional',
            enabled=False
        )
        comp_id_fld.parameterDependencies = [comp_loc_lyr.name]

        comp_brnd_nm = arcpy.Parameter(
            name='comp_brnd_nm',
            displayName='Competition Brand Name Field',
            direction='Input',
            datatype='Field',
            parameterType='Optional',
            enabled=False
        )
        comp_brnd_nm.parameterDependencies = [comp_loc_lyr.name]

        origin_geo_lyr = arcpy.Parameter(
            name='origin_geo_lyr',
            displayName='Origin Geography Layer',
            direction='Input',
            datatype='GPFeatureLayer',
            parameterType='Optional',
            enabled=True
        )
        origin_geo_lyr.filter.list = ['Polygon']

        origin_id_fld = arcpy.Parameter(
            name='origin_id_fld',
            displayName='Origin Geography ID Field',
            direction='Input',
            datatype='Field',
            parameterType='Optional',
            enabled=False
        )
        origin_id_fld.parameterDependencies = [origin_geo_lyr.name]

        params = [loc_lyr, loc_id_fld, comp_loc_lyr, comp_id_fld, comp_brnd_nm, origin_geo_lyr, origin_id_fld]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[0].value:
            parameters[1].enabled = True
            parameters[1].parameterType = 'Required'
        elif not parameters[0].value:
            parameters[1].value = None
            parameters[1].enabled = False
            parameters[1].parameterType = 'Optional'

        if parameters[2].value:
            parameters[3].enabled = True
            parameters[3].parameterType = 'Required'
            parameters[4].enabled = True
            parameters[4].parameterType = 'Required'
        elif not parameters[2].value:
            parameters[3].value = None
            parameters[3].enabled = False
            parameters[3].parameterType = 'Optional'
            parameters[4].value = None
            parameters[4].enabled = False
            parameters[4].parameterType = 'Optional'

        if parameters[5].value:
            parameters[6].enabled = True
            parameters[6].parameterType = 'Required'
        elif not parameters[5].value:
            parameters[6].value = None
            parameters[6].enabled = False
            parameters[6].parameterType = 'Optional'

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def _create_output_features(self, lyr, id_fld_name, out_fc, out_id_fld, in_name_fld=None, out_name_fld=None):
        """Function handling output creation."""

        # get the spatial reference of the input layer
        lyr_sr = arcpy.Describe(lyr).spatialReference

        # if the input spatial reference is not WGS84
        if lyr_sr.factoryCode != 4326:

            # get any applicable transformations if the datum of the input is not WGS84
            trans_lst = arcpy.ListTransformations(lyr_sr, arcpy.SpatialReference(4326))

            # if a transformation is necessary, project using it, otherwise project without
            temp_fc = os.path.join(arcpy.env.scratchGDB, 'temp_features')
            out_sr = arcpy.SpatialReference(4326)
            if len(trans_lst):
                in_feat = arcpy.management.Project(lyr, temp_fc, out_sr, trans_lst[0])[0]
            else:
                in_feat = arcpy.management.Project(lyr, temp_fc, out_sr)[0]

        # if the input is in WGS84, just let the input pass through
        else:
            in_feat = lyr

        # load the feature class into a dataframe
        df = GeoAccessor.from_featureclass(in_feat)

        # run a few checks
        if id_fld_name not in df.columns:
            raise Exception(f'{id_fld_name} is not in the {lyr.name} dataset')
        if df[id_fld_name].dtype != 'int64' and df[id_fld_name].dtype != 'O':
            raise Exception('Id field must be numeric.')
        if not any(df[id_fld_name].str.isnumeric()):
            raise Exception('All the id field values, even if strings, must be numeric.')
        elif any(df[id_fld_name].isnull()):
            raise Exception(
                'One or more of the features appear to be missing a value. There cannot be any null or empty values.')


        if in_name_fld:
            # filter to only needed fields
            df = df[[id_fld_name, in_name_fld, 'SHAPE']].copy()
            df.rename(columns={id_fld_name: out_id_fld, in_name_fld: out_name_fld}, inplace=True)
        else:
            # rename the output id field ot desired name
            df = df[[id_fld_name, 'SHAPE']].copy()
            df.rename(columns={id_fld_name: out_id_fld}, inplace=True)

        # save and return the result
        return df.spatial.to_featureclass(out_fc)

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # retrieve the parameters
        loc_lyr = parameters[0].value
        loc_id_fld = parameters[1].valueAsText
        comp_loc_lyr = parameters[2].value
        comp_id_fld = parameters[3].valueAsText
        comp_brnd_nm = parameters[4].valueAsText
        origin_geo_lyr = parameters[5].value
        origin_id_fld = parameters[6].valueAsText

        if comp_loc_lyr:
            comp_out_fc = os.path.join(self.gdb, 'location_competition')
            self._create_output_features(comp_loc_lyr, comp_id_fld, comp_out_fc, 'comp_dest_id', comp_brnd_nm,
                                         'comp_brand_name')
            # comp_lyr = arcpy.management.MakeFeatureLayer(comp_out_fc, 'Competition Locations')[0]
            comp_lyr = arcpy.mp.LayerFile('./layer_files/competition.lyrx')
            self.aprx_map.addLayer(comp_lyr)

        if loc_lyr:
            loc_out_fc = os.path.join(self.gdb, 'location')
            self._create_output_features(loc_lyr, loc_id_fld, loc_out_fc, 'dest_id')
            # loc_lyr = arcpy.management.MakeFeatureLayer(loc_out_fc, 'Business Locations')[0]
            loc_lyr = arcpy.mp.LayerFile('./layer_files/business.lyrx')
            self.aprx_map.addLayer(loc_lyr)

        if origin_geo_lyr:
            orig_out_fc = os.path.join(self.gdb, 'origin_geography')
            self._create_output_features(origin_geo_lyr, origin_id_fld, orig_out_fc, 'origin_id')
            # orig_lyr = arcpy.management.MakeFeatureLayer(orig_out_fc, 'Origin Geographies')[0]
            orig_lyr = arcpy.mp.LayerFile('./layer_files/origin_geo.lyrx')
            self.aprx_map.addLayer(orig_lyr)

        return True


class GetNearestRoutingSolution(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Get Nearest Routing Solution"
        self.description = "Create intermediate routing results to include all the routing geometries."
        self.canRunInBackground = False
        self.category = "Create Demo Data"

        # get a reference to the current project, map and geodatabase
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        self.aprx_map = aprx.activeMap
        self.gdb = aprx.defaultGeodatabase

    def getParameterInfo(self):
        """Define parameter definitions"""
        origin_lyr = arcpy.Parameter(
            name='origin_lyr',
            displayName='Origin Layer',
            direction='Input',
            datatype='GPFeatureLayer',
            parameterType='Required',
            enabled=True
        )
        origin_id_fld = arcpy.Parameter(
            name='origin_id_fld',
            displayName='Origin ID Field',
            direction='Input',
            datatype='Field',
            parameterType='Required',
            enabled=False
        )
        origin_id_fld.parameterDependencies = [origin_lyr.name]

        dest_lyr = arcpy.Parameter(
            name='aoi_layer',
            displayName='Destination Layer',
            direction='Input',
            datatype='GPFeatureLayer',
            parameterType='Required',
            enabled=True
        )
        dest_id_fld = arcpy.Parameter(
            name='dest_id_fld',
            displayName='Destination ID Field',
            direction='Input',
            datatype='Field',
            parameterType='Required',
            enabled=False
        )
        dest_id_fld.parameterDependencies = [dest_lyr.name]

        near_count = arcpy.Parameter(
            name='near_count',
            displayName='Near Count',
            direction='Input',
            datatype='GPLong',
            parameterType='Optional',
            enabled=True
        )
        near_count.value = 6

        out_fc = arcpy.Parameter(
            name='out_fc',
            displayName='Output Feature Class',
            direction='Output',
            datatype='DEFeatureClass',
            parameterType='Required',
            enabled=True
        )
        out_fc.value = os.path.join(self.gdb, 'nearest_routes')

        params = [origin_lyr, origin_id_fld, dest_lyr, dest_id_fld, near_count, out_fc]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            parameters[1].enabled = True
            parameters[1].parameterType = 'Required'
        elif not parameters[0].value:
            parameters[1].value = None
            parameters[1].enabled = False
            parameters[1].parameterType = 'Optional'

        if parameters[2].value:
            parameters[3].enabled = True
            parameters[3].parameterType = 'Required'
        elif not parameters[2].value:
            parameters[3].value = None
            parameters[3].enabled = False
            parameters[3].parameterType = 'Optional'

        return True

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # retrieve the parameters
        origin_lyr = parameters[0].value
        origin_id_fld = parameters[1].valueAsText
        dest_lyr = parameters[2].value
        dest_id_lfd = parameters[3].valueAsText
        near_count = parameters[4].value
        out_fc = parameters[5].valueAsText

        # get the nearest solution as a dataframe
        solve_df = proximity.get_closest_solution(
            origins=origin_lyr,
            origin_id_fld=origin_id_fld,
            destinations=dest_lyr,
            dest_id_fld=dest_id_lfd,
            network_dataset=data.usa_network_dataset,
            destination_count=near_count
        )

        # save the dataframe to a feature class
        solve_fc = solve_df.spatial.to_featureclass(out_fc)

        # create a feature layer and add it to the map
        solve_lyr = arcpy.management.MakeFeatureLayer(solve_fc, 'Nearest Routing Solution')[0]
        self.aprx_map.addLayer(solve_lyr)
