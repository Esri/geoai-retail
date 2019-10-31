def get_chunked_list(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

import os, platform, sys, unittest, time, winreg, re
import xml.etree.ElementTree as ET

# add dirs to sys.path (bottommost first)
for i in range(-1, -6, -1):
    sys.path.append(os.sep.join(os.getcwd().split(os.sep)[:i]))

import arcpy, shared_utils, BATestHelper

us_dataset = "USA_ESRI_2019"
ca_dataset = "CAN_ESRI_2018"

''' Test that runs Enrich for every variable in USA_ESRI_2019 '''

class TestEnrichGenericLocal:
    __owner__ = 'Max Sattarov'

    @classmethod
    def setUpClass(self):
        arcpy.CheckOutExtension("BusinessPrem")
        arcpy.env.overwriteOutput = True

    @classmethod
    def tearDownClass(self):
        arcpy.CheckInExtension("BusinessPrem")

    @staticmethod
    def get_dc_variables(dataset):
        reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\WOW6432Node\ESRI\BusinessAnalyst\Datasets\{0}".format(dataset))
        dc_folder = winreg.QueryValueEx(reg, "DataCollectionsDir")[0]

        for f in os.listdir(dc_folder):
            dc_file = os.path.join(dc_folder, f)
            tree = ET.parse(dc_file)
            root = tree.getroot()
            if root.tag == "DataCollection":
                dc_name = root.find("Metadata/name").text
                # there's EPList.xml that is not a ba_data collection
                calculators = root.find("Calculators")
                for c in calculators:
                    fields = c.findall("Fields/Field")
                    for f in fields:
                        if "HideInDataBrowser" in f.attrib:
                            if f.attrib["HideInDataBrowser"] == "True":
                                continue  # skip hidden variables

                        yield dc_name + "." + f.attrib["Name"]

                        if "PercentBase" in f.attrib:
                            if f.attrib["PercentBase"]:  # not null or empty
                                yield dc_name + "." + f.attrib["Name"] + "_P"  # percent
                        if "IndexBaseValue" in f.attrib:
                            if f.attrib["IndexBaseValue"]:  # not null or empty
                                yield dc_name + "." + f.attrib["Name"] + "_I"  # percent
                        if "AverageBase" in f.attrib:
                            if f.attrib["AverageBase"]:  # not null or empty
                                yield dc_name + "." + f.attrib["Name"] + "_A"  # percent

    @staticmethod
    def get_out_field_name(ge_field_name):
        out_field_name = ge_field_name.replace(".", "_")
        out_field_name = re.sub(r"(^\d+)", r"F\1",
                                out_field_name)  # if string starts with a set of digits, replace them with Fdigits
        return out_field_name

    def check_enrich_for_chunk(input_fc, output_fc, variables, chunk_name):
        errors = []
        gp_error = False
        print("Testing chunk {0} of {1} variables".format(chunk_name, len(variables)))
        try:
            arcpy.ba.EnrichLayer(input_fc, output_fc, variables, None, 1, None)
        except:
            gp_error = True
            errors.append(arcpy.GetMessages())

        if not gp_error:
            # check that the out feature class exists, contains at least one feature and contains all expected fields, with non "None"seek
            fields = arcpy.ListFields(output_fc)
            field_names = [f.name for f in fields]
            field_names_set = set(field_names)

            out_field_names = list([TestEnrichGenericLocal.get_out_field_name(v) for v in variables])

            for out_field in out_field_names:
                if out_field not in field_names_set:
                    errors.append(
                        "Missing the following field in the output: {0} for chunk {1}".format(out_field, chunk_name))

            # check if the features in the output has all the values not dbnull
            with arcpy.da.SearchCursor(output_fc, out_field_names) as cursor:
                for row in cursor:
                    for (i, v) in enumerate(row):
                        if v is None:
                            errors.append(
                                "'None' value is detected in the output for variable {0}".format(out_field_names[i]))
        if errors:
            raise Exception(errors)

    @unittest.skipIf(shared_utils.AO11, "this case not valid on AO11")
    @unittest.skipIf(shared_utils.conf.get("unittest", "enable_generic_enrich_local_test") != "True",
                     "Skipping Enrich Generic tests unless requested in .ini")
    def test_Enrich_Generic_Local_US(self):
        outdir = shared_utils.create_output_folder()

        input_ws = shared_utils.resolve_data_path(r"BA\Enrich_Generic\Enrich_Generic_Local.gdb")

        arcpy.management.CreateFileGDB(outdir, "test_Enrich_Generic_Local_US", "CURRENT")
        out_gdb = os.path.join(outdir, "test_Enrich_Generic_Local_US.gdb")

        arcpy.env.baDataSource = "LOCAL;;{0}".format(us_dataset)

        vars = list(TestEnrichGenericLocal.get_dc_variables(us_dataset))

        for idx, vars_chunk in enumerate(BATestHelper.get_chunked_list(vars, 200)):
            # chunks of 200 variables in each
            chunk_name = "chunk" + str(idx) + "_us"
            test_call = (lambda c: TestEnrichGenericLocal.check_enrich_for_chunk(input_ws + "/" + "RingA_US",
                                                                                 out_gdb + "/" + chunk_name, vars_chunk,
                                                                                 c))
            yield (test_call, chunk_name)

    @unittest.skipIf(shared_utils.AO11, "this case not valid on AO11")
    @unittest.skipIf(shared_utils.conf.get("unittest", "enable_canada_local_test") != "True",
                     "Skipping Enrich Generic tests for Canada (disabled via .ini)")
    @unittest.skipIf(shared_utils.conf.get("unittest", "enable_generic_enrich_local_test") != "True",
                     "Skipping Enrich Generic tests (disabled via .ini)")
    def test_Enrich_Generic_Local_CA(self):
        outdir = shared_utils.create_output_folder()

        input_ws = shared_utils.resolve_data_path(r"BA\Enrich_Generic\Enrich_Generic_Local.gdb")

        arcpy.management.CreateFileGDB(outdir, "test_Enrich_Generic_Local_CA", "CURRENT")
        out_gdb = os.path.join(outdir, "test_Enrich_Generic_Local_CA.gdb")

        arcpy.env.baDataSource = "LOCAL;;{0}".format(ca_dataset)

        try:
            vars = list(TestEnrichGenericLocal.get_dc_variables(ca_dataset))
        except:
            raise unittest.SkipTest("Dataset for Canada is not installed")

        for idx, vars_chunk in enumerate(BATestHelper.get_chunked_list(vars, 200)):
            # chunks of 200 variables in each
            chunk_name = "chunk" + str(idx) + "_ca"
            test_call = (lambda c: TestEnrichGenericLocal.check_enrich_for_chunk(input_ws + "/" + "RingA_CA",
                                                                                 out_gdb + "/" + chunk_name, vars_chunk,
                                                                                 c))
            yield (test_call, chunk_name)