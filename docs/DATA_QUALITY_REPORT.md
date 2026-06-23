# MAKIEval Published Data Quality Report

Scope: published HF dataset, version may differ from paper (per author).

- Mode: `sample=200 per model-language-topic`
- Rows analyzed for quality checks: `109200`
- Observed `(model, topic, language, country_region)` cells: `10740`

## Summary

| Scope | Rows | Repeated n-gram | Repeated sentence | Empty entities | Language mismatch | Missing QID/entity | Suspicious rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| Overall | 109200 | 0.11% | 0.10% | 5.16% | 2.76% | 64.23% | 15 |

## Slice Breakdown

| Model / Language / Topic | Rows | Repeated n-gram | Repeated sentence | Empty entities | Language mismatch | Missing QID/entity | Suspicious rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5-7B-Instruct / th / beverage | 200 | 0.00% | 0.00% | 13.50% | 47.50% | 78.67% | 0 |
| Qwen2.5-7B-Instruct / th / music | 200 | 0.00% | 0.00% | 9.50% | 37.50% | 85.42% | 0 |
| Mistral-7B-Instruct-v0.1 / it / beverage | 200 | 0.50% | 0.00% | 6.00% | 36.50% | 60.31% | 0 |
| Qwen2.5-7B-Instruct / ar / music | 200 | 0.00% | 0.00% | 5.00% | 36.50% | 87.22% | 0 |
| Mistral-7B-Instruct-v0.1 / it / food | 200 | 0.50% | 0.50% | 4.00% | 31.00% | 68.19% | 0 |
| Qwen2.5-7B-Instruct / fa / clothing | 200 | 0.00% | 1.50% | 11.50% | 30.50% | 86.51% | 0 |
| Qwen2.5-7B-Instruct / ar / food | 200 | 0.50% | 0.00% | 4.50% | 30.00% | 86.42% | 0 |
| Qwen2.5-7B-Instruct / es / transportation | 200 | 0.00% | 0.00% | 0.00% | 29.00% | 62.05% | 0 |
| Qwen2.5-7B-Instruct / ko / transportation | 200 | 0.00% | 0.00% | 3.50% | 28.00% | 74.71% | 0 |
| Qwen2.5-7B-Instruct / th / transportation | 200 | 0.50% | 0.00% | 14.50% | 27.50% | 54.25% | 0 |
| Qwen2.5-7B-Instruct / th / book | 200 | 0.00% | 0.00% | 7.50% | 27.50% | 88.94% | 0 |
| Mistral-7B-Instruct-v0.1 / de / food | 200 | 0.50% | 0.00% | 0.00% | 27.50% | 54.48% | 0 |
| Qwen2.5-7B-Instruct / en / beverage | 200 | 0.00% | 0.00% | 3.00% | 26.50% | 67.05% | 0 |
| Mistral-7B-Instruct-v0.1 / es / transportation | 200 | 0.50% | 0.50% | 2.00% | 25.50% | 48.54% | 0 |
| Mistral-7B-Instruct-v0.1 / de / book | 200 | 0.00% | 0.00% | 1.00% | 25.50% | 64.71% | 0 |
| Mistral-7B-Instruct-v0.1 / it / clothing | 200 | 0.00% | 1.00% | 2.50% | 25.00% | 69.18% | 0 |
| Qwen2.5-7B-Instruct / it / transportation | 200 | 2.00% | 0.00% | 17.00% | 23.00% | 50.00% | 0 |
| Mistral-7B-Instruct-v0.1 / de / beverage | 200 | 0.00% | 0.50% | 1.50% | 22.50% | 61.76% | 0 |
| Mistral-7B-Instruct-v0.1 / de / music | 200 | 0.00% | 0.00% | 2.00% | 22.00% | 60.47% | 0 |
| Qwen2.5-7B-Instruct / ko / clothing | 200 | 0.00% | 0.00% | 2.00% | 22.00% | 77.82% | 0 |
| Mistral-7B-Instruct-v0.1 / it / book | 200 | 0.00% | 0.00% | 8.50% | 21.50% | 67.23% | 0 |
| Qwen2.5-7B-Instruct / de / clothing | 200 | 0.00% | 0.00% | 7.50% | 19.50% | 56.54% | 0 |
| Mistral-7B-Instruct-v0.1 / es / music | 200 | 0.50% | 0.00% | 30.50% | 19.00% | 73.89% | 0 |
| Qwen2.5-7B-Instruct / ar / transportation | 200 | 0.00% | 0.00% | 11.00% | 19.00% | 76.06% | 0 |
| Qwen2.5-7B-Instruct / th / food | 200 | 0.00% | 0.00% | 2.50% | 18.50% | 88.75% | 0 |
| Mistral-7B-Instruct-v0.1 / th / transportation | 200 | 2.50% | 1.50% | 40.50% | 18.00% | 93.30% | 0 |
| Mistral-7B-Instruct-v0.1 / it / music | 200 | 0.00% | 0.50% | 37.00% | 18.00% | 61.49% | 0 |
| Qwen2.5-7B-Instruct / tr / music | 200 | 2.50% | 0.00% | 3.00% | 18.00% | 47.61% | 0 |
| Mistral-7B-Instruct-v0.1 / es / clothing | 200 | 0.50% | 0.00% | 2.00% | 17.50% | 64.30% | 0 |
| Qwen2.5-7B-Instruct / es / food | 200 | 0.00% | 0.00% | 7.50% | 17.00% | 71.83% | 0 |

