from geoai_retail import utils as utils
from arcgis.gis import GIS


def test_environment_init_no_gis():
    env = utils.Environment()
    assert(isinstance(env, utils.Environment))


def test_environment_init_gis():
    gis = GIS()
    env = utils.Environment(gis)
    assert(isinstance(env.gis, GIS))


def test_environment_init_active_gis():
    gis = GIS()
    env = utils.Environment(gis)
    assert(isinstance(env.gis, GIS))


def test_environment_has_package():
    env = utils.Environment()
    assert(env.has_package('os'))