"""
SubCellSpace GEO 工具模块
=========================

可复用的 GEO 数据操作工具集，不整合入主管线。
涵盖：GEO API 查询、数据下载、tar 解压与归类、格式检测。

使用示例:
    from src.geo.api import query_gsms
    gsms = query_gsms("GSE234713")
    
    from src.geo.download import download_gse_tar
    download_gse_tar("GSE234713", "/data/downloads/")
    
    from src.geo.extract import extract_tar_to_gsm_dirs
    extract_tar_to_gsm_dirs("/data/GSE234713_RAW.tar", "/data/GSE234713/")
    
    from src.geo.format import detect_format
    fmt = detect_format("/data/GSE234713/GSM7473682/")
"""

__version__ = "0.1.0"
