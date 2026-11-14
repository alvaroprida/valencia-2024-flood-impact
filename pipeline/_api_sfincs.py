import inspect

import _env  # noqa: F401
from hydromt_sfincs import SfincsModel

for n in ("setup_grid", "setup_grid_from_region", "setup_dep", "setup_mask_active", "setup_mask_bounds",
          "setup_manning_roughness", "setup_cn_infiltration", "setup_precip_forcing_from_grid",
          "setup_waterlevel_forcing", "setup_subgrid", "setup_config"):
    f = getattr(SfincsModel, n)
    print("\n##", n, inspect.signature(f))
