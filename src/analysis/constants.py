"""Constants taken from SOPA 2.2.11 (BSD-3, see SOPA_LICENSE)."""

# sopa/_settings.py — Settings.gene_exclude_pattern: control / blank / negative probes and placeholders,
# matched case-insensitively against gene names and excluded from counts.
GENE_EXCLUDE_PATTERN = "nan|<NA>|.*control.*|blank.*|antisense.*|unassigned.*|deprecated.*|intergenic.*|false.*|neg.*"

# sopa/io/reader/cosmx.py — COSMX_PIXEL_SIZE: µm per CosMx pixel.
COSMX_PIXEL_SIZE = 0.120280945
