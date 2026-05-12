# ── SubCellSpace Database Schema ─────────────────────────────────────
"""Column definitions, categories, and SQL DDL for datasets.db."""

from enum import StrEnum

# ── Platform enum ────────────────────────────────────────────────────

class Platform(StrEnum):
    COSMX = "CosMx"
    XENIUM = "Xenium"
    MERFISH = "MERFISH"


# ── Column categories (display grouping) ─────────────────────────────

COLUMN_CATEGORIES = [
    {
        "key": "identity",
        "label_zh": "标识与归属",
        "label_en": "Identity",
        "columns": [
            "id", "project_id", "platform",
            "name_zh", "name_en", "record_type", "merged_from_ids",
        ],
    },
    {
        "key": "provenance",
        "label_zh": "出版与溯源",
        "label_en": "Provenance",
        "columns": [
            "project_url", "download_url",
            "publication_doi", "data_source",
        ],
    },
    {
        "key": "biological",
        "label_zh": "生物学上下文",
        "label_en": "Biological Context",
        "columns": ["species", "tissue", "disease_state"],
    },
    {
        "key": "technical",
        "label_zh": "技术与规模",
        "label_en": "Technical & Scale",
        "columns": [
            "spatial_resolution_um", "gene_panel_size",
            "estimated_cell_count", "data_size_bytes",
            "data_size_display", "status",
        ],
    },
    {
        "key": "storage",
        "label_zh": "本地存储路径",
        "label_en": "Local Storage",
        "columns": ["local_path", "file_name"],
    },
]

# ── Column metadata ──────────────────────────────────────────────────

