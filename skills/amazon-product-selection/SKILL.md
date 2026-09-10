---
name: amazon-product-selection
description: Analyze and screen general Amazon product, niche, or category opportunities when the user has not chosen a specialized method. Use for ordinary Amazon 选品、类目机会、候选打分、ACoS 或利润校验；do not use for 1688 closure, annual-goal supervision, one-off refined-handbag orchestration, Sorftime ten-direction research, or explicit ABA/keyword/store/social/software datasets.
---

# Amazon Product Selection

## Goal

Turn one or more market signals into an auditable `GO / MONITOR / NO-GO` decision. Separate discovery from validation: no discovery method alone proves that a product is viable.

## Load References

- Read [references/methods.md](references/methods.md) for the selected discovery route, thresholds, formulas, and method-specific checks.
- Read [references/output-template.md](references/output-template.md) before producing the final assessment.
- Read [references/course-comparison.md](references/course-comparison.md) only when the user asks about course evolution, duplicated methods, or differences between terms.

## Route the Request

Choose one primary entry route:

1. **Category-first**: use category environment analysis, then blue-ocean screening, then find a concrete product.
2. **Signal-first**: use ABA new words, keyword data, software product filters, social media, or competitor-store reverse analysis to generate candidates.
3. **Cross-platform confirmation**: start from a validated niche and find products that sell in another platform in the same country but lack equivalent Amazon supply.
4. **Candidate validation**: start from a named product, ASIN, keyword, spreadsheet, screenshot, or link and skip directly to common validation.

If several routes point to the same candidate, treat that as stronger evidence but still run common validation.

## Collect Inputs

Request or extract only the fields needed for the chosen route. Accept incomplete data and label missing values; never invent them.

At minimum, try to obtain:

- marketplace and target category or product;
- selling price, landed cost, Amazon fees, dimensions, and weight;
- core keywords, CPC, conversion rate, and search trend;
- same-product count, review distribution, launch dates, and fulfillment mode;
- top-product and tail-product sales;
- brand, seller, product, and Amazon Retail concentration;
- seasonality, return rate, patent or infringement risk;
- source signal and observation date.

Keep data sources internally consistent when calculating one metric. For example, do not combine CPC from one provider with conversion rate from a differently defined dataset without flagging the mismatch.

## Execute

### 1. Generate candidates

Follow the selected route in `methods.md`. Record the exact source signal and why each candidate entered the list.

### 2. Apply hard gates

Reject or pause a candidate when any of these conditions is confirmed:

- infringement, compliance, dangerous-goods, or procurement risk is unacceptable;
- landed profit is non-positive or gross margin is below the applicable floor;
- expected ACoS is above the marketplace ceiling without enough organic-traffic evidence to compensate;
- the market depends strongly on mature reviews and the launch plan cannot reproduce them;
- exact same-product supply is already crowded;
- demand is seasonal, temporary, or locally irrelevant and no timing plan exists.

Do not convert a missing value into a pass. Mark it `NEEDS DATA`.

### 3. Run common validation

Validate in this order:

1. Confirm product identity and same-market demand.
2. Search Amazon for exact and near substitutes.
3. Check market size, trend, monopoly, reviews, and new-product performance.
4. Estimate advertising cost:

   `expected ACoS = CPC / (conversion rate × selling price)`

5. Calculate gross margin and absolute profit with landed cost and Amazon fees.
6. Inspect organic-versus-ad traffic, launch tactics, and achievable differentiation.
7. Check logistics, returns, seasonality, patents, and operational fit.
8. Compare the result with the user's capital, team, and operating model.

### 4. Decide

- Return `GO` only when hard gates pass and the evidence supports a practical launch.
- Return `MONITOR` when the signal is early or promising but essential data is missing.
- Return `NO-GO` when a hard gate fails or the remaining upside cannot justify the risk.

Avoid averaging away fatal weaknesses with a total score. Use scores only to rank candidates that have already passed hard gates.

## Merge Rules

- Treat category analysis and blue-ocean scoring as market selection, not final product selection.
- Treat ABA, keyword, software, social, cross-platform, and store-reverse methods as candidate generators.
- Use the same common validation layer for every candidate regardless of how it was discovered.
- Prefer current, more explicit thresholds when two course terms differ; preserve the older value in the course-comparison note.
- Classify lessons by actual content, not filename. In the 40th course, lessons 05 and 06 have crossed titles: 05 mainly teaches software product filtering, while 06 mainly teaches keyword-data selection.
- Separate course heuristics from verified current marketplace facts. If the decision depends on current fees, policies, or tool definitions, verify them or label them as unverified.

## Output

Use the structure in `output-template.md`. Always include:

- route used and evidence date;
- hard-gate result;
- metric-by-metric evidence and missing data;
- reasons for `GO / MONITOR / NO-GO`;
- the next cheapest validation action;
- confidence and assumptions.

When comparing multiple candidates, rank only those that passed the hard gates and explain the decisive difference in one sentence per candidate.
