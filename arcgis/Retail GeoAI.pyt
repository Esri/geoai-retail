# -*- coding: utf-8 -*-

import arcpy
import os
import sys

dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(dir_path, 'src')
sys.path.append(src_dir)

from archive_stash import enrich


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "RetailGeoAI"
        self.alias = "Retail GeoAI"

        # List of tool classes associated with this toolbox
        self.tools = [ExportEnrichmentCsvVariableFile, EnrichUsingCsvVariableFile,
                      EnrichUsingExistingEnrichedFeatureClassAsTemplate]


class EnrichUsingCsvVariableFile(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Enrich Using CSV Variable File"
        self.description = "Perform geoenrichment on a feature class using variables from a saved CSV variable file."
        self.canRunInBackground = True
        self.category = 'Enrich'

    def getParameterInfo(self):
        """Define parameter definitions"""
        input_feature_class = arcpy.Parameter(
            displayName='Feature Class to be Enriched',
            name='EnrichFeatureClass',
            datatype=['DEFeatureClass', 'GPFeatureLayer'],
            parameterType='Required',
            direction='Input'
        )
        path_to_csv_variable_file = arcpy.Parameter(
            displayName='CSV Variable File',
            name='PathToCsvVariableFile',
            datatype='DEFile',
            parameterType='Required',
            direction='Input'
        )
        output_feature_class = arcpy.Parameter(
            displayName='Output Enriched Feature Class',
            name='OutputFeatureClass',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Output'
        )
        params = [input_feature_class, path_to_csv_variable_file, output_feature_class]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return arcpy.CheckExtension('Business')

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
        in_fc = arcpy.Describe(parameters[0]).catalogPath
        csv_path = parameters[1].valueAsText
        out_fc = parameters[2].valueAsText
        enriched_fc = enrich.using_csv_variable_file(in_fc, csv_path, out_fc)

        return enriched_fc


class EnrichUsingExistingEnrichedFeatureClassAsTemplate(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Enrich Using Existing Enriched Feature Class as Template"
        self.description = "Perform geoenrichment on a feature class using variables derived from an already " \
                           "exsiting feature class."
        self.canRunInBackground = True
        self.category = 'Enrich'

    def getParameterInfo(self):
        """Define parameter definitions"""
        template_feature_class = arcpy.Parameter(
            displayName='Enriched Feature Class Template',
            name='FeatureClassTemplate',
            datatype=['DEFeatureClass', 'GPFeatureLayer'],
            parameterType='Required',
            direction='Input'
        )
        input_feature_class_to_enrich = arcpy.Parameter(
            displayName='Feature Class to be Enriched',
            name='FeatureClassInput',
            datatype=['DEFeatureClass', 'GPFeatureLayer'],
            parameterType='Required',
            direction='Input'
        )
        output_enriched_feature_class = arcpy.Parameter(
            displayName='Output Enriched Feature Class',
            name='OutputFeatureClass',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Output'
        )
        params = [template_feature_class, input_feature_class_to_enrich, output_enriched_feature_class]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return arcpy.CheckExtension('Business')

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
        template_fc = arcpy.Describe(parameters[0]).catalogPath
        in_fc = arcpy.Describe(parameters[1]).catalogPath
        out_fc = parameters[2].valueAsText
        enriched_fc = enrich.using_existing_enriched_feature_class_as_template(template_fc, in_fc, out_fc)

        return enriched_fc


class ExportEnrichmentCsvVariableFile(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Export Enrichment CSV Variable File"
        self.description = "Export a CSV Variable file, which can be used to perform the same geoenrichment again, " \
                           "and also to show what variables were used."
        self.canRunInBackground = True
        self.category = 'Enrich'

    def getParameterInfo(self):
        """Define parameter definitions"""
        enriched_feature_class = arcpy.Parameter(
            displayName='Enriched Feature Class Template',
            name='FeatureClassTemplate',
            datatype=['DEFeatureClass', 'GPFeatureLayer'],
            parameterType='Required',
            direction='Input'
        )
        output_csv_variable_file = arcpy.Parameter(
            displayName='Output CSV Variable File',
            name='PathToCsvVariableFile',
            datatype='DEFile',
            parameterType='Required',
            direction='Output'
        )
        params = [enriched_feature_class, output_csv_variable_file]
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
        enriched_fc = arcpy.Describe(parameters[0]).catalogPath
        out_fc = parameters[1].valueAsText
        csv_file = enrich.export_enrichment_csv_variable_file(enriched_fc, out_fc)

        return csv_file
