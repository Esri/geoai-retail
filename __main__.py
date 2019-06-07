from sys import path
import os

# directory where local packages are stored
src_path = os.path.abspath('../src')

if __name__ == "__main__" and __package__ is None:

    path.append(os.path.abspath('../src/geoai_retail'))
    __package__ = "geoai_retail"

import geoai_retail