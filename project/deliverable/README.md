# 汇总文档（PDF）

- 源文件：`deliverable/report.tex`
- 产物：`deliverable/report.pdf`

## 构建（macOS）

1. 安装 LaTeX（推荐 MacTeX 或 TeX Live），确保有 `xelatex`（可选 `latexmk`）。
2. 在项目根目录运行：

```bash
bash deliverable/build.sh
```

如果你更习惯手动编译：

```bash
cd deliverable
latexmk -xelatex report.tex
```

## 篇幅说明

- 主体内容控制为“需求分析 + 模块与关键 API + 数据库设计”。
- API 作为附录给出“精简版关键接口”，完整接口细节仍保留在仓库的 `docs/api文档.md`。
