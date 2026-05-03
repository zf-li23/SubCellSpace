# ─────────────────────────────────────────────────────────────────────
# SubCellSpace Constants
#
# Centralised constants for spatial data attributes, canonical column
# names, and platform identifiers.  All modules import from here to
# avoid hard-coded strings scattered across the codebase.
# ─────────────────────────────────────────────────────────────────────

from __future__ import annotations

# ── Platform identifiers ─────────────────────────────────────────────

PLATFORM_COSMX = "cosmx"
PLATFORM_XENIUM = "xenium"
PLATFORM_MERFISH = "merfish"
PLATFORM_STEREOSEQ = "stereoseq"

ALL_PLATFORMS = [PLATFORM_COSMX, PLATFORM_XENIUM, PLATFORM_MERFISH, PLATFORM_STEREOSEQ]

# ── Canonical column names for raw_transcripts ───────────────────────
#
# Every platform loader must map its native columns to this canonical
# schema.  The columns ``x``, ``y``, and ``gene`` are mandatory.
# ``cell_id``, ``fov``, ``CellComp``, ``qv``, and ``z`` are optional.

COL_X = "x"           # float: spatial x coordinate (microns)
COL_Y = "y"           # float: spatial y coordinate (microns)
COL_Z = "z"           # float: spatial z coordinate (microns, optional)
COL_GENE = "gene"      # str:   gene or feature identifier
COL_CELL_ID = "cell_id"  # str:   cell identifier (can be empty/NaN)
COL_FOV = "fov"        # int:   field-of-view index
COL_CELLCOMP = "CellComp"  # str:   cell compartment (Nuclear/Cytoplasm/Unknown)
COL_QV = "qv"          # float: quality value (optional)

REQUIRED_CANONICAL_COLUMNS = {COL_X, COL_Y, COL_GENE}
OPTIONAL_CANONICAL_COLUMNS = {COL_CELL_ID, COL_FOV, COL_CELLCOMP, COL_QV, COL_Z}

# ── Legacy → canonical column aliases ────────────────────────────────
# For backward compatibility, step modules can use :func:`resolve_col`
# to accept either naming scheme.  Phase 2 removes legacy aliases.

_LEGACY_ALIASES: dict[str, list[str]] = {
    COL_X:        ["x_global_px", "x_location"],
    COL_Y:        ["y_global_px", "y_location"],
    COL_GENE:     ["target", "feature_name", "geneID"],
    COL_CELL_ID:  ["cell", "cell_id"],
    COL_FOV:      ["fov", "fov_name"],
    COL_CELLCOMP: ["CellComp"],
    COL_QV:       ["qv"],
}


def resolve_col(df_columns: "pd.Index | set[str]", canonical: str) -> str | None:
    """Return the actual column name in *df_columns* matching *canonical*.

    Checks the canonical name first, then legacy aliases.  Returns
    ``None`` if no match is found.

    >>> resolve_col({"gene", "x", "y"}, "gene")
    'gene'
    >>> resolve_col({"target", "x_global_px"}, "gene")
    'target'
    >>> resolve_col({"x", "y"}, "cell_id")
    None
    """
    if canonical in df_columns:
        return canonical
    for alias in _LEGACY_ALIASES.get(canonical, []):
        if alias in df_columns:
            return alias
    return None


def resolve_col_strict(df_columns: "pd.Index | set[str]", canonical: str) -> str:
    """Like :func:`resolve_col` but raises ``KeyError`` if not found."""
    col = resolve_col(df_columns, canonical)
    if col is None:
        aliases = [canonical] + _LEGACY_ALIASES.get(canonical, [])
        raise KeyError(
            f"Required column '{canonical}' not found. "
            f"Accepted names: {aliases}. Columns present: {sorted(df_columns)}"
        )
    return col

# ── SpatialData component keys ───────────────────────────────────────

# Points layer
KEY_RAW_TRANSCRIPTS = "raw_transcripts"
KEY_MAIN_TRANSCRIPTS = "main_transcripts"

# Shapes layer
KEY_PROVIDED_BOUNDARIES = "provided_boundaries"
KEY_CELLPOSE_BOUNDARIES = "cellpose_boundaries"
KEY_STARDIST_BOUNDARIES = "stardist_boundaries"
KEY_BAYSOR_BOUNDARIES = "baysor_boundaries"
KEY_PROSEG_BOUNDARIES = "proseg_boundaries"
KEY_COMSEG_BOUNDARIES = "comseg_boundaries"
KEY_IMAGE_PATCHES = "image_patches"
KEY_TRANSCRIPT_PATCHES = "transcript_patches"

# Tables layer
KEY_MAIN_TABLE = "main_table"
KEY_REFERENCE_TABLE = "reference_table"

# Images layer
KEY_MORPHOLOGY_IMAGE = "morphology_image"
KEY_HE_IMAGE = "he_image"

# ── SpatialData attrs keys ──────────────────────────────────────────

ATTRS_PLATFORM = "platform"
ATTRS_RAW_TRANSCRIPTS_KEY = "raw_transcripts_key"
ATTRS_MAIN_TRANSCRIPTS_KEY = "main_transcripts_key"
ATTRS_MAIN_BOUNDARIES_KEY = "main_boundaries_key"
ATTRS_MAIN_TABLE_KEY = "main_table_key"
ATTRS_CELL_ID_EXISTS = "cell_id_exists"
ATTRS_CELL_ID_COLUMN = "cell_id_column"
ATTRS_CELL_SEGMENTATION_IMAGE = "cell_segmentation_image"
ATTRS_TISSUE_SEGMENTATION_IMAGE = "tissue_segmentation_image"
ATTRS_INGESTION_SUMMARY = "ingestion_summary"

# ── Pipeline step names ─────────────────────────────────────────────

STEP_DENOISE = "denoise"
STEP_SEGMENTATION = "segmentation"
STEP_AGGREGATION = "aggregation"
STEP_CLUSTERING = "clustering"
STEP_ANNOTATION = "annotation"
STEP_SPATIAL_ANALYSIS = "spatial_analysis"
STEP_SUBCELLULAR_ANALYSIS = "subcellular_analysis"
STEP_SPATIAL_DOMAIN = "spatial_domain"
STEP_SUBCELLULAR_SPATIAL_DOMAIN = "subcellular_spatial_domain"
STEP_ANALYSIS = "analysis"
