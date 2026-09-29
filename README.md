# SubCellSpace

成像型空间转录组（CosMx / Xenium / MERFISH）**GEO 数据库**的本地整理工具：登记、完整性检查、数据补全，
并为每个样本生成细胞水平的 Xenium 风格报告，最终发布为静态网站。

细胞水平的分析（转录本归属、分割、聚合、预处理）**使用 [SOPA](https://github.com/gustaveroussy/sopa)**，
本项目不再开发分析方法。

## 组成

| 部分 | 位置 | 作用 |
|------|------|------|
| GEO 登记表 | `data/{cosmx,xenium,merfish}_geo.csv` | 每个 GSM 一行：状态、GEO 元数据、组织/疾病、文件、统计 |
| GEO 工具链 | `src/geo/` | GSM 展开、下载、解压、元数据补全、格式识别 |
| touch | `src/touch.py` | 样本目录的文件完整性检查（默认只读） |
| 读取器 | `src/io/` | 把 GEO 上不完整、不标准的文件转成 SpatialData |
| 报告 | `src/html_report.py` | Xenium 风格的交互式 HTML 报告 |
| 浏览器 | `frontend/` | 登记表的静态浏览页面 |

## 使用

```bash
conda env create -f environment.yml && conda activate subcellspace
pip install -e ".[dev]"

subcellspace lookup GSE234713          # 查询登记表
subcellspace touch <样本目录>           # 完整性检查
subcellspace ingest cosmx <tx_file>     # GEO 文件 → SpatialData
subcellspace stats <样本目录>           # 流式统计

python scripts/export_frontend_json.py  # 登记表 → frontend/public/*.json
cd frontend && npm install && npm run dev

ruff check src scripts tests && pytest -q
```

项目进度、决定和集群约定见 [AGENTS.md](AGENTS.md)。
