# SubCellSpace Frontend

React + TypeScript + Vite 数据浏览器，**不含分析业务逻辑**。

## 快速启动

```bash
cd frontend
npm install
npm run dev        # 自动启动后端（需 conda activate subcellspace）
```

前端监听 `http://127.0.0.1:5173`，API 代理至 `http://127.0.0.1:8000`。

## 页面

| 路由 | 功能 | 数据源 |
|------|------|--------|
| `/` | HomePage — 导航卡片与概述 | 静态 |
| `/report` / `/report/:runName` | ReportPage — 管线结果可视化 | API `/api/reports/{run}` |
| `/browser` | DataBrowser — 数据集浏览 | `datasets.json` |
| `/editor` | DataEditor — 数据集 CRUD（仅 dev 模式） | API `/api/db/*` |
| `/benchmark` | BenchmarkPage — 基准比较 | API `/api/benchmarks/{run}` |

## 构建

```bash
npm run build      # → dist/
```

## 启动脚本

`scripts/dev.mjs` 自动检测 8000 端口，后端未运行时自动拉起。

关键依赖：`react-router-dom`、`@tanstack/react-query`。
