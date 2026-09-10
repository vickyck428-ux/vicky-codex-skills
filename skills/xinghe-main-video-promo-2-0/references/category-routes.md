# Category routes

Select exactly one route. User selection wins; otherwise infer conservatively from product name plus visible evidence. Use `other` when uncertain.

| Route | Typical evidence | Setting and props | Safe use action | Lighting/camera | Avoid |
|---|---|---|---|---|---|
| `beauty-personal-care` | bottle, jar, tube, compact, grooming tool | clean vanity, towel, mirror, stone tray | pick up, open cap, dispense only if clearly designed for it | soft beauty light, macro, slow push | invented ingredients, skin transformation, efficacy claims |
| `apparel-accessories` | garment, shoe, bag, jewelry, watch | neutral wardrobe, entryway, clean pedestal | fabric movement, wearing, fastening, carrying | soft directional light, detail pan | changing cut/color, extra logos, impossible body fit |
| `food-beverage` | sealed food pack, bottle, can, snack | kitchen or dining surface, matching tableware | open only if opening is visible, pour/serve only when physically suitable | appetizing warm light, close detail | invented ingredients, health claims, changing package text |
| `home-kitchen` | cookware, storage, furniture, decor, cleaning item | tidy home or kitchen | place, open, organize, wipe, cook only when clearly applicable | bright natural interior, steady dolly | wrong scale, unsafe heat, invented components |
| `electronics-appliances` | device, cable, control, appliance | clean desk, living room, kitchen counter | connect, press, rotate control, operate only visible controls | crisp studio/interior, controlled orbit | fake UI, impossible ports, water exposure, unsupported performance claims |
| `mother-baby-toys` | baby item, plush, block, learning toy | clean nursery or play surface | adult hand places or demonstrates simple visible mechanism | soft safe daylight, stable framing | unattended hazardous use, age claims, small-part invention |
| `pet-supplies` | bowl, leash, toy, carrier, grooming item | clean home or outdoor pet setting | place, clip, roll, brush only when clearly designed | friendly daylight, low-angle follow | unsafe restraint, forced animal behavior, veterinary claims |
| `tools-auto` | hand tool, hardware, car accessory, outdoor gear | organized bench, garage, vehicle-safe context | grip, align, tighten, mount only when compatible use is evident | strong side light, mechanical macro | missing PPE, dangerous operation, sparks, unsupported strength claims |
| `other` | ambiguous or mixed product | neutral seamless studio with one matching surface | rotate, pick up, place, reveal one visible feature | clean commercial light, slow push/orbit | guessing use, people using unknown products, invented parts |

## Director storyboard grammar

Choose the shot count from the product need, usually 4-8 shots for a 15-second ecommerce video. Do not force a fixed five-shot template.

Each shot card must include:

- **Time:** exact start and end time.
- **Director intent:** why this shot exists in the story.
- **Scene style:** the visual world, surface, props, color, and benchmark-style cues.
- **Main subject:** product, hand, model partial, detail, or setting.
- **Composition:** where the product sits and how readable it is.
- **Action beat:** one action only.
- **Camera movement:** one camera move only.
- **Lighting / premium cue:** the specific lighting, texture, rhythm, or sound-design reason the shot feels high-end.
- **Sound / voiceover timing:** where music, sound design, and short narration should land.
- **Transition:** how the shot connects to the next shot.
- **Product consistency lock:** what product identity details must remain unchanged.
- **Do not:** shot-specific drift risks.

When storyboard control images are generated, they must visually match these shot cards. During video generation, upload the product identity image first, then storyboard control images. The product image locks the product; storyboard images lock narrative logic and scene design.

Storyboard control image requirements:

- Use one visual panel per shot.
- Each panel must show the intended frame, not just a reference mood.
- Each panel must include compact readable director labels: shot number, time range, camera movement, main action beat, and scene/style cue.
- Use camera arrows, rack-focus marks, orbit marks, push-in marks, or hold marks when they clarify movement.
- Do not add marketing slogans, selling captions, price text, badges, platform UI, random text, or extra brand names.

Typical structure:

1. **Context entry:** establish a believable product world.
2. **Product establishment:** make identity and scale clear.
3. **First contact:** add tactile interaction when useful.
4. **Sensory/detail proof:** show one real visible detail.
5. **Experience/use moment:** connect the product to a safe user ritual or use cue.
6. **Product memory/hero:** return to an inspection-ready final frame.

Omit or merge shots when the product does not need them. Add one extra detail or experience shot only when it improves logic without making the video busy.

## Keyword hints

The script recognizes English and Chinese product names. Useful hints include:

- `beauty-personal-care`: beauty, skincare, serum, cream, perfume, 美妆, 护肤, 精华, 面霜, 个护
- `apparel-accessories`: apparel, shoe, handbag, jewelry, 服饰, 鞋, 包, 手表, 首饰, 珠宝
- `food-beverage`: food, snack, coffee, tea, beverage, 食品, 零食, 咖啡, 茶, 饮料
- `home-kitchen`: furniture, kitchen, storage, cup, lamp, 家居, 厨房, 收纳, 杯, 灯, 厨具
- `electronics-appliances`: electronic, phone, earbud, charger, 电子, 手机, 耳机, 充电器, 蓝牙
- `mother-baby-toys`: baby, toy, stroller, 母婴, 婴儿, 玩具, 童车, 儿童
- `pet-supplies`: pet, cat, dog, leash, 宠物, 猫, 狗, 牵引绳, 猫砂
- `tools-auto`: tool, wrench, auto, outdoor, 工具, 扳手, 车载, 汽车, 户外, 汽配

## Cross-border compliance hints

For Amazon, TikTok Shop, Shopify, AliExpress, and Temu, keep claims especially conservative. Treat these phrases as warning signals unless the user provided proof and asked to include them: `FDA approved`, `clinically proven`, `guaranteed`, `No.1`, `cure`, `medical grade`, `治愈`, `根治`, `第一`, `最强`, `保证`, `永久`, `无副作用`, `认证`.

Warnings do not block generation; they tell the human reviewer to verify the claim before using the video commercially.
