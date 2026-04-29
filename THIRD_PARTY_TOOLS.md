# Third-Party Tool References

The SubCellSpace repository is intended to remain lightweight for GitHub backup and collaboration.
Large local datasets and full third-party tool source trees are kept out of version control.

## Referenced tools

- SCRIN (Subcellular co-localized RNA interaction network): https://github.com/xryanglab/SCRIN
- Sopa (SpatialData-based spatial omics pipeline): https://github.com/prism-oncology/sopa
- spARC (Spatial Affinity-Graph Recovery of Counts): https://github.com/KrishnaswamyLab/sparc
- cellpose (cell and nucleus segmentation with superhuman generalization): https://github.com/MouseLand/cellpose
- Baysor (Bayesian segmentation of imaging-based spatial transcriptomics data): https://github.com/kharchenkolab/Baysor
- Proseg (Probabilistic cell segmentation for in situ spatial transcriptomics): https://github.com/dcjones/proseg
- BayesSpace (Bayesian model for clustering and enhancing the resolution of spatial gene expression experiments): https://github.com/edward130603/BayesSpace
- STAGATE (Adaptive Graph Attention Auto-encoder for Spatial Domain Identification of Spatial Transcriptomics): https://github.com/RucDongLab/STAGATE
- SpaGCN (spatial graph convolutional network): https://github.com/jianhuupenn/SpaGCN
- GraphST (Spatially informed clustering, integration, and deconvolution of spatial transcriptomics): https://github.com/JinmiaoChenLab/GraphST
- BANKSY (spatial clustering): https://github.com/prabhakarlab/BANKSY
- PhenoGraph (Subpopulation detection in high-dimensional single-cell data): https://github.com/jacoblevine/PhenoGraph
- scVI (Deep probabilistic analysis of single-cell and spatial omics data): https://github.com/scverse/scvi-tools
- CellTypist (A tool for semi-automatic cell type classification): https://github.com/Teichlab/CellTypist
- scArches (Reference mapping for single-cell genomics): https://github.com/theislab/scarches
- TOSICA (Transformer for One-Stop Interpretable Cell-type Annotation): https://github.com/JackieHanLab/TOSICA

## Local usage recommendation

1. Keep cloned tool repositories under local `tools/` for development experiments.
2. Keep large raw/intermediate files under local `data/` and `outputs/`.
3. Commit only SubCellSpace source code, configs, and lightweight documentation.
