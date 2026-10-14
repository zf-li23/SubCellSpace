"""SOPA mode: cell-level analysis built on SOPA (https://github.com/gustaveroussy/sopa, BSD-3, see SOPA_LICENSE).

SOPA is used as a library where it works unchanged (``sopa.aggregate``, ``sopa.spatial.assign_transcript_to_cell``).
Where SOPA assumes an image is present — not the case for most GEO uploads — the corresponding step is ported here
without that assumption:

- ``sdata.to_sopa_sdata``      image-free SpatialData with the keys SOPA expects
- ``aggregate.count_by_cell_id``  counts from vendor cell_ids (SOPA only aggregates over shapes)
- ``preprocess.preprocess``    ``sopa scanpy-preprocess`` without the image sanity check
"""

from .aggregate import count_by_cell_id, count_with_boundaries
from .preprocess import add_markers, preprocess
from .sdata import to_sopa_sdata

__all__ = ["count_by_cell_id", "count_with_boundaries", "preprocess", "add_markers", "to_sopa_sdata"]
