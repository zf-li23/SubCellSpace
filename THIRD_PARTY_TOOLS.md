# Third-Party Tool References

The SubCellSpace repository is intended to remain lightweight for GitHub backup and collaboration.
Large local datasets and full third-party tool source trees are kept out of version control.

## Referenced tools

- Sopa (SpatialData-based spatial omics pipeline): https://github.com/prism-oncology/sopa
- SCRIN (Subcellular co-localized RNA interaction network): https://github.com/xryanglab/SCRIN

## Local usage recommendation

1. Keep cloned tool repositories under local `tools/` for development experiments.
2. Keep large raw/intermediate files under local `data/` and `outputs/`.
3. Commit only SubCellSpace source code, configs, and lightweight documentation.
