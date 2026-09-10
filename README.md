# Vicky Codex Skills

这是 Vicky 自建与星河电商工作流的公开只读副本，包含 **44 个主 Skill + 2 个显式兼容入口**。本机 `~/.codex/skills` 是维护源；本仓库由人工运行同步工具、审计并确认后更新，不设自动定时推送。

## 总入口

优先使用 `$vicky-ecommerce-router`。它只判断当前任务阶段，并转交一个主 Skill；显式写出的 `$skill-name` 永远优先。

主要分流：

- Amazon 选品：普通选品、精铺女包、Sorftime 十方向、年度监督、1688 闭环和原子数据方法互斥。
- 星河图片：参考图二创、完整 Amazon 套系、详情模块、单张营销创意和普通商品编辑互斥。
- 星河视频：参考视频复刻、带货演示和 15 秒精品宣传片互斥；只有“商品视频”时先问一次目标。
- WFS：售前候选、1688 共享池、FBM 已出单动作、T1/采购/装箱/Shipment ID 和 Listing 工作簿按阶段分流。

详细规则见 [`skills/vicky-ecommerce-router/references/routes.md`](skills/vicky-ecommerce-router/references/routes.md)。

## 分类

- Amazon 选品：`amazon-*selection*`、`amazon-product-selection`、`amazon-handbag-selection-orchestrator`
- 库存/竞品/财务：`amazon-inventory-*`、`amazon-competitive-repricing`、`amazon-competitor-monitor`、`financial-analysis`
- 1688 与渠道闭环：`lc-1688-*`、`lc-channel-output-dispatcher`、`lc-feishu-selection-sync`、`lc-google-risk-screen`
- Walmart/WFS：`walmart-*`、`lc-fbm-*`、`lc-walmart-wfs-shipping-manifest`
- 星河：全部 `xinghe-*`
- 兼容入口：`amazon-finance-profit-analysis`、`lc-product-selection-orchestrator`

完整清单以 [`skill-sources.json`](skill-sources.json) 为准。

## 调用名迁移

- 原中文调用名 `星河跨境电商选品自动化` 已迁移为 `$xinghe-crossborder-product-selection`，UI 显示名仍为“星河跨境电商选品自动化”。
- `$amazon-finance-profit-analysis` 仅显式转交 `$financial-analysis`。
- `$lc-product-selection-orchestrator` 仅显式转交 `$lc-1688-channel-closure`。

## 安装

安装全部 Skill：

```bash
git clone https://github.com/vickyck428-ux/vicky-codex-skills.git
cp -R vicky-codex-skills/skills/* "${CODEX_HOME:-$HOME/.codex}/skills/"
```

也可以只复制一个需要的目录。安装后重新启动 Codex 或刷新 Skill 列表。

## 外部依赖

本仓库不复制老陈 Skill、飞书插件、账号配置、密钥或业务数据库。部分 Skill 需要另行安装或配置：

- `lc-amazon-data-crawl`、`lc-amazon-listing-asin`、`lc_amazon_market_research`、`lark-base`
- `closurectl`、`selectionctl`、`inventory-ai-runner`、`shipping-orchestrator`、`1688-walmart-tool`
- Sorftime MCP、星河/火山引擎图片或视频运行环境
- 本地模板、费率卡、运行 SQLite、飞书配置和浏览器资料

路径通过示例配置或环境变量提供，例如 `INVENTORY_AI_RUNNER`、`SKU_COST_REGISTRY`、`SHIPPING_ORCHESTRATOR_ROOT`、`WALMART_1688_TOOL_ROOT`、`COURSE_KB_ROOT`。缺少依赖时应返回 `BLOCKED` 或 `NEEDS DATA`，不得伪造完成。

## 安全边界

- 图片上传、成本主档、价格、库存、采购、Listing、FBA/WFS 货件和飞书生产写入均需要当次、目标匹配的明确确认。
- 竞品有效价为 `displayed_price + shipping`；Coupon 只记录变化，不再次从显示价扣除。
- Pencil case 不进入销售、利润、成功率、女包库存、选品或补货指标，只能进入独立“历史遗留清退”。
- WFS 默认 `operations_paused=true`；暂停时只允许工作日北京时间 09:45–13:00 每日一次只读验证。只有用户明确说“恢复运营监督”才可恢复。

## 同步与验证

```bash
python3 scripts/sync_public_skills.py --dry-run
python3 scripts/sync_public_skills.py --apply
python3 scripts/validate_public_repo.py
```

同步工具使用固定白名单，并排除本地配置、密钥、Cookie、浏览器资料、数据库、缓存、日志、报告、备份和编译产物。验证命中个人绝对路径、秘密、高风险文件或大文件时会失败。真正公开推送前仍需人工检查暂存文件和提交哈希。

## Copyright

Copyright © 2026 vc. All rights reserved.

本仓库未附开源许可证。公开可见和可下载不代表授予复制、修改、再发布或商业使用许可；法律另有规定的除外。
