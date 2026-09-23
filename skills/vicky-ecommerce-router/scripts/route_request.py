#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Route:
    status: str
    primary_skill: str | None
    reason: str
    clarification: str | None = None
    choices: tuple[str, ...] = ()


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in text for term in terms)


def route(raw: str) -> Route:
    text = raw.strip().lower()
    explicit = re.search(r"\$([a-z0-9][a-z0-9-]{0,63})", text)
    if explicit:
        skill = explicit.group(1)
        return Route("ROUTED", skill, "用户显式指定 Skill")

    if has_any(text, ("1688全链路", "1688 全链路", "闭环状态", "恢复闭环", "迁移闭环", "mac mini迁移", "mac mini 迁移")):
        return Route("ROUTED", "lc-1688-channel-closure", "1688 闭环、恢复、迁移或状态核对")
    if has_any(text, ("年度目标", "年末目标", "每日监督", "方法轮换", "早报", "晚报", "稳定款缺口")):
        return Route("ROUTED", "lc-selection-goal-orchestrator", "目标驱动或日常监督")
    if has_any(text, ("sorftime", "10个方向", "10 个方向", "十个方向", "十个建议", "跨平台十")):
        return Route("ROUTED", "xinghe-crossborder-product-selection", "Sorftime 或十个跨平台方向")
    if has_any(text, ("精铺女包", "女包多方法", "全方法女包", "女包候选库")):
        return Route("ROUTED", "amazon-handbag-selection-orchestrator", "单次女包多方法选品")

    atomic = (
        (("aba", "品牌分析热搜"), "amazon-aba-selection"),
        (("关键词excel", "关键词 excel", "关键词库", "搜索词找产品"), "amazon-keyword-selection"),
        (("同行店铺", "竞品店铺", "storefront"), "amazon-competitor-store-selection"),
        (("社媒选品", "tiktok趋势", "instagram趋势", "pinterest趋势"), "amazon-social-media-selection"),
        (("软件商品库", "商品库excel", "商品库 excel"), "amazon-software-product-selection"),
    )
    for terms, skill in atomic:
        if has_any(text, terms):
            return Route("ROUTED", skill, "用户明确提供对应原子方法数据")

    if has_any(text, ("参考视频", "视频复刻", "拆解复刻", "爆款视频二创")):
        return Route("ROUTED", "xinghe-viral-video-remix-2-0", "参考视频拆解复刻")
    if has_any(text, ("带货视频", "口播", "ugc", "转化型视频", "产品演示视频")) or (
        has_any(text, ("真人", "手模", "产品演示", "转化型"))
        and has_any(text, ("视频", "短片", "口播", "ugc"))
    ):
        return Route("ROUTED", "xinghe-ecommerce-selling-video-2-0", "带货演示或转化内容")
    if has_any(text, ("15秒", "15 秒", "精品宣传片", "电影感", "无叠字")) and has_any(text, ("视频", "宣传片", "主图")):
        return Route("ROUTED", "xinghe-main-video-promo-2-0", "15 秒精品主图宣传片")
    if has_any(text, ("商品视频", "主图视频")):
        return Route("NEEDS_CLARIFICATION", None, "商品视频目标不明确", "你要带货演示，还是精品宣传片？", ("xinghe-ecommerce-selling-video-2-0", "xinghe-main-video-promo-2-0"))

    if has_any(text, ("参考图", "竞品图", "复刻排版", "锁定构图")) and has_any(text, ("产品图", "自己的图", "我的产品")):
        return Route("ROUTED", "xinghe-reference-image-remix-3", "参考图加自有产品图二创")
    if has_any(text, ("完整21图", "完整 21 图", "主图副图a+", "主图、副图和a+", "整套amazon", "整套 amazon")):
        return Route("ROUTED", "xinghe-amazon-visual-suite", "完整 Amazon 视觉套系")
    if has_any(text, ("场景图", "生活场景图", "使用场景图", "产品场景图")):
        return Route("ROUTED", "xinghe-scene-image-generator", "产品生活或使用场景图")
    if has_any(text, ("模特图", "上身图", "手持图", "试穿图", "佩戴图", "白底模特", "换模特")):
        return Route("ROUTED", "xinghe-model-image-generation", "白底真人模特产品图")
    if has_any(text, ("淘宝详情", "天猫详情", "京东详情", "拼多多详情", "国内电商详情", "电商详情图")):
        return Route("ROUTED", "xinghe-ecommerce-detail", "国内电商详情页或详情图")
    if has_any(text, ("pdp", "详情页", "a+模块", "a+ 模块", "详情模块")):
        return Route("ROUTED", "xinghe-crossborder-detail-3", "跨境详情页或模块化内容")
    if has_any(text, ("高点击", "广告图", "信息流", "带文案", "创意图")):
        return Route("ROUTED", "xinghe-ecommerce-creative-image", "单张 CTR 营销创意图")
    if has_any(text, ("白底主图", "换背景", "换颜色", "产品编辑", "amazon主图", "amazon 主图")):
        return Route("ROUTED", "xinghe-wanneng-shengtu-3-0", "普通商品图编辑或单张主图")

    if has_any(text, ("shipment id", "t1批准", "t1 已批准", "采购到货", "实测", "装箱", "箱号")):
        return Route("ROUTED", "lc-walmart-wfs-shipping-manifest", "WFS 审批后或发货阶段")
    if has_any(text, ("fbm已出单", "fbm 已出单", "订单报表", "首发动作", "补货动作", "成交转仓")):
        return Route("ROUTED", "lc-fbm-warehouse-action-center", "FBM 成交后动作阶段")
    if has_any(text, ("共享候选池", "共享款池", "亚沃共享", "1688共享")):
        return Route("ROUTED", "lc-fbm-shared-pool-selection", "1688 亚沃共享候选池")
    if has_any(text, ("listing草稿", "listing 草稿", "上传工作簿", "walmart上架表", "walmart 上架表")):
        return Route("ROUTED", "walmart-1688-listing", "Walmart Listing 工作簿")
    if has_any(text, ("渠道输出批次", "按渠道分流", "生成多个渠道表格")):
        return Route("ROUTED", "lc-channel-output-dispatcher", "Feishu 决策后的多渠道输出")
    if has_any(text, ("wfs选品", "wfs 选品", "amazon到walmart缺口", "amazon 到 walmart 缺口", "每日候选")):
        return Route("ROUTED", "walmart-wfs-handbag-selection", "WFS 售前找款阶段")

    if "amazon" in text and has_any(text, ("选品", "产品机会", "类目机会")):
        return Route("ROUTED", "amazon-product-selection", "普通 Amazon 选品，未指定方法")
    return Route("NO_MATCH", None, "不属于固定重叠路由")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text")
    args = parser.parse_args()
    raw = args.text if args.text is not None else sys.stdin.read()
    print(json.dumps(asdict(route(raw)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
