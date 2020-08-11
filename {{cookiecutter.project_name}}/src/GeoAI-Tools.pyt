# -*- coding: utf-8 -*-
import os

from arcgis.features import GeoAccessor
from arcgis.geometry import Geometry
import arcpy
from ba_tools import data, proximity, enrich

# ensure outputs can be overwritten
arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "GeoAI-Tools"
        self.alias = "GeoAITools"

        # List of tool classes associated with this toolbox
        self.tools = [GetNearestRoutingSolution, EnichFromPreviouslyEnriched, AddUsaGeographyLayer,
                      AddGeographyLayerInAoi, GetBusinessesByCode, GetCompetitionByLayerLookup, CreateAoiMask,
                      ExportDataForMachineLearning]


class EnichFromPreviouslyEnriched(object):
    def __init__(self):
        """Enrich a dataset using another previously enriched dataset as the template."""
        """id_field:str=None, input_feature_class_fields_in_output:bool=False"""
        self.label = "Erich from Previously Enriched"
        self.description = "Enrich from Previously Enriched"
        self.canRunInBackground = False
        self.category = "Enrich"

    def getParameterInfo(self):
        """Input Parameters"""
        enrch_lyr = arcpy.Parameter(
            name='enrich_;yr',
            displayName='Input Layer',
            direction='Input',
            datatype=['GPFeatureLayer', 'DEFeatureClass'],
            parameterType='Required',
            enabled=True
        )

        loc_id_fld = arcpy.Parameter(
            name='geo_id',
            displayName='Enrich Geography ID Field',
            direction='Input',
            datatype='Field',
            parameterType='Optional',
            enabled=False
        )
        loc_id_fld.parameterDependencies = [enrch_lyr.name]

        tmplt_lyr = arcpy.Parameter(
            name='tmplt_lyr',
            displayName='Template Layer',
            direction='Input',
            datatype=['GPFeatureLayer', 'DEFeatureClass'],
            parameterType='Required',
            enabled=True
        )

        output_fc = arcpy.Parameter(
            name='output_fc',
            displayName='Output Feature Class',
            direction='Output',
            datatype='GPFeatureClass',
            parameterType='Required',
            enabled=True
        )

        params = [enrch_lyr, loc_id_fld, tmplt_lyr, output_fc]
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
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """Tool source code."""
        enrch_lyr = parameters[0].value
        loc_id_fld = parameters[1].valueAsText
        tmplt_lyr = parameters[2].value
        output_fc = parameters[3].valueAsText

        out_df = enrich.enrich_from_enriched(
            enrich_template_feature_class=tmplt_lyr,
            feature_class_to_enrich=enrch_lyr,
            id_field=loc_id_fld,
            input_feature_class_fields_in_output=False,
            return_geometry=True
        )
        out_fc = out_df.spatial.to_featureclass(output_fc)

        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprx_map = aprx.activeMap
        aprx_map.addLayer(out_fc)

        return out_fc


