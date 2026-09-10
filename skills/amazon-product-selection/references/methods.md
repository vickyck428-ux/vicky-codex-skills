# Merged Product-Selection Methods

## Core model

Use two layers:

1. **Discovery** produces a candidate from category, keyword, product, platform, social, or seller-store data.
2. **Validation** tests the same candidate against demand, competition, advertising, profit, reviews, risk, and operational fit.

Do not declare a product viable from discovery data alone.

## Shared formulas and thresholds

### Expected ACoS

Calculate:

`expected ACoS = CPC / (conversion rate × average selling price)`

Use decimal conversion rate, such as `0.10` for 10%. Keep CPC, conversion rate, and price definitions from compatible data sources.

Course working ceilings:

- United States: treat over 40% as a hard warning or rejection.
- Europe: treat over 35% as a hard warning because VAT reduces available margin.

Ranking points after hard gates pass:

- at or below 20%: +5;
- at or below 30%: +3;
- at or below 35%: +1.

### Gross margin

Calculate with landed cost and all Amazon fees. Report absolute profit as well as margin.

- Current working floor: 30%.
- Ranking points: at least 45% +5; at least 40% +3; at least 35% +1.
- A margin below 35% receives no positive score; below 30% is normally a rejection.

### Review dependence

Use both views when data permits:

1. In category analysis, calculate the sales share of listings with at least 500 reviews. Prefer at most 30%; over 50% is high risk.
2. Across about ten core keywords, calculate the share of organic first-page listings with at most 50 reviews. Prefer at least 20%.

Inspect successful new products separately. Course ranking heuristic:

- mostly launch with two free Vine reviews: +5;
- mostly launch with about ten Vine reviews: +3;
- mostly launch with about thirty Vine reviews: +1;
- mostly arrive with more than fifty reviews or obvious review manipulation: reject unless the user can reproduce the tactic lawfully.

### Advertising dependence

Use ad spend divided by total sales, not campaign ACoS, when judging whole-business dependence. A course operating target for broad distribution models is at most about 20% of total sales.

## 1. Category environment analysis

Use this to understand a category before choosing a product.

1. Resolve the correct category node and marketplace.
2. Inspect top-100 monthly sales and revenue; remember that tool totals may describe only the sampled top 100, not the entire category.
3. Compare top-10 with top-100 averages.
4. Inspect:
   - average price and top-product price;
   - average reviews and ratings;
   - average seller count and hijacking risk;
   - brand, seller, and product concentration;
   - Amazon Retail share;
   - new-product count and new-product sales;
   - A+ and video adoption;
   - returns and seasonality.
5. Verify tool estimates on Amazon. Treat product counts and sales estimates as directional, not exact.

Do not reject a category from one concentration metric. Determine whether the concentration comes from brand power, seller control, a product form, or a structural entry barrier.

## 2. Small blue-ocean niche screening

Use a coarse filter to find niches, then apply fatal metrics and ranking points.

### Coarse discovery range

Course working examples:

- top-100 total monthly sales: roughly 3,000–15,000;
- average monthly sales: roughly 30–150;
- average reviews: preferably no more than 200–300;
- optional minimum price: about 20 or another margin-supporting value;
- optional maximum weight: about 6 lb;
- Amazon Retail share: preferably no more than about 35%.

These are search ranges, not automatic passes.

### Fatal metrics

Check:

- gross margin and absolute profit;
- expected ACoS;
- review dependence;
- whether successful new-product launch tactics are reproducible;
- severe product, seller, or brand monopoly;
- patent, compliance, logistics, and return risks.

### Ranking signals

After fatal metrics pass, use these as supporting points:

- incremental or growing market: +1;
- product concentration below 40%: +1; above 60%: -1;
- Amazon Retail share below 30%: +1; above 50%: -1;
- local sellers outnumber Chinese sellers: +1;
- weak listing quality, such as no A+ or video accounting for over 40% of sales: +1;
- strong listing quality, such as A+ and video accounting for over 70% of sales: -1;
- return rate below 5%: +1; above 10%: -1;
- top monthly sales at least about 100: +1;
- profitable tail products: +1.

Use points only for comparison among candidates that passed the fatal metrics.

## 3. Multi-platform product selection

Use this after finding a viable niche.

1. Match the same country or consumer market. For example, validate a US Amazon opportunity on US eBay, Walmart, Etsy, Home Depot, Wayfair, TikTok Shop, or relevant local sites.
2. Search the niche's core keywords on the other platform.
3. Identify products with credible sales or engagement. Distinguish product reviews from seller reviews and ads from organic placements.
4. Search Amazon for the exact product and close substitutes.
5. Prefer products that sell on the source platform but have no equivalent Amazon supply, no local FBA supply, or only weak supply.
6. Validate expected ACoS, profit, reviews, patents, logistics, and differentiation.

