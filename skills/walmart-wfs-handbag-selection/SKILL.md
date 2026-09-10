---
name: walmart-wfs-handbag-selection
description: 编排 Amazon 到 Walmart US/CA 的售前女包找款、市场缺口和每日候选。用于 WFS女包选品、每日30款、Amazon热卖转Walmart或双池关键词；不用于1688共享池、FBM已出单动作、T1审批、采购到货、装箱、Shipment ID或Listing上传表。
---

# Walmart WFS 女包选品

## 定位

这是选品方法与运行编排 Skill。复用外部 `lc-amazon-data-crawl`、现有 WFS 控制器、运行账本、飞书能力和既有运营自动任务。运行数据和密钥必须位于 Skill 目录外。

开始前读取 [selection-policy.md](references/selection-policy.md) 和 [daily-30-routing.md](references/daily-30-routing.md)。涉及字段或迁移时，再读取 [data-schema.md](references/data-schema.md) 或 [mac-mini-migration.md](references/mac-mini-migration.md)。

## 入口

所有命令使用外部配置：

```bash
python3 scripts/wfs_skillctl.py <command> --config /path/to/wfs-local.json
```

支持：

- `doctor`：只读检查环境、路径、固定门槛、关键词库和安全边界。
- `status`：只读盘点关键词、账本、最近试跑、报告哈希和阻塞原因。
- `smoke`：仅在运营未暂停时运行技术试跑。
- `validate-readonly`：运营暂停期间唯一允许的验证入口；仅工作日北京时间 09:45–13:00，每日一次，强制 dry-run。
- `daily`：门禁通过后调用现有控制器正式日跑；支持 `--dry-run`。
- `feishu-test`：默认只 dry-run；只有显式 `--confirm-send` 才发送带“WFS测试”的成功试跑报告。

Mac mini缺少Node、原项目或飞书权限时，改用零依赖便携入口：

```bash
python3 scripts/portable_batch.py init --output "$HOME/Documents/wfs-daily-YYYYMMDD" --date YYYY-MM-DD
python3 scripts/portable_batch.py inspect --batch-dir "$HOME/Documents/wfs-daily-YYYYMMDD"
python3 scripts/portable_batch.py check --batch-dir "$HOME/Documents/wfs-daily-YYYYMMDD"
python3 scripts/portable_batch.py pack --batch-dir "$HOME/Documents/wfs-daily-YYYYMMDD"
```

便携入口只依赖Python标准库，生成CSV、图片目录、校验报告和ZIP；不连接飞书。

首次配置从 [wfs-local.example.json](assets/config/wfs-local.example.json) 复制到外部运行目录。关键词模板见 [keywords-master.csv](assets/inputs/keywords-master.csv)，迁移时优先保留已有主表和历史状态，不得用模板覆盖账本。

## 执行流程

0. 外部运行配置必须显式包含 `operations_paused`。为 `true` 时阻止 `smoke`、`daily`、`feishu-test` 和所有运营任务，只允许 `doctor`、`status` 及受时间/幂等门禁保护的 `validate-readonly`。只有用户原文明确说“恢复运营监督”后，才可把配置改为 `false`；不得从近义表达推断恢复。

1. 先运行 `doctor` 和 `status`，报告真实完成情况，不把方案当作已实现。
2. `doctor` 通过后再运行 `smoke`。登录、验证码、卖家精灵字段缺失或中断均视为 `BLOCKED`。
3. 技术试跑必须完成6页，两个词均有 ASIN，价格、评论、30天销量覆盖率均不低于80%。
4. 同日重复试跑，确认不重复写商品和投递。
5. 仅在技术试跑成功、至少60个验证词且每池至少30个、10个试跑词均通过指标门禁后运行 `daily`。
6. 只投递新增商品和关键变化；零新增只输出一行回执。
7. 现有自动任务只能在全部 Mac Mini 验收完成后引用 `daily`，不得创建重复任务。
8. 正式日跑最终保存30个独立产品组，主流15款、风格15款；30款全部作为FBM候选，最多4款额外标记为沃美WFS候选。
9. 每日30款结果不完整时保持 `PENDING`；smoke、pilot、部分抓取和0候选不得伪装成正式 `DAILY/SUCCESS`。
10. 关键词和商品必须有明确女包手袋意图。无明确女包意图、仅含泛化 `bag`、或属于背包/午餐包/电脑包/旅行收纳袋的词与商品一律排除。

## 失败规则

- `BLOCKED` 批次不推进关键词冷却，不提升正式候选，不发送部分候选。
- 缺少历史数据库或报告哈希时禁止正式日跑，先完成迁移或明确恢复方案。
- 美国与加拿大需求独立判断；美国缺口不能替代加拿大核验。
- 初步缺口和已确认机会必须分开统计。
- 便携结果包只有通过30款、15/15、FBM门禁和WFS上限检查后才允许打包交回。

## 禁止行为

- 不自动创建 Listing、采购、发 WFS、修改商品状态或平台数据。
- 不复制或重新实现 Amazon 抓取器。
- 不在 Skill 中保存 Cookie、Chrome 用户目录、账号、密钥、用户ID、历史 ASIN、运行日期、日志或报告。
- 不自动更改月销150–600、售价至少25美元等核心门槛。
- 不直接删除疑似同款；标记 `POSSIBLE_DUPLICATE` 后人工复核。
- 不启用或新建正式定时任务，除非用户在验收完成后明确确认。
- 不把Skill内的流程说明当成账号授权、真实数据或已完成选品。
