#!/usr/bin/env python3
from route_request import route


CASES = {
    "帮我做普通 Amazon 选品": "amazon-product-selection",
    "做一次美国站精铺女包全方法选品": "amazon-handbag-selection-orchestrator",
    "用 Sorftime 给我十个跨平台方向": "xinghe-crossborder-product-selection",
    "恢复 1688 全链路并核对闭环状态": "lc-1688-channel-closure",
    "做一张 Amazon 白底主图": "xinghe-wanneng-shengtu-3-0",
    "按参考图和我的产品图做二创": "xinghe-reference-image-remix-3",
    "生成 PDP 详情页模块": "xinghe-crossborder-detail-3",
    "生成完整 21 图主图副图A+": "xinghe-amazon-visual-suite",
    "给这个产品做 8 张生活场景图": "xinghe-scene-image-generator",
    "给包包做白底真人模特图": "xinghe-model-image-generation",
    "生成一套淘宝电商详情图": "xinghe-ecommerce-detail",
    "做真人手模带货视频": "xinghe-ecommerce-selling-video-2-0",
    "做 15 秒电影感无叠字精品宣传片": "xinghe-main-video-promo-2-0",
    "拆解参考视频并复刻": "xinghe-viral-video-remix-2-0",
    "做 Walmart WFS 每日候选": "walmart-wfs-handbag-selection",
    "FBM 已出单，按订单报表生成首发动作": "lc-fbm-warehouse-action-center",
    "T1 已批准，采购到货后生成装箱表": "lc-walmart-wfs-shipping-manifest",
    "已有 Shipment ID，更新发货表": "lc-walmart-wfs-shipping-manifest",
}

for request, expected in CASES.items():
    result = route(request)
    assert result.primary_skill == expected, (request, result, expected)

ambiguous = route("帮我做个商品视频")
assert ambiguous.status == "NEEDS_CLARIFICATION"
assert len(ambiguous.choices) == 2

explicit = route("请用 $amazon-keyword-selection 做这个")
assert explicit.primary_skill == "amazon-keyword-selection"

print(f"PASS {len(CASES) + 2} routing cases")
