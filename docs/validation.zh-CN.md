# 验证状态

最近一次真实站点测试：2026-08-20。这是一份有日期的冒烟测试，不是永久可用性承诺。出版社网页、机构订阅权限和反自动化策略都可能独立变化。

## 测试口径

- 27/27 项离线测试通过，覆盖 DOI 处理、出版社路由、页面状态识别、PDF 核验、断点清单、会话额度分类和批量转换结果归档。
- 使用真实 DOI 页面测试了 21 个代表性出版社 profile。
- 只有 PDF 结构可解析、不是补充材料，并且 DOI 或高置信标题与请求一致，才记为 `success`。
- 测试使用操作者已有的合法访问权限；仓库不包含账号、Cookie、学校配置、浏览器 profile 或下载所得 PDF。

## 真实站点矩阵

| Profile | 样本 DOI | 结果 | 成功路线 | 证据或阻塞原因 |
|---|---|---|---|---|
| ACM | `10.1145/3448016.3452834` | 成功 | CloakBrowser | DOI 匹配，13 页 |
| ACS | `10.1021/acs.est.6c00693` | 成功 | CloakBrowser | DOI 匹配，22 页 |
| AIP | `10.1063/5.0237567` | 需要验证 | — | Cloudflare 标记 |
| AMS | `10.1175/aies-d-23-0093.1` | 成功 | CloakBrowser | DOI 匹配，19 页 |
| Annual Reviews | `10.1146/annurev-phyto-011325-012824` | 未定 | — | CloakBrowser 套餐会话额度 |
| APS | `10.1103/PhysRevLett.128.161102` | 需要验证 | — | Cloudflare 标记 |
| Copernicus | `10.5194/acp-24-1-2024` | 成功 | 出版社 HTTP | DOI 匹配，21 页 |
| Elsevier | `10.1016/j.watres.2024.121507` | 成功 | 出版社官方 API | DOI 匹配，11 页 |
| Frontiers | `10.3389/fmicb.2026.1831710` | 成功 | 出版社 HTTP | DOI 匹配，14 页 |
| IEEE | `10.1109/JSTQE.2026.3687110` | 成功 | 出版社 HTTP | DOI 匹配，10 页 |
| IOP | `10.1088/1361-648X/ae72dd` | 需要验证 | — | hCaptcha 标记 |
| MDPI | `10.3390/foods10081757` | 未定 | — | CloakBrowser 套餐会话额度 |
| Oxford Academic | `10.1093/nar/gkaa892` | 需要验证 | — | Cloudflare 标记 |
| PLOS | `10.1371/journal.pone.0000001` | 成功 | CloakBrowser | DOI 匹配，11 页 |
| PNAS | `10.1073/pnas.2309123120` | 未定 | — | CloakBrowser 套餐会话额度 |
| Royal Society | `10.1098/rsos.150470` | 未定 | — | CloakBrowser 套餐会话额度 |
| RSC | `10.1039/d5cp03829d` | 需要验证 | — | Cloudflare 标记 |
| Science | `10.1126/sciadv.adp3964` | 未定 | — | CloakBrowser 套餐会话额度 |
| Springer Nature | `10.1038/s41586-020-2649-2` | 成功 | 出版社 HTTP | DOI 匹配，6 页 |
| Wiley | `10.1002/adfm.202525261` | 未定 | — | CloakBrowser 套餐会话额度 |
| World Scientific | `10.1142/S0218194026500348` | 需要验证 | — | reCAPTCHA 标记 |

本次观察结果：9 篇 PDF 下载并严格核验成功，6 个站点正确识别出验证页面，另有 6 个站点因本地 CloakBrowser 套餐会话额度而无法下结论。ASME、SAGE、Taylor & Francis、Cambridge 和 Emerald 已有路由与检测测试，但未进入这次真实矩阵。

识别出验证页面表示安全停止，不代表已经绕过 CAPTCHA。交互模式只用于用户明确选择并亲自操作的接管流程。

## MinerU 状态

批量封装与结果归档已通过合成 MinerU 输出树的离线测试。本次没有安装可选的本地 MinerU 运行时及模型，因此不声称完成了真实本地模型转换。云端转换会上传 PDF，必须另行明确同意，所以本次未使用。
