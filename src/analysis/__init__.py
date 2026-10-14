"""SOPA mode: cell-level analysis ported from SOPA 2.2.11 (https://github.com/gustaveroussy/sopa, BSD-3, see SOPA_LICENSE).

SOPA itself is not a dependency. The parts SubCellSpace needs are ported here, without SOPA's assumption that an
image is present (most GEO uploads have none; the matrix / transcripts carry the information needed):

- ``constants``              SOPA's gene-exclusion pattern and CosMx pixel size
- ``aggregate.assign_to_boundaries``  SOPA's point-in-polygon transcript assignment (``sopa.spatial.join``)
- ``aggregate.count_by_cell_id`` / ``count_with_boundaries``  per-cell counts (SOPA only aggregates over shapes)
- ``preprocess.preprocess``  ``sopa scanpy-preprocess`` without the image sanity check
"""

from .aggregate import assign_to_boundaries, count_by_cell_id, count_with_boundaries
from .constants import COSMX_PIXEL_SIZE, GENE_EXCLUDE_PATTERN
from .preprocess import add_markers, preprocess

__all__ = ["assign_to_boundaries", "count_by_cell_id", "count_with_boundaries", "preprocess", "add_markers",
           "COSMX_PIXEL_SIZE", "GENE_EXCLUDE_PATTERN"]
