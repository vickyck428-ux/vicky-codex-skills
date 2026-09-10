#!/usr/bin/env node

import { Buffer } from "node:buffer";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TRACKING_NAMES = new Set([
  "spm", "ali_refid", "ali_trackid", "xxc", "extension_id", "jd_pop",
  "ref", "ref_", "tag", "aff_fcid", "aff_fsk", "aff_platform", "sk",
  "clickid", "click_id", "campaign", "campaign_id", "source", "source_type",
  "ad_id", "adid", "material_id", "msclkid", "gclid", "fbclid", "irclickid",
  "campid", "mkcid", "mkevt", "mkrid", "siteid", "customid", "toolid",
  "refer_page_name", "refer_page_id", "refer_page_sn", "smtt",
]);

const MARKETPLACE_PLATFORMS = new Set([
  "taobao", "tmall", "jd", "pinduoduo", "douyin-shop", "kuaishou-shop",
  "xiaohongshu-commerce", "1688", "amazon",
  "tiktok-shop", "aliexpress", "temu", "ebay", "walmart", "shopee", "lazada",
]);

function ensureUrl(raw) {
  const value = String(raw ?? "").trim();
  if (!value) throw new Error("URL is empty");
  return new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(value) ? value : `https://${value}`);
}

function addParam(target, key, value) {
  if (!(key in target)) target[key] = value;
  else if (Array.isArray(target[key])) target[key].push(value);
  else target[key] = [target[key], value];
}

function isTrackingParam(name) {
  const key = name.toLowerCase();
  return key.startsWith("utm_") || key.startsWith("aff_") || TRACKING_NAMES.has(key);
}

function decodeBase64Json(value) {
  try {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    const decoded = Buffer.from(padded, "base64").toString("utf8");
    try { return JSON.parse(decoded); } catch { return decoded; }
  } catch {
    return null;
  }
}

function detectPlatform(url) {
  const host = url.hostname.toLowerCase().replace(/^www\./, "");
  if (/(^|\.)detail\.tmall\.com$|(^|\.)tmall\.com$/.test(host)) return "tmall";
  if (/(^|\.)taobao\.com$/.test(host)) return "taobao";
  if (/(^|\.)jd\.com$/.test(host)) return "jd";
  if (/(^|\.)(yangkeduo|pinduoduo)\.com$/.test(host)) return "pinduoduo";
  if (/(^|\.)(jinritemai|douyin)\.com$/.test(host)) return "douyin-shop";
  if (/(^|\.)(kwaishop|kuaishou)\.com$/.test(host)) return "kuaishou-shop";
  if (/(^|\.)xiaohongshu\.com$/.test(host)) return "xiaohongshu-commerce";
  if (/(^|\.)1688\.com$/.test(host)) return "1688";
  if (/(^|\.)amazon\.[a-z.]+$/.test(host)) return "amazon";
  if (/(^|\.)shop\.tiktok\.com$/.test(host)) return "tiktok-shop";
  if (/(^|\.)aliexpress\.[a-z.]+$/.test(host)) return "aliexpress";
  if (/(^|\.)temu\.[a-z.]+$/.test(host)) return "temu";
  if (/(^|\.)ebay\.[a-z.]+$/.test(host)) return "ebay";
  if (/(^|\.)walmart\.[a-z.]+$/.test(host)) return "walmart";
  if (/(^|\.)shopee\.[a-z.]+$/.test(host)) return "shopee";
  if (/(^|\.)lazada\.[a-z.]+$/.test(host)) return "lazada";
  if (host.endsWith(".myshopify.com")) return "shopify";
  if (/\/products?\//i.test(url.pathname)) return "shopify-or-dtc";
  return "generic-web";
}

function extractIdentity(url, platform) {
  const path = decodeURIComponent(url.pathname);
  const q = url.searchParams;
  let productId = null;
  let variantId = q.get("skuId") || q.get("sku_id") || q.get("variant") || null;
  let extra = {};

  switch (platform) {
    case "tmall":
    case "taobao":
      productId = q.get("id") || path.match(/\/i(\d+)\.htm/i)?.[1] || null;
      break;
    case "jd":
      productId = path.match(/\/(?:product\/)?(\d+)\.html/i)?.[1] || q.get("sku") || null;
      break;
    case "pinduoduo":
      productId = q.get("goods_id") || q.get("goodsId") || path.match(/goods[_/-](\d+)/i)?.[1] || null;
      break;
    case "douyin-shop":
      productId = q.get("id") || q.get("product_id") || q.get("promotion_id") || path.match(/(?:product|detail)[/_-](\d+)/i)?.[1] || null;
      break;
    case "kuaishou-shop":
    case "xiaohongshu-commerce":
      productId = q.get("id") || q.get("product_id") || q.get("goods_id") || path.match(/(?:product|goods|detail)[/_-](\d+)/i)?.[1] || null;
      break;
    case "1688":
      productId = path.match(/\/offer\/(\d+)\.html/i)?.[1] || q.get("offerId") || null;
      break;
    case "amazon":
      productId = path.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})(?:[/?]|$)/i)?.[1]?.toUpperCase() || null;
      break;
    case "tiktok-shop":
      productId = path.match(/\/view\/product\/(\d+)/i)?.[1] || q.get("product_id") || null;
      break;
    case "aliexpress":
      productId = path.match(/\/item\/(\d+)\.html/i)?.[1] || q.get("productId") || null;
      break;
    case "temu":
      productId = q.get("goods_id") || path.match(/-g-(\d+)\.html/i)?.[1] || null;
      break;
    case "ebay":
      productId = path.match(/\/itm\/(?:[^/]+\/)?(\d+)/i)?.[1] || null;
      break;
    case "walmart":
      productId = path.match(/\/ip\/(?:[^/]+\/)?(\d+)/i)?.[1] || null;
      break;
    case "shopee": {
      const match = path.match(/-i\.(\d+)\.(\d+)/i);
      productId = match?.[2] || q.get("itemid") || null;
      extra.shop_id = match?.[1] || q.get("shopid") || null;
      break;
    }
    case "lazada": {
      const match = path.match(/-i(\d+)-s(\d+)\.html/i);
      productId = match?.[1] || q.get("itemId") || null;
      extra.sku_id = match?.[2] || variantId;
      break;
    }
    case "shopify":
    case "shopify-or-dtc":
      productId = path.match(/\/products\/([^/?]+)/i)?.[1] || null;
      break;
    default: {
      const pathProductId = path.match(/\/(?:product|products|item|p)\/([^/?]+)/i)?.[1] || null;
      const productishPath = /\/(?:product|products|item|goods|p)(?:[/.]|$)/i.test(path);
      productId = q.get("product_id") || q.get("productId") || q.get("item_id") || pathProductId || (productishPath ? q.get("id") : null);
      break;
    }
  }

  return { productId, variantId, extra };
}