Do not transfer demand across culturally different countries without additional validation. A popular product on a Chinese platform does not prove US demand.

## 4. ABA new-word selection

Use weekly ABA hot-search data to identify genuinely new search terms.

1. Find terms that did not previously appear in the historical ABA list and entered recently.
2. Exclude digital goods, fresh food, medicine, and other non-target or restricted categories.
3. Determine why the term appeared:
   - a genuinely new product;
   - a new name for an old product;
   - a media, event, or seasonal spike;
   - a changed search habit.
4. Prefer unfamiliar physical products with few matching listings and low CPC.
5. Reject or monitor familiar products, abundant matches, high CPC, and temporary event terms.
6. Verify listing launch dates, trend continuity, same-product supply, seller origin, reviews, advertising, procurement, costs, and patents.
7. Cross-check social media or trend data when the term may be viral.

A tool label saying “new word” is not proof; historical absence must be verified.

Judge how quickly the opportunity may crowd:

- very high current sales attract faster imitation;
- more new followers or copy listings shorten the window;
- a more prominent ABA rank normally attracts more sellers;
- if the earliest competing listing appeared within about ten days, a hot product may support only a small first-wave test rather than long-term stocking.

Prefer unexpected demand shocks over predictable seasonal or holiday rises. When a good product is likely to crowd, consider a smaller marketplace, another platform, a short-cycle launch, or a defensible redesign. Verify that demand transfers before moving across countries.

## 5. Software product filtering

Use a product database to generate candidates from observable listing traits.

1. Choose broad discovery or a target category node.
2. Combine filters such as:
   - launch within 30 days or another recent period;
   - no more than about 20 reviews;
   - FBM or a specified fulfillment mode;
   - minimum price or sales;
   - unpopular, heavy, oversized, or otherwise under-screened constraints when operationally suitable.
3. Inspect every filtered result manually.
4. Avoid immediately copying an extremely hot new US product that is visible to all users of the same tool.
5. Consider another marketplace or meaningful differentiation.
6. Validate same-product count, ads, CPC, conversion, margin, seasonality, patents, logistics, and supply.

Filters create a watchlist, not a decision.

## 6. Keyword-data selection

Use keyword databases to discover demand expressed in search language.

1. Inspect search volume and growth to estimate demand and direction.
2. Use CPC, conversion, and price to calculate expected ACoS.
3. Use SPR or CPR only as an estimated first-page order requirement.
4. Inspect title density and top-three click or purchase share.
5. Use a low traffic-acquisition-cost metric when the provider defines one clearly.
6. Do not use tool product count or supply-demand ratio as a direct competition measure when it includes only active or sampled listings.
7. Filter for unusual or unfamiliar terms, then identify the physical product behind each term.
8. Run full common validation.

Example discovery filters from the course include traffic-value maximum 2, price at least 10, average reviews at most 100, and excluding seasonal terms. Treat them as adjustable starting points.

## 7. Social-media selection

Use this for early signals, then validate on Amazon.

1. Select target-country sources such as TikTok, Instagram, Pinterest, Reddit, YouTube, or X.
2. Train the feed by searching, liking, and following novelty-product content, or use an official creative or ad center.
3. Prefer several independent viral posts over one isolated viral post.
4. Record views, likes, comments, shares, CTR, creator count, posting dates, and country.
5. Identify the product and search Amazon for exact and near substitutes.
6. Validate demand durability, same-product supply, expected ACoS, profit, reviews, patents, and logistics.
7. Use small test quantities for early, low-data products.

Social data is early but noisy; third-party marketplace data is slower but more confirmed. Use each for its proper role.

## 8. Competitor-store mirror reverse selection

Use this after finding one credible blue-ocean product or seller.

1. Enter the seller's storefront.
2. Infer seller age from lifetime, 12-month, and 3-month feedback; use feedback only as a volume proxy.
3. Judge the seller's operating tier from listing count, sales per listing, launch cadence, inventory, and ad spend.
4. Reject stores with a substantially stronger brand, capital base, or operating model than the user can reproduce.
5. Find products with fast organic growth and viable profit, not only the store's highest sales.
6. Reverse-search core keywords and the relevant niche.
7. Calculate expected ACoS and profit.
8. Count exact same products. Prefer one or two suppliers/listings; treat more than two or three as crowding.
9. Design concrete differentiation, such as quantity, bundle, dimensions, weight, material, or use case.
10. Run common risk checks before launch.

This method discovers candidates from a comparable operator; it does not justify copying protected content or designs.
