# SubCellSpace

成像型空间转录组（CosMx / Xenium / MERFISH）**GEO 数据库**的本地整理工具：登记、完整性检查、数据补全，
并为每个样本生成细胞水平的 Xenium 风格报告，最终发布为静态网站。

细胞水平的分析（转录本归属、聚合、预处理）**移植自 [SOPA](https://github.com/gustaveroussy/sopa)**（BSD-3，
代码在 `src/analysis/`，不依赖 sopa 包），本项目不再开发分析方法。

## 组成

| 部分 | 位置 | 作用 |
|------|------|------|
| GEO 登记表 | `data/{cosmx,xenium,merfish}_geo.csv` | 每个 GSM 一行：状态、GEO 元数据、组织/疾病、文件、统计 |
| GEO 工具链 | `src/geo/` | GSM 展开、下载、解压、元数据补全、格式识别 |
| touch | `src/touch.py` | 样本目录的文件完整性检查（默认只读） |
| 读取器 | `src/io/` | 把 GEO 上不完整、不标准的文件读成统一的样本结构 |
| 补全 + SOPA 模式 | `src/complete.py`、`src/analysis/` | 按规则补出细胞×基因表；移植自 SOPA（去掉图像依赖）的分配与预处理 |
| 报告 | `src/html_report.py` | Xenium 风格的交互式 HTML 报告 |
| 浏览器 | `frontend/` | 登记表的静态浏览页面 |

## 使用

```bash
conda env create -f environment.yml && conda activate subcellspace
pip install -e ".[dev]"

subcellspace lookup GSE234713          # 查询登记表
subcellspace touch <样本目录>           # 完整性检查
subcellspace process <样本目录> -o <输出目录>   # 读取 → 补全 → 预处理 → h5ad + 统计 + 报告
subcellspace stats <样本目录>           # 流式统计

python scripts/export_frontend_json.py  # 登记表 → frontend/public/*.json
cd frontend && npm install && npm run dev

bash scripts/fetch_testdata.sh          # 拉取 3 个最小的真实样本供测试（需集群网络）
ruff check src scripts tests && pytest -q
```

集群上的批量运行（Slurm 作业数组、conda-pack 环境）见 [AGENTS.md](AGENTS.md) §5。

项目进度、决定和集群约定见 [AGENTS.md](AGENTS.md)。
