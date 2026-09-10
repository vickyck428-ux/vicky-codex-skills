---
name: amazon-finance-profit-analysis
description: Compatibility alias for the canonical financial-analysis Skill. Use only when the user explicitly invokes $amazon-finance-profit-analysis; never select this alias automatically.
---

# Amazon 财务分析兼容入口

这是历史调用名，只负责把同一请求原样转交 `$financial-analysis`。不要复制、修改或并行运行旧版财务脚本。

所有销售、利润、退货率和 SKU 汇总在计算前必须排除 `pencil case`、`pencil pouch`、`pen case`、`pen pouch` 和 `pen bag`。若存在对应实物库存，只能单列为“历史遗留清退”，不得进入正常经营数据。