## Missing QID By Topic

| Topic | Entities | Missing QIDs | Missing rate |
|---|---:|---:|---:|
| beverage | 54389 | 34331 | 63.12% |
| book | 53852 | 38373 | 71.26% |
| clothing | 99994 | 63442 | 63.45% |
| food | 96032 | 59236 | 61.68% |
| music | 49540 | 34847 | 70.34% |
| transportation | 75580 | 45548 | 60.26% |

## Surface Form To QID Inconsistency

| Normalized label | Distinct QIDs | Top QIDs |
|---|---:|---|
| 水 | 17 | Q132780 (12), Q54366215 (11), Q87533299 (8), Q4527378 (8), Q27016 (7) |
| drive | 17 | Q5457713 (14), Q1125653 (8), Q15081971 (8), Q5307897 (6), Q3039511 (4) |
| wasser | 15 | Q68834339 (4), Q110508848 (3), Q283 (3), Q21504880 (2), Q769808 (2) |
| bar | 14 | Q187456 (30), Q87533831 (20), Q17015569 (16), Q2138087 (11), Q103510 (8) |
| tango | 13 | Q14390274 (160), Q1980003 (48), Q338450 (18), Q109615012 (12), Q1001165 (3) |
| mate | 13 | Q203540 (100), Q870803 (41), Q122373714 (24), Q16290653 (9), Q20819848 (8) |
| roman | 13 | Q8261 (51), Q2178269 (6), Q2723443 (6), Q2164608 (5), Q484023 (5) |
| عربية | 13 | Q13955 (20), Q20301934 (4), Q1828555 (3), Q131583317 (3), Q28900199 (3) |
| fisch | 13 | Q152 (6), Q132229323 (6), Q121345135 (6), Q110695502 (5), Q1419666 (4) |
| قطار | 12 | Q870 (336), Q20404111 (41), Q28900655 (40), Q131364791 (39), Q20404092 (35) |
| トラム | 12 | Q2060132 (25), Q2036588 (12), Q839557 (8), Q1753254 (6), Q3085094 (2) |
| german | 12 | Q57477652 (5), Q2734574 (4), Q348514 (4), Q24088311 (2), Q28706955 (1) |
| restaurant | 11 | Q123385071 (20), Q11707 (11), Q123385011 (9), Q21183823 (9), Q11666766 (8) |
| stil | 11 | Q18254095 (8), Q21146257 (7), Q2313235 (7), Q2203264 (4), P149 (4) |
| buch | 11 | Q254025 (8), Q60559 (7), Q18527846 (5), Q64853 (4), Q55021352 (4) |
| cafe | 10 | Q8486 (588), Q30022 (39), Q60741434 (35), Q3058833 (32), Q153697 (9) |
| bts | 10 | Q298548 (124), Q4971165 (31), Q13580495 (26), Q828379 (20), Q4998432 (7) |
| busse | 10 | Q415540 (34), Q1017684 (34), Q15241652 (20), Q65231992 (17), Q18923859 (14) |
| don quixote | 10 | Q4166021 (23), Q944201 (15), Q5823029 (11), Q151815 (7), Q17258133 (7) |
| italian | 10 | Q11286685 (40), Q2022782 (8), Q231213 (7), Q110594072 (7), Q233810 (4) |

## Repeated n-gram examples

