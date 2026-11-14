import _env  # noqa: F401
import xarray as xr
from hydromt import DataCatalog

d = xr.open_dataset("data/processed/rain_field_crs.nc")
print(d)
print("crs:", d.rio.crs if hasattr(d, "rio") else None)
dc = DataCatalog("models/catalog.yml")
try:
    r = dc.get_rasterdataset("rain")
    print("loaded:", type(r), getattr(r, "dims", None))
except Exception as e:
    print("ERR", type(e).__name__, e)
