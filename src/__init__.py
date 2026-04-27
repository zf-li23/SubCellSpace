"""SubCellSpace — A modular spatial transcriptomics analysis framework."""

import warnings

# Python 3.13: upstream spatialdata emits import-time FutureWarnings for
# functools.partial usage. These do not affect any computations.
warnings.filterwarnings(
    "ignore",
    message=r"functools\.partial will be a method descriptor in future Python versions.*",
    category=FutureWarning,
)