class AddUsaGeographyLayer(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Standard Geography Layer"
        self.description = "Add Standard Geography Layer"
        self.canRunInBackground = False
        self.category = "Standard Geographic Areas"

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

    def _get_lyr(self, lyr_name):
        """Helper function to look up layer from data."""
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
        return out_lyr

    def _add_lyr_to_map(self, lyr):
        """Helper function to add layer to active map."""
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprx_map = aprx.activeMap
        aprx_map.addLayer(lyr)
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        lyr_name = parameters[0].valueAsText
        out_lyr = self._get_lyr(lyr_name)
        out_lyr.name = str(lyr_name)
        self._add_lyr_to_map(out_lyr)
        return out_lyr


class AddGeographyLayerInAoi(AddUsaGeographyLayer):

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Get Standard Geography in AOI"
        self.description = "Get Standard Geography in AOI"
        self.canRunInBackground = False
        self.category = "Standard Geographic Areas"

    def getParameterInfo(self):
        """Define parameter definitions"""
        geo_lyr = arcpy.Parameter(
            name='ba_layer',
            displayName='Business Analyst Layer',
            direction='Input',
            datatype='GPString',
            parameterType='Required',
            enabled=True
        )
        geo_lyr.filter.type = 'ValueList'
        geo_lyr.filter.list = ['Block Group', 'Tract', 'Zip Code', 'County', 'Place/City', 'CBSA', 'DMA', 'State']

        aoi_lyr = arcpy.Parameter(
            name='aoi_layer',
            displayName='Area of Interest',
            direction='Input',
            datatype='GPFeatureLayer',
            parameterType='Required',
            enabled=True
        )
        aoi_lyr.filter.list = ["Polygon"]

        out_fc = arcpy.Parameter(
            name='out_fc',
            displayName='Output Feature Class',
            direction='Output',
            datatype='DEFeatureClass',
            parameterType='Required',
            enabled=True
        )

        params = [geo_lyr, aoi_lyr, out_fc]
        return params

    def execute(self, parameters, messages):
        """The source code of the tool."""
        geo_lyr_name = parameters[0].valueAsText
        aoi_param = parameters[1].value
        out_fc = parameters[2].valueAsText

        geo_lyr = self._get_lyr(geo_lyr_name)
        geo_lyr.name = str(geo_lyr_name)

        aoi_lyr = arcpy.management.MakeFeatureLayer(aoi_param)[0]
        sel_lyr = arcpy.management.SelectLayerByLocation(geo_lyr, 'HAVE_THEIR_CENTER_IN', aoi_lyr)[0]
        geo_fc = arcpy.management.CopyFeatures(sel_lyr, out_fc)

        geo_lyr = arcpy.management.MakeFeatureLayer(geo_fc)[0]
        arcpy.management.ApplySymbologyFromLayer(geo_lyr, "./layer_files/origin_geo.lyrx")

        self._add_lyr_to_map(geo_lyr)
        
        return geo_lyr


class GetBusinessesByCode(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Get Businesses by NAICS or SIC Code"
        self.description = "Get Business Feature Class by NAICS or SIC Code."
        self.canRunInBackground = False
        self.category = "Business Data"

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
            datatype='GPFeatureLayer',
            parameterType='Required',
            enabled=True
        )
        aoi_lyr.filter.list = ["Polygon"]

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
        self.category = "Business Data"

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
            comp_lyr = arcpy.mp.LayerFile('./layer_files/competition.lyrx')
            self.aprx_map.addLayer(comp_lyr)

        if loc_lyr:
            loc_out_fc = os.path.join(self.gdb, 'location')
            self._create_output_features(loc_lyr, loc_id_fld, loc_out_fc, 'dest_id')
            loc_lyr = arcpy.mp.LayerFile('./layer_files/business.lyrx')
            self.aprx_map.addLayer(loc_lyr)

        if origin_geo_lyr:
            orig_out_fc = os.path.join(self.gdb, 'origin_geography')
            self._create_output_features(origin_geo_lyr, origin_id_fld, orig_out_fc, 'origin_id')
            orig_lyr = arcpy.mp.LayerFile('./layer_files/origin_geo.lyrx')
            self.aprx_map.addLayer(orig_lyr)

        return True


class GetNearestRoutingSolution(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Get Nearest Routing Solution"
        self.description = "Create intermediate routing results to include all the routing geometries."
        self.canRunInBackground = False
        self.category = "Demo Data"

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


class CreateAoiMask(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create AOI Mask"
        self.description = "Create area of interest mask."
        self.canRunInBackground = False

        # get a reference to the current project, map and geodatabase
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        self.aprx_map = aprx.activeMap
        self.gdb = aprx.defaultGeodatabase

    def getParameterInfo(self):
        """Define parameter definitions"""
        aoi_lyr = arcpy.Parameter(
            name='aoi_lyr',
            displayName='Area of Interest',
            direction='Input',
            datatype='GPFeatureLayer',
            parameterType='Required',
            enabled=True
        )
        out_fc = arcpy.Parameter(
            name='out_fc',
            displayName='Output Mask Feature Class',
            direction='Output',
            datatype='DEFeatureClass',
            parameterType='Required',
            enabled=True
        )

        params = [aoi_lyr, out_fc]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return True

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # retrieve the parameters
        aoi_fc = parameters[0].value
        out_fc = parameters[1].valueAsText

        # ensure the aoi is a polygon
        geom_type = arcpy.Describe(aoi_fc).shapeType
        if not geom_type == 'Polygon':
            raise Exception(f'The area of interest input must be the Polygon geometry type, not {geom_type}.')

        # create a geomery list with one geometry, a rectangle covering the globe
        mask_geom = Geometry({
            "rings": [[
                [-180.0, -90.0],
                [-180.0, 90.0],
                [180.0, 90.0],
                [180.0, -90.0],
                [-180.0, -90.0]
            ]],
            "spatialReference": {"wkid": 4326, "latestWkid": 4326}
        })
        extent_features = [mask_geom.as_arcpy]

        # create a mask feature class by punching out the area of interest
        mask_fc = arcpy.analysis.Erase(extent_features, aoi_fc, out_fc)[0]

        # get a layer to work with, and apply nice symbology
        lyr = arcpy.management.MakeFeatureLayer(mask_fc)[0]
        arcpy.management.ApplySymbologyFromLayer(lyr, './layer_files/aoi_mask.lyrx')

        # add the mask to the map
        self.aprx_map.addLayer(lyr)