function canonicalize(url, platform, identity) {
  const { productId, variantId } = identity;
  const host = url.hostname.toLowerCase().replace(/^www\./, "");
  let canonical;

  if (platform === "tmall" && productId) canonical = new URL(`https://detail.tmall.com/item.htm?id=${productId}`);
  else if (platform === "taobao" && productId) canonical = new URL(`https://item.taobao.com/item.htm?id=${productId}`);
  else if (platform === "jd" && productId) canonical = new URL(`https://item.jd.com/${productId}.html`);
  else if (platform === "pinduoduo" && productId) canonical = new URL(`https://mobile.yangkeduo.com/goods.html?goods_id=${productId}`);
  else if (platform === "1688" && productId) canonical = new URL(`https://detail.1688.com/offer/${productId}.html`);
  else if (platform === "amazon" && productId) canonical = new URL(`https://${host}/dp/${productId}`);
  else if (platform === "aliexpress" && productId) canonical = new URL(`https://${host}/item/${productId}.html`);
  else if (platform === "ebay" && productId) canonical = new URL(`https://${host}/itm/${productId}`);
  else if (platform === "walmart" && productId) canonical = new URL(`https://${host}/ip/${productId}`);
  else {
    canonical = new URL(url.toString());
    canonical.hash = "";
    for (const key of [...canonical.searchParams.keys()]) {
      if (isTrackingParam(key)) canonical.searchParams.delete(key);
    }
  }

  if ((platform === "tmall" || platform === "taobao") && variantId) canonical.searchParams.set("skuId", variantId);
  if ((platform === "shopify" || platform === "shopify-or-dtc") && variantId) canonical.searchParams.set("variant", variantId);
  canonical.hostname = canonical.hostname.toLowerCase();
  return canonical.toString();
}

export function normalizeProductUrl(raw) {
  const url = ensureUrl(raw);
  const platform = detectPlatform(url);
  const identity = extractIdentity(url, platform);
  const trackingParams = {};
  const functionalParams = {};

  for (const [key, value] of url.searchParams.entries()) {
    addParam(isTrackingParam(key) ? trackingParams : functionalParams, key, value);
  }

  const decodedTracking = {};
  for (const [key, value] of Object.entries(trackingParams)) {
    if (key === "extension_id") {
      const source = Array.isArray(value) ? value[0] : value;
      const decoded = decodeBase64Json(source);
      if (decoded !== null) decodedTracking[key] = decoded;
    }
  }

  const productLike = Boolean(identity.productId) || /\/(?:product|products|item|goods|dp|itm)(?:[/.]|$)/i.test(url.pathname);
  const mode = productLike
    ? "product-page"
    : MARKETPLACE_PLATFORMS.has(platform)
      ? "marketplace-page"
      : "brand-website";

  return {
    input_url: String(raw),
    canonical_url: canonicalize(url, platform, identity),
    mode,
    platform,
    product_id: identity.productId,
    variant_id: identity.variantId,
    ...identity.extra,
    functional_params: functionalParams,
    tracking_params: trackingParams,
    decoded_tracking: decodedTracking,
  };
}

function runCli() {
  const inputs = process.argv.slice(2);
  if (!inputs.length) {
    console.error("Usage: node scripts/normalize-product-url.mjs <url> [url ...]");
    process.exitCode = 2;
    return;
  }

  let failed = false;
  const results = inputs.map((input) => {
    try { return normalizeProductUrl(input); }
    catch (error) {
      failed = true;
      return { input_url: input, error: error instanceof Error ? error.message : String(error) };
    }
  });
  console.log(JSON.stringify(results.length === 1 ? results[0] : results, null, 2));
  if (failed) process.exitCode = 1;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  runCli();
}
