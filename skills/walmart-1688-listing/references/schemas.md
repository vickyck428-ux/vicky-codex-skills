# Schemas

## Parsed product

`parsed_products.json` contains:

```json
{
  "products": [{
    "offerId": "735483499993",
    "titleZh": "source title",
    "category": {"topCategoryId": 1042954, "leafCategoryId": 201548714},
    "attributes": [{"name": "材质", "values": ["PU"]}],
    "packageInfo": {"depthIn": 11.81, "widthIn": 7.87, "heightIn": 3.94, "weightLb": 1.1},
    "dimensions": [{"name": "颜色", "values": [{"name": "黑色", "imageUrl": "https://..."}]}],
    "variants": [{
      "skuId": "5730601457142",
      "specId": "...",
      "dimensions": {"颜色": "黑色"},
      "inventory": 999,
      "costRmb": 51,
      "weightLb": 0.88,
      "images": ["https://..."]
    }]
  }],
  "failures": []
}
```

## Listing content

Write `listing_content.json` as:

```json
{
  "products": [{
    "offerId": "735483499993",
    "keywords": ["shoulder handbag", "top handle purse"],
    "title": "A brief English title beginning with the configured brand and not exceeding 150 characters or a stricter template limit.",
    "description": "The exact title followed by one English paragraph of at least 150 words containing every option.",
    "keyFeatures": ["Feature 1", "Feature 2", "Feature 3", "Feature 4", "Feature 5"],
    "material": "Faux Leather",
    "dimensionTranslations": {
      "颜色": {
        "黑色（无链条）": "Black No Chain",
        "黑色（带链条）": "Black With Chain"
      }
    }
  }]
}
```

Every product and every raw dimension value must appear exactly once. Do not add facts unsupported by parsed evidence. Select one or two primary keywords. The title, description, key features, material, and translations may contain only letters, numbers, spaces, commas, and periods. Use proper capitalization and reject all-caps copy, URLs, retailer names, promotional claims, unsupported authenticity or quality claims, emojis, and special formatting. Remove calendar years unless the official product-type Content Standard requires one, but preserve supported decade terms including `1900s`, `1990s`, and `2000s`.

Follow `us-listing-content-policy.md`. Keep the title at most 150 characters or the stricter current template limit. Write the description as one paragraph of at least 150 words with no general maximum unless the template supplies one. Keep exactly five Key Features for this tool, each at most 80 characters including spaces.

## Image review

Copy `image_review.skeleton.json` to `image_review.json`. For every SKU, keep only candidate URLs that passed visual review:

```json
{
  "products": [{
    "offerId": "735483499993",
    "variants": [{
      "skuId": "5730601457142",
      "candidateImages": ["https://..."],
      "approvedImages": ["https://..."],
      "rejectedImages": [{"url": "https://...", "reason": "CHINESE_TEXT"}]
    }]
  }]
}
```

Approve at most nine candidate images. Prefer at least four distinct eligible images. Require an exact-product primary image on a seamless white background and follow the file, size, content, and AI-editing rules in `us-listing-content-policy.md`. If all images contain obvious Chinese text, Hello Kitty, cartoons, other suspected third-party IP, or unrelated products, leave `approvedImages` empty so the SKU is blocked.
