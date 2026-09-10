---
name: lc-product-selection-orchestrator
description: Compatibility alias for the canonical lc-1688-channel-closure Skill. Use only when the user explicitly invokes $lc-product-selection-orchestrator; never select this alias automatically.
---

# 1688 选品总控兼容入口

这是历史调用名，只负责把请求原样转交 `$lc-1688-channel-closure`。不得调用旧 `selectionctl`、创建第二套状态机或恢复旧品牌路由。

正式品牌字段以运行层为准：Amazon 只接受 `Amazon品牌 = Vocuer | BenPo bar`；Walmart 只接受 `Walmart品牌 = StyleSack | Baguery`。历史 `目标品牌` 仅展示，不驱动路由；不同平台必须分别确认。