COLUMNS = [
    # Identity
    {"name": "id",                 "type": "INTEGER", "nullable": False, "category": "identity",
     "label_zh": "ID",             "label_en": "ID",
     "description_zh": "全局唯一数据集 ID", "description_en": "Globally unique dataset ID"},
    {"name": "project_id",         "type": "INTEGER", "nullable": False, "category": "identity",
     "label_zh": "项目 ID",        "label_en": "Project ID",
     "description_zh": "所属项目 ID，同项目数据集共享", "description_en": "Project ID shared by datasets in the same project"},
    {"name": "platform",           "type": "TEXT",    "nullable": False, "category": "identity",
     "label_zh": "技术平台",       "label_en": "Platform",
     "description_zh": "CosMx / Xenium / MERFISH", "description_en": "CosMx / Xenium / MERFISH"},
    {"name": "name_zh",            "type": "TEXT",    "nullable": False, "category": "identity",
     "label_zh": "中文名称",       "label_en": "Name (ZH)",
     "description_zh": "数据集中文名称（已去除技术前缀）", "description_en": "Dataset name in Chinese (tech prefix removed)"},
    {"name": "name_en",            "type": "TEXT",    "nullable": True,  "category": "identity",
     "label_zh": "英文名称",       "label_en": "Name (EN)",
     "description_zh": "数据集英文名称（已去除技术前缀）", "description_en": "Dataset name in English (tech prefix removed)"},
    {"name": "record_type",        "type": "TEXT",    "nullable": False, "category": "identity",
     "label_zh": "记录类型",       "label_en": "Record Type",
     "description_zh": "Standard / Merged / Raw_Fragment", "description_en": "Standard / Merged / Raw_Fragment"},
    {"name": "merged_from_ids",    "type": "TEXT",    "nullable": True,  "category": "identity",
     "label_zh": "合并来源 ID",    "label_en": "Merged From IDs",
     "description_zh": "JSON 数组格式的来源数据集 ID 列表", "description_en": "Source dataset IDs as JSON array"},

    # Provenance
    {"name": "project_url",        "type": "TEXT",    "nullable": True,  "category": "provenance",
     "label_zh": "项目链接",       "label_en": "Project URL",
     "description_zh": "浏览器可打开的数据集说明页面", "description_en": "Web page describing the project/dataset"},
    {"name": "download_url",       "type": "TEXT",    "nullable": True,  "category": "provenance",
     "label_zh": "下载链接",       "label_en": "Download URL",
     "description_zh": "wget 可直接下载源数据的链接", "description_en": "Direct download link for source data"},
    {"name": "publication_doi",    "type": "TEXT",    "nullable": True,  "category": "provenance",
     "label_zh": "出版 DOI",       "label_en": "Publication DOI",
     "description_zh": "相关论文的 DOI", "description_en": "DOI of the associated publication"},
    {"name": "data_source",        "type": "TEXT",    "nullable": False, "category": "provenance",
     "label_zh": "数据来源方",     "label_en": "Data Source",
     "description_zh": "Nanostring / 10x Genomics / Vizgen / GEO", "description_en": "Nanostring / 10x Genomics / Vizgen / GEO"},

    # Biological Context
    {"name": "species",            "type": "TEXT",    "nullable": False, "category": "biological",
     "label_zh": "物种",           "label_en": "Species",
     "description_zh": "Homo sapiens / Mus musculus", "description_en": "Homo sapiens / Mus musculus"},
    {"name": "tissue",             "type": "TEXT",    "nullable": False, "category": "biological",
     "label_zh": "组织/器官",      "label_en": "Tissue/Organ",
     "description_zh": "组织或器官名称", "description_en": "Tissue or organ name"},
    {"name": "disease_state",      "type": "TEXT",    "nullable": True,  "category": "biological",
     "label_zh": "疾病状态",       "label_en": "Disease State",
     "description_zh": "Non-diseased / Cancer 等", "description_en": "Non-diseased / Cancer etc."},

    # Technical & Scale
    {"name": "spatial_resolution_um", "type": "REAL", "nullable": True,  "category": "technical",
     "label_zh": "空间分辨率 (μm)",  "label_en": "Spatial Resolution (μm)",
     "description_zh": "空间分辨率，单位微米", "description_en": "Spatial resolution in micrometers"},
    {"name": "gene_panel_size",    "type": "INTEGER", "nullable": True,  "category": "technical",
     "label_zh": "基因 Panel 大小", "label_en": "Gene Panel Size",
     "description_zh": "Panel 中基因总数", "description_en": "Total genes in panel"},
    {"name": "estimated_cell_count", "type": "INTEGER", "nullable": True,  "category": "technical",
     "label_zh": "预估细胞数",     "label_en": "Est. Cell Count",
     "description_zh": "预估或实际细胞数量", "description_en": "Estimated or actual cell count"},
    {"name": "data_size_bytes",    "type": "INTEGER", "nullable": True,  "category": "technical",
     "label_zh": "数据大小 (字节)", "label_en": "Data Size (Bytes)",
     "description_zh": "数据大小（字节），便于排序比较", "description_en": "Data size in bytes for sorting/comparison"},
    {"name": "data_size_display",  "type": "TEXT",    "nullable": True,  "category": "technical",
     "label_zh": "数据大小",       "label_en": "Data Size",
     "description_zh": "数据大小（可读格式）", "description_en": "Data size (human-readable)"},
    {"name": "status",             "type": "TEXT",    "nullable": False, "category": "technical",
     "label_zh": "数据状态",       "label_en": "Status",
     "description_zh": "ready / pending / error", "description_en": "ready / pending / error"},

    # Local Storage
    {"name": "local_path",         "type": "TEXT",    "nullable": True,  "category": "storage",
     "label_zh": "本地路径",       "label_en": "Local Path",
     "description_zh": "实验室服务器上的数据集目录路径", "description_en": "Dataset directory path on lab server"},
    {"name": "file_name",          "type": "TEXT",    "nullable": True,  "category": "storage",
     "label_zh": "文件名",         "label_en": "File Name",
     "description_zh": "主数据文件名", "description_en": "Main data file name"},
]

# ── SQL DDL ──────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS datasets (
    id                   INTEGER PRIMARY KEY,
    project_id           INTEGER NOT NULL,
    platform             TEXT    NOT NULL,
    name_zh              TEXT    NOT NULL,
    name_en              TEXT,
    record_type          TEXT    NOT NULL,
    merged_from_ids      TEXT,

    project_url          TEXT,
    download_url         TEXT,
    publication_doi      TEXT,
    data_source          TEXT    NOT NULL,

    species              TEXT    NOT NULL,
    tissue               TEXT    NOT NULL,
    disease_state        TEXT,

    spatial_resolution_um REAL,
    gene_panel_size      INTEGER,
    estimated_cell_count INTEGER,
    data_size_bytes      INTEGER,
    data_size_display    TEXT,
    status               TEXT    NOT NULL DEFAULT 'pending',

    local_path           TEXT,
    file_name            TEXT
);

CREATE INDEX IF NOT EXISTS idx_datasets_platform ON datasets(platform);
CREATE INDEX IF NOT EXISTS idx_datasets_project_id ON datasets(project_id);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status);
"""

# ── Default column display priority (frontend initial view) ──────────
# Columns shown by default; rest are hidden behind "more info" toggle.

PRIORITY_COLUMNS = [
    "id", "platform", "name_en",
    "species", "tissue", "disease_state",
    "estimated_cell_count", "data_size_display", "status",
    "project_url", "download_url",
]