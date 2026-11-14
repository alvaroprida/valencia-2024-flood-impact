"""Import first: point PROJ/GDAL at the conda env, not at the PostgreSQL install that sets PROJ_LIB globally."""
import os
import sys
import warnings

_lib = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Library", "share")
_conda = r"C:\Users\alvar\miniconda3\envs\fluvial_flood_risk\Library\share"
for base in (_lib, _conda):
    if os.path.exists(os.path.join(base, "proj", "proj.db")):
        os.environ["PROJ_LIB"] = os.environ["PROJ_DATA"] = os.path.join(base, "proj")
        os.environ["GDAL_DATA"] = os.path.join(base, "gdal")
        break

_bin = r"C:\Users\alvar\miniconda3\envs\fluvial_flood_risk\Library\bin"
if os.path.isdir(_bin):
    os.environ["PATH"] = _bin + os.pathsep + os.environ["PATH"]
    os.add_dll_directory(_bin)

warnings.filterwarnings("ignore")
