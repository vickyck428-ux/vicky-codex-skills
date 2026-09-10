# Mac Mini 安装与迁移

## 1. 目录与依赖

建议：

- Skill：`~/.codex/skills/walmart-wfs-handbag-selection`
- 运行数据：`~/Documents/wfs-handbag-runtime`
- 外部抓取 runner：由 `lc-amazon-data-crawl/scripts/setup_runner.sh` 创建或复用，不复制本 Skill 内的爬虫。

检查 Codex、Python、Node、Chrome/Chrome for Testing、`lark-cli`、`lc-amazon-data-crawl` 和运行器。复制 `assets/config/` 下三个模板到运行目录；把控制器模板中的 `__...__` 占位符替换为 Mac Mini 本地绝对路径，再设置 `WFS_RUNNER_ROOT`、`WFS_RUNTIME_DIR`、`WFS_CRAWL_SKILL_DIR`、`WFS_FEISHU_CONFIG` 供入口配置展开。

如果Mac mini暂时没有Node、runner或飞书授权，不要阻塞整个选品工作。先使用 `scripts/portable_batch.py` 便携模式，由Codex填写标准CSV并打包交回；原运营电脑负责最终同步。便携模式只需要Python 3，不要求源电脑路径，也不保存密钥。

## 2. 迁移历史

正式迁移前停止源端 WFS 写入并备份：

- SQLite 商品、运行和投递账本；
- 当前关键词主表及验证数据；
- Walmart 核验工作文件；
- 报告哈希、断点、状态和必要的历史 JSONL/CSV。

目标端核对表记录数、最近一次 `run_id`、报告哈希及投递幂等键。不得用空库或模板覆盖已有历史。不要复制 `.venv`、Cookie、Chrome 用户目录、调试截图或缓存。

## 3. 交互式登录

由用户在 Mac Mini 完成：

1. Codex 与老陈云端授权；
2. Amazon 浏览器会话并设置美国邮编 `10001`；
3. 卖家精灵插件登录并确认数据字段可见；
4. 紫鸟中登录 Walmart US 和 CA；加拿大默认邮编 `M5V 2T6`；
5. 飞书机器人身份和 Vicky 用户身份。

验证码、MFA 或登录过期时停止运行，标记 `BLOCKED`，等待用户处理。不要迁移浏览器会话文件。

## 4. 验收顺序

1. `doctor` 检查环境和配置；`status` 核对历史。
2. 运行 `daily --dry-run`，预期在试跑未完成时安全阻塞。
3. 运行技术试跑：两个固定词各3页。
4. 验证6页完成、两个词都有ASIN，价格/评论/30天销量覆盖率各≥80%。
5. 同日重复运行，确认不重复写商品。
6. `feishu-test` 先 dry-run，再在用户确认后加 `--confirm-send`；消息必须带“WFS测试”。
7. 核对第二次相同报告不会重复发送。
8. 全部通过后，才允许让现有运营自动任务的工作日10:00分支调用 `daily`；不新建自动任务。

便携模式另行验收：初始化结果包，确认生成30行骨架和15/15双池；填写测试数据后运行 `check`；确认超过4款WFS、单店超过2款、FBM非PASS或WFS硬门禁不全都会安全阻断；最后运行 `pack` 并在原运营电脑执行只读导入检查。

技术试跑命令：

```bash
WFS_RUNTIME_DIR="$HOME/Documents/wfs-handbag-runtime" python3 "$HOME/.codex/skills/walmart-wfs-handbag-selection/scripts/wfs_skillctl.py" smoke --config "$HOME/Documents/wfs-handbag-runtime/config/wfs-local.json"
```

## 5. 故障恢复

- `BLOCKED`：修复登录或字段后使用同一日期重跑；不推进冷却。
- 半途失败：保留调试资料，但不提升部分候选。
- 历史不一致：停止正式日跑，从源端重新执行一致性备份并核对哈希。
- 飞书失败：先查 `deliveries`，相同幂等键只允许补发未成功记录。
- 正式任务未通过验收：保持关闭，不创建临时替代定时器。
