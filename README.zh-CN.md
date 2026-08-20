# 论文 PDF 静默下载 Skill

[English](README.md)

这是一个独立、静默优先的 Agent Skill 与 Python CLI：下载你有权访问的论文 PDF，核验文件确实是目标论文主文，并可选用 MinerU 将已验证论文库批量转换为 Markdown。

本项目不包含、也不调用 InstSci。它是独立的静默下载器；出版社覆盖、分层状态检测和严格核验思路参考了包括 [InstSci](https://github.com/Rimagination/instsci) 在内的公开学术获取工具。

## 核心特点

- 默认静默：CloakBrowser 无窗口运行，每个出版社使用独立持久 profile。
- 严格成功标准：仅有 `%PDF-` 不算成功；必须解析 PDF、排除补充材料，并核对 DOI 或论文标题。
- 主流站点覆盖：ACS、ACM、APS、Annual Reviews、ASME、Frontiers、Wiley、Elsevier/ScienceDirect、IEEE、IOP、RSC、Springer Nature、World Scientific、AIP、AMS、Copernicus、MDPI、Oxford Academic、PLOS、PNAS、Royal Society、Science、SAGE、Taylor & Francis、Cambridge、Emerald。
- 可恢复批处理：每个 DOI 有独立 `manifest.json`，批次根目录有 JSON/CSV 总清单。
- MinerU 本地优先：默认在本机离线转换；必须同时指定 `--mode api --allow-upload` 才允许上传到 MinerU Open API。
- 两个可组合 Skill：只下载 PDF 时无需安装 MinerU，转换 Skill 可单独使用。

## 授权与安全边界

仅用于开放获取论文，或你自己的校园、图书馆、机构订阅和出版社 API 权限覆盖的内容。请遵守出版社条款，不要重新分发订阅 PDF。

默认静默模式不会自动操作验证码。持续挑战会被记录为 `challenge_required`、`auth_required` 或 `blocked`，任务继续处理下一篇。只有显式添加 `--interactive`，才会打开持久浏览器，由用户本人完成 CAPTCHA、SSO 或 OTP。

## 安装

需要 Python 3.11 或更高版本。

```bash
git clone https://github.com/wxt18757928900-lgtm/paper-pdf-download-skill.git
cd paper-pdf-download-skill
python -m pip install -e ".[browser]"
cloakbrowser install
```

仓库发布后可使用隔离安装：

```bash
pipx install "paper-pdf-download-skill[browser] @ git+https://github.com/wxt18757928900-lgtm/paper-pdf-download-skill.git"
```

使用 Agent Skills 安装器安装 [`skills/`](skills/) 下的两个 Skill，或复制到你的 Agent Skill 目录：

```bash
npx skills add wxt18757928900-lgtm/paper-pdf-download-skill
```

MinerU 是可选依赖。本地私密转换请按 [MinerU 官方安装文档](https://github.com/opendatalab/MinerU/blob/master/docs/zh/quick_start/index.md) 安装，常见命令是：

```bash
python -m pip install -U "mineru[all]"
```

## 快速使用

检查环境且不显示密钥：

```bash
paper-pdf doctor
```

静默批量下载：

```bash
paper-pdf download 10.1038/s41586-020-2649-2 10.1109/5.771073 --output ./library
paper-pdf download --file ./dois.txt --output ./library --workers 1
```

`--workers` 表示并行出版社会话数，不是同一 profile 中的标签页数。除非 CloakBrowser 许可证和机构访问规则允许多个会话，否则保持默认值 `1`。

需要人工接管时才显式开启：

```bash
paper-pdf download --file ./retry.txt --output ./library --interactive
```

下载完成后，用一次 MinerU 批处理转换全部已验证 PDF：

```bash
paper-pdf run --file ./dois.txt --output ./library --mode local --backend pipeline
```

转换已有论文库：

```bash
paper-pdf convert ./library --mode local
```

云 API 从不自动启用：

```bash
paper-pdf convert ./library --mode api --allow-upload
```

## 输出结构与成功标准

```text
library/
├── manifest.json
├── manifest.csv
└── ieee/
    └── 10.1109_5.771073-<hash>/
        ├── paper.pdf
        ├── paper.md                 # 请求转换后才出现
        ├── assets/mineru/           # 图片、表格及 MinerU 其他资源
        └── manifest.json
```

无法核验的候选只保存为 `unverified.pdf`，绝不会提升为 `paper.pdf`。Markdown 转换失败时保留已验证 PDF，并在清单中记录部分完成。

## 配置与隐私

复制 [`paper-pdf.example.toml`](paper-pdf.example.toml) 到私有位置，通过 `paper-pdf --config /path/to/config.toml ...` 或 `PAPER_PDF_CONFIG` 使用。API key 只从环境变量读取，不会写入清单。

学校、校园 IP、VPN 路由、账号、Cookie、浏览器 profile 和本机路径只能写进不提交 Git 的本地配置。公开仓库不内置清华或任何学校预设。

详细说明见[出版社支持](skills/paper-pdf-download/references/publisher-support.md)、[下载配置](skills/paper-pdf-download/references/configuration.md)和[MinerU 转换](skills/paper-pdf-to-markdown/references/mineru.md)。

带日期的[真实站点验证矩阵](docs/validation.zh-CN.md)会严格区分：已核验下载、验证页面、工具会话额度，以及尚未实测的 profile。离线 CI 测试通过不等于真实出版社下载成功。

## 开发

CI 不访问真实出版社，测试全部使用合成 PDF 和离线 HTML。

```bash
python -m pip install -e ".[dev]"
pytest
ruff check src tests scripts
python -m build
```

本项目使用 [MIT 许可证](LICENSE)。外部工具保留各自许可证，参见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