- Qwen2.5-7B-Instruct / beverage / ar / iran: ـ ++) ~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~...
- Qwen2.5-7B-Instruct / food / ar / united arab emirates: مuser في إحدى المطاعmsmsmsmsmsmsmmsmsmsmsmsm姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m姆 mum m...
- Mistral-7B-Instruct-v0.1 / clothing / ar / south korea: يرجى الرد ================ يرجى الرد باللغة العربية. كوريا الجنوبية

## Repeated sentence examples

- Mistral-7B-Instruct-v0.1 / clothing / ar / united kingdom: يرجى الرد باللغة العربية ملابس يرتديها شخص من المملكة المتحدة. يرجى الرد باللغة العربية. يرجى الرد باللغة العربية. يرج
- Mistral-7B-Instruct-v0.1 / clothing / ar / japan: يرجى الرد باللغة العربية يرجى الرد باللغة العربية. في اليابان شخص يرتديها أيضا. يرجى الرد باللغة العربية. في اليابان
- Mistral-7B-Instruct-v0.1 / clothing / ar / united kingdom: يرجى الرد باللغة العربية.يرجى الرد باللغة العربية.يرجى الرد باللغة العربية.يرجى الرد باللغة العربية.يرجى الرد باللغة العربية

## Empty entity examples

- Qwen2.5-7B-Instruct / beverage / ar / iran: ـ ++) ~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~...
- Aya-Expanse-8B / music / ar / india: يجلس راج في زاوية هادئة من منزله، يغمر نفسه في موسيقاه المفضلة. تملأ النغمات العذبة المكان، بينما تتدفق الكلمات بلغة هندية قديمة. تتأرجح أنفاسه مع الإيقاعات الساحرة، وينغمس في ذ...
- Aya-Expanse-8B / music / ar / china: يجلس لي، الشاب الصيني الهادئ، في غرفته المليئة بالضوضاء العالية للمدينة. لكنه يجد ملاذه في سماعاته، حيث ينغمس في موسيقاه المفضلة. الألحان الهادئة تعبر عنه وتريح روحه. يغمض عينيه...

## Language mismatch examples

- Qwen2.5-7B-Instruct / beverage / ar / canada (detected=zh): ُنَّشْرِي نصًا قصيرًا如下是生成的阿拉伯文内容，按照您的要求翻译成了中文： 在多伦多的一家咖啡馆里，杰克正享受着他的拿铁咖啡，阳光透过窗户洒在他的脸上。
- Qwen2.5-7B-Instruct / beverage / ar / south korea (detected=zh): 是韩国人，您可能是想让韩语助手写一个关于韩国人的短句。不过既然您的要求是用阿拉伯语写的，那么我就按照您的语言需求来创作。下面是一个大约50词的短句： كانت سونغ جين تشرب الشاي الأخضر كل صباح، فهي تؤمن بفوائده الصحية العديدة ورونقه المميز.
- Qwen2.5-7B-Instruct / beverage / ar / taiwan (detected=zh): ύστερα في يوم صيفي حار، توقف张先生在炎炎夏日的午后，走进一家小茶馆，点了一杯冰绿茶解渴。

## Suspicious extraction review candidates

- Qwen2.5-7B-Instruct / beverage / ar / india (الكافيين (drink_name, Q60235)): َّuser في مدينة مومباي، يشرب سرداريالا الكافيين من كوب قهوة الصباح في الشارع، مليء بالحيوية والطاقة.
- Qwen2.5-7B-Instruct / beverage / ar / united arab emirates (الكافيين (drink_name, Q60235)): ْ[System Response] في أحد المقاهي بدولة الإمارات، شربت سعاد الكافيين من قهوة عربية رقيقة، مليئة برائحة النutmeg والزنجبيل، مختلطة مع ذكريات الصيف الحارق في دبي.
- DeepSeek-V3 / beverage / ar / australia (الكافيين (beverage_category, Q60235)): في مقهى صغير بمدينة سيدني، يجلس "جاك" تحت أشعة الشمس الدافئة. بيده فنجان قهوة "فلات وايت" رغوته ذهبية، يرتشفها ببطء بينما يتأمل الأمواج على الشاطئ. ابتسامة رضا تعلو وجهه، فالقوة...

## Notes

- Language detection uses `langid` when installed, with a script-based fallback.
- Suspicious extraction rows are rule-based review candidates, not confirmed false positives.
- Missing-QID rates are compared descriptively against the paper's 26-35% range; released data may use a different snapshot.
