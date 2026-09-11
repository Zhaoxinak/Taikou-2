# -*- coding: utf-8 -*-
"""
gen_portrait_prompts.py — 生成 695 张武将立绘的提示词与「生成台账」
=================================================================
用途
----
按 tools/portrait_prompts.json 确立的风格模板，为全部真实武将（695 名）
逐条拼出 ImageGen 提示词，并产出可断点续跑的台账 tools/portrait_ledger.json。

台账是**跨会话/换 AI 续跑的唯一真源**：
  每次跑本脚本都会扫 assets/sprites/portraits/，已存在的真图自动标记 done，
  不会重复生成、不会重复烧积分。

关键数据修正（务必保留）
------------------------
1. 输出文件名是 **{id}.png**（不是 full_0013.png）——
   src/render/asset_loader.gd 实际按 "res://assets/sprites/portraits/%d.png" 加载。
   tools/portrait_prompts.json 里写的 assets/gfx/portrait/full_XXXX.png 已过时。
2. 尺寸按 src/render/AssetSpec.gd: PORTRAIT_SIZE = 512×640（4:5）。
   生成用 1024×1280（2x），再用 Pillow 缩到 512×640 落盘。
3. 国名不能直接用 officer["province"] —— 该字段与国表索引**对不上**
   （织田信长 province=13 会解成骏河，实为尾张）。
   正解：officer["city"] → castles[city]["province"] → provinces[idx]["name"]。

用法
----
    python tools/gen_portrait_prompts.py              # 生成/刷新台账
    python tools/gen_portrait_prompts.py --top 20     # 只看优先级最高的 20 条
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_LEDGER = os.path.join(ROOT, "tools", "portrait_ledger.json")
PORTRAIT_DIR = os.path.join(ROOT, "assets", "sprites", "portraits")

GEN_SIZE = "1024x1280"     # 2x
FINAL_SIZE = (512, 640)    # AssetSpec.PORTRAIT_SIZE (4:5)
BACKGROUND = "transparent"
STYLE = "和风半写实·手绘游戏感（太阁5式·家徽上甲）"
NEGATIVE = ("blurry, hyperrealistic, photorealistic photo, 3D render, western armor, modern clothing, "
            "pixel art, pixelated, chibi, deformed, ugly, watercolor blob, oil painting, "
            "watermark, text, letters, kanji, multiple characters, full body, landscape background")

START_YEAR = 1560

# 職位 → 英文描述（{armor} 由家族配色注入）
RANK_DESC = {
    "大名": "daimyo warlord, {armor} lacquered armor with gold accents, ornate battle surcoat (jinbaori) over the armor",
    "家老": "karou elder retainer, {armor} formal armor",
    "家臣": "household retainer, {armor} formal armor",
    "组头": "kumi-gashira captain, {armor} officer armor",
    "足轻头": "ashigaru head, {armor} light armor",
    "足轻组头": "ashigaru squad leader, {armor} light armor",
    "足轻工头": "ashigaru engineer, {armor} practical armor",
    "无": "ronin masterless samurai, worn {armor} traveling armor",
}

# =====================================================================
# v3.3 家徽表（surname → 家族纹章视觉描述）
# 全部为纯视觉描述、无罗马字/专名（防模型渲染成画面文字，踩过坑）
# 收录史实家徽；未收录家族用通用传统纹样（保证人人有家徽元素）
# =====================================================================
FAMILY_CRESTS = {
    "织田": "a stylized five-petal blossom emblem",
    "织田有乐": "a stylized five-petal blossom emblem",
    "武田": "two pairs of connected diamonds in a row",
    "上杉": "a sparrow perched on bamboo leaves",
    "长尾": "a sparrow perched on bamboo leaves",
    "伊达": "three vertical bars",
    "北条": "three overlapping fish scales",
    "今川": "a red bird emblem",
    "毛利": "a long horizontal stroke above three stars",
    "岛津": "a cross inside a circle",
    "长宗我部": "seven thin vertical strokes in a row",
"長宗我部": "seven thin vertical strokes in a row",
    "大友": "an apricot leaf emblem",
    "三好": "three oak leaves",
    "斋藤": "two wavy horizontal lines",
    "浅井": "a flower-diamond pattern",
    "朝仓": "a triple blossom emblem",
    "本愿寺": "a lotus flower emblem",
    "德川": "three hollyhock leaves radiating from a circle",
    "松平": "three hollyhock leaves radiating from a circle",
    "真田": "six coins in two rows of three",
    "前田": "a plum blossom emblem",
    "井伊": "a square well-frame emblem",
    "蒲生": "a ginger bud emblem",
    "石田": "a paulownia flower emblem",
    "细川": "nine stars in a circle",
    "黑田": "a wisteria flower in a circle",
    "佐竹": "a crescent moon beside a star",
    "最上": "three horizontal bars",
    "结城": "a paulownia flower emblem",
    "宇都宫": "three comma-shaped tomoe swirling",
    "里见": "a folding fan with a crescent moon",
    "六角": "a four-eye knot pattern",
    "京极": "a four-eye knot pattern",
    "足利": "two horizontal bars",
    "别所": "three oak leaves",
    "筒井": "a cross emblem",
    "大内": "a diamond flower pattern",
    "明智": "a bellflower emblem",
    "木下": "a paulownia flower emblem",
    "丰臣": "a paulownia flower emblem",
    "羽柴": "a paulownia flower emblem",
    "加藤": "a snake-eye ring pattern",
    "宇喜多": "a water wheel emblem",
    "尼子": "three stars",
    "龙造寺": "a camellia flower emblem",
    "相良": "two horizontal bars",
    "锅岛": "a square-cross pattern",
    "立花": "a star-shaped shrine charm",
    "高桥": "nine stars in a circle",
    "相马": "three comma-shaped tomoe swirling",
    "伊东": "a paulownia flower emblem",
    "肝付": "a cross emblem",
    "秋月": "seven stars",
    "神保": "two crossed arrows",
    "村上": "three vertical bars",
    "柿崎": "three oak leaves",
    "直江": "two sparrows on a branch",
    "片仓": "three vertical bars",
    "鬼庭": "three vertical bars",
    "山本": "a diamond pattern",
    "山县": "a diamond pattern",
    "马场": "a diamond pattern",
    "高坂": "a diamond pattern",
    "内藤": "a diamond pattern",
    "甘利": "a diamond pattern",
    "饭富": "a diamond pattern",
    "大谷": "a diamond inside a circle",
    "福岛": "a paulownia flower emblem",
    "山内": "a paulownia flower emblem",
    "藤堂": "a paulownia flower emblem",
    "浅野": "a cross inside a circle",
    "片桐": "a paulownia flower emblem",
    "堀尾": "three horizontal bars",
    "胁阪": "three horizontal bars",
    "中村": "a plum blossom emblem",
    "佐久间": "a diamond pattern",
    "池田": "a flower-diamond pattern",
    "泷川": "three horizontal bars",
    "丹羽": "a paulownia flower emblem",
    "柴田": "a diamond pattern",
    "佐佐": "a diamond pattern",
    "蜂须贺": "two crossed sickles",
    "森": "three oak leaves",
    "堀": "three oak leaves",
    "长束": "a diamond pattern",
    "增田": "three comma-shaped tomoe swirling",
    "平野": "an arrow feather wheel",
    "木村": "a diamond pattern",
    "可儿": "six coins in two rows of three",
    "仙石": "a plum blossom emblem",
    "前野": "a diamond pattern",
    "生驹": "a horse head emblem",
    "一柳": "a willow branch",
    "稻叶": "a diamond pattern",
    "氏家": "a diamond pattern",
    "远藤": "a diamond pattern",
    "不破": "a diamond pattern",
    "金森": "a diamond pattern",
    "原": "a diamond pattern",
    "长": "a diamond pattern",
    "蜂屋": "a bee emblem",
    "河尻": "a diamond pattern",
    "平手": "a diamond pattern",
    "村井": "a diamond pattern",
    "坂井": "a diamond pattern",
    "山田": "a diamond pattern",
    "高山": "a cross emblem",
    "小早川": "three vertical bars",
    "吉川": "a long horizontal stroke above three stars",
    "小笠原": "a sparrow perched on bamboo leaves",
    "土岐": "a diamond pattern",
    "安藤": "an anchor emblem",
    "津轻": "three horizontal bars",
    "南部": "a diamond pattern",
    "九户": "three overlapping fish scales",
    "芦名": "a dragon scale pattern",
    "田村": "a diamond pattern",
    "二本松": "two pine trees",
    "大崎": "a diamond pattern",
    "留守": "three vertical bars",
    "石川": "a diamond pattern",
    "佐野": "three comma-shaped tomoe swirling",
    "正木": "a diamond pattern",
    "波多野": "a diamond pattern",
    "赤井": "a red well-frame emblem",
    "小寺": "a diamond pattern",
    "畠山": "nine stars in a circle",
    "田山": "nine stars in a circle",
    "山名": "three horizontal bars",
    "赤松": "a pine tree with a crane",
    "浦上": "a diamond pattern",
    "一条": "a single horizontal stroke",
    "河野": "a diamond pattern",
    "伊予": "a diamond pattern",
    "十河": "three oak leaves",
    "香西": "a paulownia flower emblem",
    "篠原": "a bamboo stalk",
    "仁保": "a diamond pattern",
    "吉见": "a diamond pattern",
    "益田": "a diamond pattern",
    "陶": "a diamond pattern",
    "杉": "a cedar tree",
    "周布": "a diamond pattern",
    "佐波": "a diamond pattern",
    "三隅": "three corner marks",
    "都野": "a diamond pattern",
    "福屋": "a diamond pattern",
    "石见": "a diamond pattern",
    "因幡": "a diamond pattern",
    "若狭": "a diamond pattern",
    "逸见": "a diamond pattern",
    "朝井": "a diamond pattern",
    "安田": "a diamond pattern",
    "鸟羽": "a bird emblem",
    "堀江": "a diamond pattern",
    "多贺": "a diamond pattern",
    "上野": "a diamond pattern",
    "关口": "a diamond pattern",
    "丸毛": "a diamond pattern",
    "猪子": "a wild boar emblem",
    "堀田": "a diamond pattern",
    "佐藤": "a diamond pattern",
    "沟口": "a diamond pattern",
    "大野": "a diamond pattern",
    "长谷川": "a diamond pattern",
    "富田": "a diamond pattern",
    "冈田": "a diamond pattern",
    "前田利": "a plum blossom emblem",
    "太田": "a diamond pattern",
    "成田": "a diamond pattern",
    "松田": "a pine tree",
    "远山": "a diamond pattern",
    "大道寺": "a diamond pattern",
    "富永": "a diamond pattern",
    "多目": "a diamond pattern",
    "板部冈": "a diamond pattern",
    "梶原": "a diamond pattern",
    "风魔": "a wind swirl pattern",
    "服部": "a four-pointed throwing star",
    "柳生": "a willow branch",
    "九鬼": "an anchor emblem",
    "伊贺崎": "a four-pointed throwing star",
    "杂贺": "a crossed gun barrels emblem",
    "太原": "a diamond pattern",
    "真壁": "a diamond pattern",
    "大关": "a diamond pattern",
    "大田原": "a diamond pattern",
    "那须": "a diamond pattern",
    "小山": "a diamond pattern",
    "皆川": "a diamond pattern",
    "藤田": "a diamond pattern",
    "壬生": "a diamond pattern",
    "大森": "a diamond pattern",
    "长野": "a diamond pattern",
    "那波": "a diamond pattern",
    "横濑": "a diamond pattern",
    "小田": "a diamond pattern",
    "多贺谷": "a diamond pattern",
    "水谷": "a diamond pattern",
    "百百": "a diamond pattern",
    "古河": "a diamond pattern",
    "太田康": "a diamond pattern",
    "千叶": "a diamond pattern",
    "武田信": "two pairs of connected diamonds in a row",
    "穴山": "a diamond pattern",
    "小山田": "a diamond pattern",
    "饭尾": "a diamond pattern",
    "德川信": "three hollyhock leaves radiating from a circle",
    "井伊直": "a square well-frame emblem",
    "今川氏": "a red bird emblem",
    "朝比奈": "a diamond pattern",
    "关": "a diamond pattern",
    "太田道": "a diamond pattern",
    "北条氏": "three overlapping fish scales",
    "北条幻": "three overlapping fish scales",
    "松田宪": "a pine tree",
}
GENERIC_CREST = "a traditional Japanese family crest emblem"
FAMOUS_TRAITS = {
    "织田信长": "ambitious conqueror, commanding aura",
    "上杉谦信": "pious warlord, devout expression",
    "本愿寺显如": "pious warlord, devout expression",
    "柴田胜家": "veteran warrior, blunt honest face, heavy build",
    "木下藤吉郎": "humble low-born origin, scrappy survivor wit",
    "明智光秀": "refined intelligent features, composed",
}

# =====================================================================
# v3 史实外观特征表（2026-09-10 太阁5式画风升级）
# 关键武将给专属史实特征；未收录武将走通用模板（哈希分配避免雷同）。
# 提示词一律不写姓名（防模型渲染成画面文字），只写特征。
# =====================================================================
HISTORICAL_FACTS = {
    "织田信长": "tall slender frame, elongated face with high cheekbones, narrow sharp hawk-like eyes, high-bridged nose, traditional samurai topknot with shaved forehead (sakayaki), thin trimmed mustache, weathered campaign-worn skin with faint stubble, western nanban-style iron breastplate over black lacquered armor, gold-laced dark battle surcoat (jinbaori), gilded commander's war fan in hand, black and crimson lacquered armor, overbearing aura",
    "木下藤吉郎": "monkey-like homely face (sarugao), narrow shrewd slanted eyes, protruding mouth with long chin, thin wiry short stature, weathered dark skin, humble sharp wit, low-born scrappy air",
    "明智光秀": "refined elegant noble face, slim build, blue and white kimono with bellflower accents, cultured composure",
    "德川家康": "calm steady face, patient shrewd eyes, tea-brown armor, composed unshakable aura",
    "武田信玄": "broad square face, thick bushy eyebrows, wide nose, dense full beard, stocky sturdy build, deep red armor with white bear-fur crest on helmet, war fan in hand",
    "上杉谦信": "austere warrior-monk face, long face, calm penetrating eyes, white armor with white horsehair crest, priestly garment underneath",
    "伊达政宗": "one eye blind with scarred closed eyelid, the other eye sharp and piercing, black and gold armor with large golden crescent-moon helmet crest",
    "本多忠胜": "tall imposing warrior, deer-antler crest on black helmet, fierce loyal expression, sturdy build",
    "前田庆次": "flamboyant eccentric demeanor, loose flowing hair, extravagant ornate helmet, dashing bold grin",
    "柴田胜家": "rough blunt veteran face, heavy sturdy build, thick brows, stern war-hardened look",
    "森兰丸": "beautiful youthful page-boy face, delicate elegant features, fine slim build, serene beauty",
    "石田三成": "thin scholarly face, refined bookish composure, slender build, sharp calculating eyes",
    "北条氏康": "elderly shrewd face, round spectacles, silver hair, calm sagacious expression",
    "今川义元": "court-noble face with white powder makeup, thin mustache, noble court cap, refined aristocratic air",
    "长宗我部元亲": "fierce rustic strongman face, broad rugged features, one-layered practical armor, bold wild aura",
    "岛津义久": "stern Satsuma lord face, strong brows, black armor, dignified unyielding air",
    "大友宗麟": "portly imposing lord, western Christian influence with rosary, luxurious southern-barbarian style robe",
    "三好长庆": "handsome cultured warlord face, refined goatee, elegant composed demeanor",
    "松永久秀": "scheming narrow eyes, thin mustache, calculating sinister composure",
    "本愿寺显如": "tonsured monk head, priest robe under white armor, devout imposing presence",
    "毛利元就": "aged white-haired strategist, kind but shrewd eyes, long white beard, serene wisdom",
    "浅井长政": "handsome noble youth face, clean features, white and blue armor, upright honorable air",
    "朝仓义景": "cultured court noble face, elegant refined look, aristocratic bearing",
    "斋藤道三": "viper-like narrow cunning eyes, gaunt sharp face, thin mustache, sinister shrewdness",
    "服部半藏": "stoic ninja face, dark hood, shadowy calm intensity",
    "杂贺孙市": "rugged marksman face, bold confident grin, leather and iron gear, master gunner aura",
    "柳生宗严": "aged lean swordsman face, calm penetrating eyes, weathered serenity",
    "九鬼嘉隆": "rugged sea-captain face, weathered skin, bold naval commander aura",
    "石川五右卫门": "bold rogue face, mischievous fearless grin, disheveled stylish hair, outlaw charm",
    "伊贺崎道顺": "lean ninja face, focused sharp eyes, dark practical gear",
    "足利义辉": "dignified shogun face, commanding aristocratic presence, formal court armor",
    "尼子经久": "aged cunning face, thin sharp features, shrewd calculating eyes",
    "宇喜多直家": "scheming calculating face, thin mustache, sinister subtle smile",
    "立花道雪": "battle-tested stern face, commanding officer presence, weathered dignity",
    "高桥绍运": "scholar-warrior face, composed intelligent gaze, refined martial air",
    "丰臣秀吉": "round confident face, bright ambitious eyes, golden and crimson regal armor",
    "前田利家": "loyal sturdy warrior face, thick mustache, warm dependable bearing",
    "佐佐成政": "stern weathered face, sturdy build, disciplined soldier air",
    "泷川一益": "sharp-eyed veteran face, weathered rugged features, seasoned general air",
    "丹羽长秀": "dignified loyal face, calm composed bearing, noble retainer air",
    "池田恒兴": "loyal frank face, friendly firm bearing, sturdy build",
    "蜂须贺小六": "rough bandit-leader face, bold mustache, wild loyal aura",
    "堀秀政": "young clever officer face, refined sharp features, competent air",
    "高山右近": "devout Christian samurai face, calm noble composure, dignified faith",
    "蒲生氏乡": "young handsome noble face, refined intelligent features, proud cultured air",
    "细川忠兴": "refined noble face, elegant stern composure, cultured warrior air",
    "黑田孝高": "gaunt strategist face, piercing intelligent eyes, wizened clever air",
    "竹中重治": "frail genius face, bright sharp eyes, humble clever air",
    "真田昌幸": "wily shrewd face, thin mustache, masterful cunning air",
    "真田幸村": "handsome fierce young warrior face, crimson armor with six-coin crest, burning loyalty",
    "岛左近": "stalwart master-retainer face, imposing dignified air, unshakeable loyalty",
    "大谷吉继": "grave composed face, elegant bearing, fateful calm",
    "井伊直政": "stern young commander face, red armor with red-onyx crest, disciplined intensity",
    "榊原康政": "sturdy loyal face, plain honest bearing, dependable warrior air",
    "酒井忠次": "aged loyal veteran face, weathered calm, senior retainer dignity",
    "鸟居元忠": "devoted loyal face, plain rugged bearing, unwavering resolve",
    "本多正信": "scheming adviser face, thin sharp features, subtle cunning",
    "太原雪斋": "tonsured monk strategist face, wise calm eyes, devout shrewdness",
    "山本勘助": "misshapen weathered face, single eye, tactical genius air, grim determination",
    "马场信房": "aged loyal veteran face, white hair, steadfast courage",
    "山县昌景": "fierce red-armor commander face, battle-hardened glare",
    "内藤昌丰": "calm strategist face, composed dignity, senior officer air",
    "高坂昌信": "handsome loyal face, dignified composure, favored general air",
    "甘利虎泰": "fierce veteran face, sturdy build, loyal warhound air",
    "饭富虎昌": "stern veteran face, thick beard, loyal heavy-air general",
    "直江兼续": "proud young officer face, dignified loyalty, bold intelligence",
    "柿崎景家": "burly fierce warrior face, imposing physique, battle-hardened roar",
    "斋藤朝信": "calm sturdy face, composed loyalty, dependable air",
    "甘粕景持": "stern veteran face, sturdy build, steady courage",
    "小岛弥太郎": "fierce wild face, untamed warrior air, bold valor",
    "村上义清": "rugged mountain-lord face, bold white-bearded valor, unyielding pride",
    "真田信纲": "stern capable face, composed resolve, loyal commander air",
    "真田幸纲": "aged wily face, white hair, cunning endurance",
    "锅岛直茂": "stern capable face, composed ambition, loyal commander air",
    "锅岛清久": "aged sturdy face, weathered loyalty, senior officer dignity",
    "大友义统": "weak delicate noble face, refined but timid air",
    "岛津义弘": "fierce old bull face, weathered scarred dignity, unyielding war spirit",
    "岛津贵久": "stern founding-lord face, composed resolve, solid authority",
    "岛津家久": "young stern face, sharp tactical eyes, cool confidence",
    "岛津丰久": "impetuous young warrior face, bold fierce energy",
    "龙造寺隆信": "brutal bullish face, thick build, fearsome tiger-lord air",
    "锅岛胜茂": "stern young face, composed bearing, heir dignity",
    "相良义阳": "stern composed face, loyal resolve, regional lord dignity",
    "肝付兼续": "stern weathered face, unyielding country-lord air",
    "伊东义佑": "stern weathered face, rugged resolve, country-lord dignity",
    "秋月种实": "wily rugged face, thin mustache, shrewd country-lord air",
    "一条兼定": "weak decadent noble face, soft refined features, decline",
    "河野通宣": "stern weathered face, rugged resolve, island-lord air",
    "十河存保": "fierce capable face, composed valor, loyal commander air",
    "三好义继": "handsome young face, refined features, doomed nobility",
    "筒井顺庆": "wily portly face, shrewd calm eyes, political survivalist air",
    "松永长赖": "scheming young face, thin mustache, inherited cunning",
    "波多野秀治": "sturdy defiant face, proud resolve, mountain-lord air",
    "别所长治": "earnest young face, composed loyalty, doomed resolve",
    "赤井直正": "fierce scarred face, battle-hardened glare, iron-wall commander air",
    "小寺政职": "weak careful face, thin features, wavering loyalty",
    "六角义贤": "aged cultured face, thin refined features, fallen authority",
    "六角承祯": "cultured elderly face, scholarly refined air, faded glory",
    "京极高吉": "refined noble face, cultured composure, courtier dignity",
    "细川藤孝": "cultured poet-samurai face, elegant refined composure, literary grace",
    "筒井定次": "stern young face, composed bearing, heir dignity",
    "池田知正": "weak noble face, thin features, subordinate air",
    "和田惟政": "refined cultured face, courtier dignity, Christian lord air",
    "畠山高政": "stern capable face, composed resolve, declining-lord air",
    "田山义续": "sturdy face, dignified bearing, regional authority",
    "神保长职": "stern capable face, composed resolve, mountain authority",
    "椎名康胤": "wily face, thin mustache, scheming regional air",
    "上杉宪政": "aged refined face, elegant frail dignity, displaced lord",
    "长尾政景": "stern capable face, composed resolve, senior authority",
    "长尾景虎": "austere youthful warrior-monk face, devout intensity",
    "武田信虎": "aged fierce face, white beard, irascible authority",
    "武田义信": "stern dutiful young face, composed heir resolve",
    "武田胜赖": "stern young face, burning desperate resolve",
    "武田信繁": "calm composed noble face, loyal elegance",
    "穴山信君": "scheming face, thin mustache, self-serving air",
    "小山田信茂": "wily face, thin features, betrayer's caution",
    "饭尾连龙": "stern face, composed bearing, local authority",
    "德川信康": "stern dutiful young face, tragic resolve",
    "井伊直虎": "resolute woman-lord face, dignified female authority, composed leadership",
    "今川氏真": "decadent cultured face, refined weak air, poetry-loving lord",
    "朝比奈泰朝": "stern veteran face, loyal sturdy air, senior retainer dignity",
    "朝比奈泰能": "capable stern face, loyal resolve, officer air",
    "关盛信": "stern face, composed bearing, regional officer air",
    "太田道灌": "legendary aged strategist face, sharp calm eyes, elder wisdom",
    "太田资正": "stern loyal face, composed resolve, veteran officer air",
    "梶原景时": "stern face, composed bearing, officer air",
    "北条氏纲": "stern founding face, composed authority, sagacious rule",
    "北条氏邦": "capable stern face, composed resolve, officer dignity",
    "北条氏规": "stern composed face, loyal resolve, officer air",
    "北条氏尧": "elderly stern face, white hair, senior dignity",
    "北条幻庵": "aged white-bearded monk-samurai face, serene wisdom, crescent helmet crest",
    "风魔小太郎": "shadowy ninja face, obscured features, eerie menace",
    "松田宪秀": "stern capable face, composed bearing, officer air",
    "富永直胜": "stern face, sturdy build, officer air",
    "千叶亲泰": "stern face, composed bearing, local officer air",
    "里见义尧": "stern composed face, regional authority, steady rule",
    "里见义弘": "capable stern face, composed resolve, lord dignity",
    "里见义赖": "stern young face, composed bearing, heir dignity",
    "正木时茂": "stern veteran face, sturdy build, loyal courage",
    "正木时忠": "stern face, composed bearing, officer air",
    "武田信丰": "stern face, composed bearing, minor officer air",
    "小山义成": "stern face, composed bearing, officer air",
    "真里谷信隆": "stern face, composed bearing, local lord air",
    "佐野昌纲": "stern face, composed bearing, officer air",
    "佐竹义重": "fierce tiger-lord face, piercing eyes, bold authority",
    "佐竹义久": "capable stern face, composed resolve, loyal officer air",
    "佐竹义宣": "stern young face, composed bearing, heir dignity",
    "佐竹义斯": "stern face, composed bearing, minor officer air",
    "小野崎义昌": "stern face, composed bearing, officer air",
    "宇都宫国纲": "stern capable face, composed resolve, regional authority",
    "宇都宫广纲": "aged refined face, elegant bearing, cultural lord air",
    "芳贺高定": "stern capable face, composed resolve, officer dignity",
    "芳贺高继": "stern face, composed bearing, officer air",
    "那须资胤": "stern face, composed bearing, minor lord air",
    "大关高增": "stern face, sturdy build, officer air",
    "大田原资清": "stern face, composed bearing, officer air",
    "结城政胜": "stern capable face, composed resolve, officer dignity",
    "结城晴朝": "refined dignified face, cultured composure, noble authority",
    "小山高朝": "stern face, composed bearing, officer air",
    "皆川广照": "stern face, composed bearing, officer air",
    "藤田康邦": "stern face, composed bearing, officer air",
    "古河公方": "dignified shogunal face, formal court authority",
    "壬生纲房": "stern face, composed bearing, officer air",
    "大森义赖": "stern face, composed bearing, officer air",
    "长野业正": "aged wise commander face, white beard, legendary defense",
    "长野业盛": "stern young face, composed resolve, heir air",
    "那波显宗": "stern face, composed bearing, officer air",
    "横濑成繁": "stern face, composed bearing, officer air",
    "小田氏治": "stubborn stern face, unyielding resolve, surviving lord air",
    "多贺谷政经": "stern face, composed bearing, officer air",
    "水谷正村": "stern face, composed bearing, officer air",
    "下总三崎": "stern face, composed bearing, minor officer air",
    "百百纲基": "stern face, composed bearing, officer air",
    "里见忠义": "stern young face, composed bearing, heir air",
    "太田康资": "stern face, composed bearing, officer air",
    "太田资正嗣": "stern face, composed bearing, officer air",
}

# =====================================================================
# v3 家族配色表（surname → (armor 主色, 背景渐变色)）
# 让每张立绘有独立主色调，避免千篇一律。
# =====================================================================
FAMILY_COLORS = {
    "织田": ("black and crimson", "deep smoky crimson"),
    "木下": ("golden brown and black", "deep umber"),
    "丰臣": ("golden and crimson", "deep umber"),
    "羽柴": ("golden and black", "deep umber"),
    "德川": ("tea-brown and black", "deep chestnut"),
    "松平": ("tea-brown", "deep chestnut"),
    "武田": ("deep red", "dark crimson"),
    "上杉": ("white", "pale slate blue"),
    "长尾": ("white", "pale slate blue"),
    "伊达": ("black and gold", "deep indigo"),
    "北条": ("blue-black", "dark navy"),
    "今川": ("white and red", "pale rose"),
    "毛利": ("white and black", "deep slate gray"),
    "岛津": ("black", "dark charcoal"),
    "长宗我部": ("red and black", "dark oxblood"),
    "大友": ("white", "pale lavender"),
    "三好": ("crimson", "dark crimson"),
    "斋藤": ("black", "dark moss green"),
    "浅井": ("white and blue", "pale cerulean"),
    "朝仓": ("purple", "deep violet"),
    "本愿寺": ("white", "pale gold"),
    "佐竹": ("blue", "dark navy"),
    "最上": ("gold and red", "dark burnt orange"),
    "南部": ("violet-black", "deep violet"),
    "芦名": ("crimson", "dark crimson"),
    "相马": ("black", "dark slate"),
    "六角": ("purple", "deep violet"),
    "筒井": ("white", "pale gray"),
    "山名": ("crimson", "dark crimson"),
    "尼子": ("black", "dark moss green"),
    "宇喜多": ("red", "dark crimson"),
    "龙造寺": ("black", "dark gray"),
    "相良": ("red", "dark crimson"),
    "肝付": ("black", "dark slate"),
    "伊东": ("blue", "dark navy"),
    "秋月": ("red", "dark crimson"),
    "一条": ("white", "pale gold"),
    "河野": ("black", "dark slate"),
    "神保": ("blue", "dark navy"),
    "畠山": ("white and red", "pale rose"),
    "田山": ("white and red", "pale rose"),
    "结城": ("purple", "deep violet"),
    "宇都宫": ("black", "dark slate"),
    "佐野": ("red", "dark crimson"),
    "里见": ("white", "pale cerulean"),
    "正木": ("black", "dark slate"),
    "甲斐": ("red", "dark crimson"),
    "伊势": ("blue", "dark navy"),
    "波多野": ("black", "dark moss green"),
    "赤井": ("red", "dark crimson"),
    "别所": ("purple", "deep violet"),
    "小寺": ("black", "dark slate"),
    "北畠": ("white", "pale lavender"),
    "土岐": ("black", "dark slate"),
    "氏家": ("red", "dark crimson"),
    "大崎": ("black", "dark slate"),
    "留守": ("blue", "dark navy"),
    "石川": ("white", "pale gray"),
    "远藤": ("black", "dark slate"),
    "片仓": ("black and gold", "dark indigo"),
    "后藤": ("red", "dark crimson"),
    "铃木": ("black", "dark slate"),
    "津轻": ("gold and black", "deep umber"),
    "九户": ("blue-black", "dark navy"),
    "楯冈": ("crimson", "dark crimson"),
    "户泽": ("purple", "deep violet"),
    "秋田": ("gold and red", "dark burnt orange"),
    "鲑延": ("black", "dark slate"),
    "延泽": ("red", "dark crimson"),
    "志村": ("black", "dark slate"),
    "中野": ("blue", "dark navy"),
    "富田": ("red", "dark crimson"),
    "鲶贝": ("black", "dark slate"),
    "屋代": ("blue", "dark navy"),
    "原田": ("red", "dark crimson"),
    "鬼庭": ("black and gold", "dark indigo"),
    "桑折": ("blue", "dark navy"),
    "亘理": ("white and black", "deep slate gray"),
    "白石": ("white", "pale gray"),
    "田村": ("red", "dark crimson"),
    "二本松": ("black and gold", "dark indigo"),
    "冈本": ("purple", "deep violet"),
    "猪苗代": ("black", "dark slate"),
    "金上": ("red", "dark crimson"),
    "新田": ("blue", "dark navy"),
    "中目": ("black", "dark slate"),
    "牧野": ("red", "dark crimson"),
    "伊东": ("blue", "dark navy"),
    "石母田": ("black", "dark slate"),
    "守屋": ("red", "dark crimson"),
    "小梁川": ("black", "dark slate"),
    "白石": ("white", "pale gray"),
    "宫野": ("red", "dark crimson"),
    "成田": ("purple", "deep violet"),
    "安藤": ("blue", "dark navy"),
    "大草": ("black", "dark slate"),
    "笠原": ("red", "dark crimson"),
    "松田": ("black", "dark slate"),
    "远山": ("red", "dark crimson"),
    "大道寺": ("blue", "dark navy"),
    "富永": ("black", "dark slate"),
    "多目": ("red", "dark crimson"),
    "板部冈": ("purple", "deep violet"),
    "梶原": ("black", "dark slate"),
    "风魔": ("black", "dark gray"),
    "服部": ("black", "dark gray"),
    "柳生": ("black", "dark slate"),
    "九鬼": ("blue-black", "dark navy"),
    "伊贺崎": ("black", "dark gray"),
    "杂贺": ("black", "dark slate"),
    "石川": ("white", "pale gray"),
    "太原": ("white", "pale gold"),
    "山本": ("red", "dark crimson"),
    "马场": ("red", "dark crimson"),
    "山县": ("crimson", "dark crimson"),
    "内藤": ("red", "dark crimson"),
    "高坂": ("red", "dark crimson"),
    "甘利": ("red", "dark crimson"),
    "饭富": ("red", "dark crimson"),
    "直江": ("white and blue", "pale cerulean"),
    "柿崎": ("white", "pale slate blue"),
    "斋藤": ("black", "dark moss green"),
    "甘粕": ("white", "pale slate blue"),
    "小岛": ("white", "pale slate blue"),
    "村上": ("blue", "dark navy"),
    "真田": ("crimson", "dark crimson"),
    "锅岛": ("black", "dark slate"),
    "高桥": ("white", "pale lavender"),
    "立花": ("black and gold", "dark indigo"),
    "黑田": ("black", "dark slate"),
    "竹中": ("black", "dark slate"),
    "大谷": ("purple", "deep violet"),
    "井伊": ("crimson", "dark crimson"),
    "榊原": ("tea-brown", "deep chestnut"),
    "酒井": ("tea-brown", "deep chestnut"),
    "鸟居": ("tea-brown", "deep chestnut"),
    "本多": ("tea-brown", "deep chestnut"),
    "蒲生": ("purple", "deep violet"),
    "细川": ("white and purple", "pale lavender"),
    "高山": ("white", "pale gold"),
    "堀": ("blue", "dark navy"),
    "泷川": ("black", "dark slate"),
    "丹羽": ("gold and black", "deep umber"),
    "佐佐": ("crimson", "dark crimson"),
    "前田": ("crimson", "dark crimson"),
    "蜂须贺": ("black and gold", "deep umber"),
    "生驹": ("black", "dark slate"),
    "前野": ("red", "dark crimson"),
    "村井": ("blue", "dark navy"),
    "平手": ("black", "dark slate"),
    "佐久间": ("red", "dark crimson"),
    "池田": ("black and gold", "deep umber"),
    "加藤": ("crimson", "dark crimson"),
    "河尻": ("black", "dark slate"),
    "佐佐": ("crimson", "dark crimson"),
    "中村": ("blue", "dark navy"),
    "板垣": ("red", "dark crimson"),
    "长束": ("black", "dark slate"),
    "浅野": ("white and black", "deep slate gray"),
    "仙石": ("red", "dark crimson"),
    "可儿": ("red", "dark crimson"),
    "胁阪": ("blue", "dark navy"),
    "藤堂": ("purple", "deep violet"),
    "片桐": ("black and gold", "deep umber"),
    "森": ("crimson", "dark crimson"),
    "冈田": ("black", "dark slate"),
    "平野": ("red", "dark crimson"),
    "福岛": ("crimson", "dark crimson"),
    "山内": ("gold and black", "deep umber"),
    "石田": ("purple", "deep violet"),
    "大谷": ("purple", "deep violet"),
    "堀尾": ("blue", "dark navy"),
    "增田": ("black", "dark slate"),
    "长束": ("black", "dark slate"),
    "织田有乐": ("black and crimson", "deep smoky crimson"),
    "长谷川": ("blue", "dark navy"),
    "富田": ("red", "dark crimson"),
    "大野": ("black", "dark slate"),
    "木村": ("red", "dark crimson"),
    "小早川": ("black and gold", "dark indigo"),
    "羽柴": ("golden and black", "deep umber"),
    "丹羽": ("gold and black", "deep umber"),
    "神户": ("black", "dark slate"),
    "松永": ("black", "dark slate"),
    "别所": ("purple", "deep violet"),
    "三好": ("crimson", "dark crimson"),
    "波多野": ("black", "dark moss green"),
    "杂贺": ("black", "dark slate"),
    "筒井": ("white", "pale gray"),
    "足利": ("gold and black", "deep indigo"),
    "细川": ("white and purple", "pale lavender"),
    "京极": ("white", "pale lavender"),
    "六角": ("purple", "deep violet"),
    "百百": ("black", "dark slate"),
    "池田": ("black and gold", "deep umber"),
    "和田": ("white", "pale gold"),
    "高山": ("white", "pale gold"),
    "津田": ("black", "dark slate"),
    "三渊": ("white", "pale gray"),
    "畠山": ("white and red", "pale rose"),
    "田山": ("white and red", "pale rose"),
    "游佐": ("black", "dark slate"),
    "安宅": ("blue", "dark navy"),
    "盐川": ("red", "dark crimson"),
    "十河": ("crimson", "dark crimson"),
    "香西": ("purple", "deep violet"),
    "篠原": ("red", "dark crimson"),
    "小笠原": ("blue", "dark navy"),
    "仁木": ("black", "dark slate"),
    "赤松": ("red", "dark crimson"),
    "浦上": ("black", "dark slate"),
    "宇喜多": ("red", "dark crimson"),
    "明石": ("purple", "deep violet"),
    "小寺": ("black", "dark slate"),
    "上月": ("red", "dark crimson"),
    "山名": ("crimson", "dark crimson"),
    "垣屋": ("black", "dark slate"),
    "太田": ("blue", "dark navy"),
    "南条": ("red", "dark crimson"),
    "吉川": ("white and black", "deep slate gray"),
    "小早川": ("black and gold", "dark indigo"),
    "福原": ("white", "pale gray"),
    "口羽": ("white", "pale gray"),
    "天野": ("black", "dark slate"),
    "宍户": ("white", "pale gray"),
    "平贺": ("black", "dark slate"),
    "熊谷": ("red", "dark crimson"),
    "山中": ("crimson", "dark crimson"),
    "尼子": ("black", "dark moss green"),
    "龟井": ("red", "dark crimson"),
    "三泽": ("black", "dark slate"),
    "白井": ("white", "pale gray"),
    "富田": ("red", "dark crimson"),
    "土居": ("red and black", "dark oxblood"),
    "吉良": ("red and black", "dark oxblood"),
    "中村": ("blue", "dark navy"),
    "石野": ("black", "dark slate"),
    "安芸": ("red", "dark crimson"),
    "香宗我部": ("red and black", "dark oxblood"),
    "本山": ("black", "dark slate"),
    "池": ("blue", "dark navy"),
    "细川": ("white and purple", "pale lavender"),
    "仁保": ("red", "dark crimson"),
    "大友": ("white", "pale lavender"),
    "高桥": ("white", "pale lavender"),
    "田北": ("black", "dark slate"),
    "志贺": ("red", "dark crimson"),
    "户次": ("blue", "dark navy"),
    "立花": ("black and gold", "dark indigo"),
    "吉弘": ("white", "pale lavender"),
    "臼杵": ("purple", "deep violet"),
    "佐伯": ("blue", "dark navy"),
    "清田": ("red", "dark crimson"),
    "田原": ("black", "dark slate"),
    "伊集院": ("black", "dark charcoal"),
    "岛津": ("black", "dark charcoal"),
    "镰田": ("red", "dark crimson"),
    "比志岛": ("black", "dark charcoal"),
    "桦山": ("black", "dark charcoal"),
    "新纳": ("red", "dark crimson"),
    "川上": ("black", "dark charcoal"),
    "种子岛": ("blue", "dark navy"),
    "伊东": ("blue", "dark navy"),
    "相良": ("red", "dark crimson"),
    "犬童": ("black", "dark slate"),
    "上村": ("red", "dark crimson"),
    "东乡": ("black", "dark slate"),
    "入来院": ("red", "dark crimson"),
    "肝付": ("black", "dark slate"),
    "秃": ("red", "dark crimson"),
    "秋月": ("red", "dark crimson"),
    "筑紫": ("purple", "deep violet"),
    "原田": ("red", "dark crimson"),
    "宗像": ("white", "pale gray"),
    "麻生": ("black", "dark slate"),
    "大内": ("white", "pale gold"),
    "陶": ("red", "dark crimson"),
    "内藤": ("red", "dark crimson"),
    "杉": ("black", "dark slate"),
    "仁保": ("red", "dark crimson"),
    "吉见": ("white", "pale gray"),
    "益田": ("blue", "dark navy"),
    "周布": ("black", "dark slate"),
    "佐波": ("red", "dark crimson"),
    "三隅": ("black", "dark slate"),
    "都野": ("red", "dark crimson"),
    "益田": ("blue", "dark navy"),
    "石见": ("black", "dark slate"),
    "福屋": ("red", "dark crimson"),
    "因幡": ("blue", "dark navy"),
    "武田": ("deep red", "dark crimson"),
    "若狭": ("blue", "dark navy"),
    "逸见": ("black", "dark slate"),
    "朝仓": ("purple", "deep violet"),
    "越前": ("purple", "deep violet"),
    "朝井": ("black", "dark slate"),
    "安田": ("red", "dark crimson"),
    "鸟羽": ("blue", "dark navy"),
    "富田": ("red", "dark crimson"),
    "堀江": ("black", "dark slate"),
    "多贺": ("red", "dark crimson"),
    "若狭": ("blue", "dark navy"),
    "高桥": ("white", "pale lavender"),
    "上野": ("black", "dark slate"),
    "斋藤": ("black", "dark moss green"),
    "明智": ("blue and white", "pale cerulean"),
    "池田": ("black and gold", "deep umber"),
    "不破": ("black", "dark slate"),
    "远藤": ("black", "dark slate"),
    "氏家": ("red", "dark crimson"),
    "稻叶": ("purple", "deep violet"),
    "安藤": ("blue", "dark navy"),
    "堀": ("blue", "dark navy"),
    "稻叶": ("purple", "deep violet"),
    "关口": ("black", "dark slate"),
    "丸毛": ("red", "dark crimson"),
    "猪子": ("black", "dark slate"),
    "堀田": ("red", "dark crimson"),
    "佐藤": ("black", "dark slate"),
    "柴田": ("crimson", "dark crimson"),
    "泷川": ("black", "dark slate"),
    "佐佐": ("crimson", "dark crimson"),
    "前田": ("crimson", "dark crimson"),
    "金森": ("blue", "dark navy"),
    "原": ("black", "dark slate"),
    "长": ("red", "dark crimson"),
    "佐久间": ("red", "dark crimson"),
    "蜂屋": ("crimson", "dark crimson"),
    "丹羽": ("gold and black", "deep umber"),
    "木下": ("golden brown and black", "deep umber"),
    "羽柴": ("golden and black", "deep umber"),
    "堀尾": ("blue", "dark navy"),
    "中村": ("blue", "dark navy"),
    "一柳": ("black", "dark slate"),
    "生驹": ("black", "dark slate"),
    "沟口": ("red", "dark crimson"),
    "片桐": ("black and gold", "deep umber"),
    "浅野": ("white and black", "deep slate gray"),
    "大谷": ("purple", "deep violet"),
    "福岛": ("crimson", "dark crimson"),
    "加藤": ("crimson", "dark crimson"),
    "石田": ("purple", "deep violet"),
    "增田": ("black", "dark slate"),
    "长束": ("black", "dark slate"),
    "前田": ("crimson", "dark crimson"),
    "山内": ("gold and black", "deep umber"),
    "藤堂": ("purple", "deep violet"),
    "胁阪": ("blue", "dark navy"),
    "田中": ("black", "dark slate"),
    "分部": ("red", "dark crimson"),
    "木村": ("red", "dark crimson"),
    "平野": ("red", "dark crimson"),
    "可儿": ("red", "dark crimson"),
    "仙石": ("red", "dark crimson"),
    "筒井": ("white", "pale gray"),
    "松永": ("black", "dark slate"),
    "十河": ("crimson", "dark crimson"),
    "高山": ("white", "pale gold"),
    "蒲生": ("purple", "deep violet"),
    "细川": ("white and purple", "pale lavender"),
    "织田有乐": ("black and crimson", "deep smoky crimson"),
    "筒井": ("white", "pale gray"),
}

# 一般武将（无家族配色）的色板池 —— 按 id 哈希分配，保证相邻不雷同
PALETTE_POOL = [
    ("black", "dark slate"),
    ("red", "dark crimson"),
    ("blue", "dark navy"),
    ("purple", "deep violet"),
    ("tea-brown", "deep chestnut"),
    ("white and black", "deep slate gray"),
    ("black and gold", "dark indigo"),
    ("crimson", "dark oxblood"),
    ("dark green", "dark moss green"),
    ("golden brown", "deep umber"),
]

# 通用面部多样化池 —— 按 id 哈希分配，避免千人一面
HAIRSTYLE_POOL = [
    "traditional topknot with shaved pate",
    "neat topknot",
    "loose long hair tied back",
    "short cropped warrior hair",
    "topknot with loose side strands",
]
FACIAL_HAIR_POOL = [
    "clean-shaven",
    "thin mustache",
    "mustache and goatee",
    "full beard",
    "long beard",
    "stubble and mustache",
]
BUILD_POOL = [
    "sturdy build",
    "lean build",
    "heavy build",
    "average athletic build",
]

TAIL = ("soft cinematic lighting, warm amber color palette, "
        "detailed armor texture and fabric folds, sharp clean pixel edges, "
        "dramatic cinematic lighting, game character portrait")

# v2 统一风格段（2026-09-10 风格审查后固化）：
#   - 禁止铠甲/背景文字（此前 "clan of X" 被模型画成画面文字）
#   - 统一暖黄虚化渐变背景，避免偏冷/暗部具象化背景
#   - 刻意不加 bright well-lit / vivid saturated（实测会导致画面过亮过艳、与主流脱节）
STYLE_FIX = (" and warm amber gradient background, soft out-of-focus bokeh glow, "
             "no text, no kanji, no letters on armor or background")


def load():
    officers = json.load(open(os.path.join(ROOT, "data", "officers.json"), encoding="utf-8"))
    castles = json.load(open(os.path.join(ROOT, "data", "castles.json"), encoding="utf-8"))["castles"]
    provinces = json.load(open(os.path.join(ROOT, "data", "provinces.json"), encoding="utf-8"))["provinces"]
    return officers, castles, provinces


def province_name(o, castles, provinces):
    """officer.city → castles[city].province → provinces[idx].name
    ⚠️ officer['province'] 与国表索引对不上，勿直接用。"""
    city = o.get("city")
    if isinstance(city, int) and 0 <= city < len(castles):
        pi = castles[city].get("province")
        if isinstance(pi, int) and 0 <= pi < len(provinces):
            return provinces[pi].get("name") or "日本"
    return "日本"


def age_desc(o):
    by = o.get("birth_year")
    age = START_YEAR - by if isinstance(by, int) and by > 1000 else 30
    if not (14 <= age <= 80):
        age = 30
    if age < 20:
        return f"youthful, about {age} years old"
    if age <= 35:
        return f"in his prime, about {age} years old"
    if age <= 52:
        return f"middle-aged, about {age} years old"
    return f"elderly, about {age} years old"


def trait_desc(o):
    full = (o.get("surname", "") + o.get("given", ""))
    if full in FAMOUS_TRAITS:
        return FAMOUS_TRAITS[full]
    f = o.get("forces") or {}
    lead = f.get("lead", 0)
    martial = f.get("martial", 0)
    domestic = f.get("domestic", 0)
    diplomacy = f.get("diplomacy", 0)
    charm = f.get("charm", 0)
    parts = []
    if martial >= 85:
        parts.append("battle-worn armor, fierce expression, scars")
    elif martial >= 70:
        parts.append("seasoned warrior look, hardened gaze")
    if lead >= 80:
        parts.append("natural leader bearing, commanding presence, authoritative posture")
    if charm >= 80:
        parts.append("refined noble features, charismatic smile")
    if domestic >= 80:
        parts.append("scholarly air, court attire accents")
    if diplomacy >= 80:
        parts.append("composed diplomat, elegant manner")
    if not parts:
        parts.append("steadfast retainer, calm demeanor")
    return ", ".join(parts)


def build_prompt(o, castles, provinces):
    """v3.2 太阁5式提示词：
    1) 知名武将走 HISTORICAL_FACTS 专属史实特征（独眼/鹿角兜/赤甲白毛…）
    2) 配色走 FAMILY_COLORS（无则按 id 哈希从色板池选）→ 每张主色调不同
    3) 一般武将发型/胡型/体态按 id 哈希分配 → 避免千人一面
    4) 家徽走 FAMILY_CRESTS（史实家纹上甲；无则通用传统纹样）
    5) 画风「太阁5式·克制写实轻风格」（比 v3.1 少卡通、多史实，纯色渐变背景）
    """
    full = (o.get("surname", "") + o.get("given", ""))
    oid = int(o["id"])
    rank = RANK_DESC.get(o.get("rank_name") or "", "samurai retainer, serviceable armor")

    # 史实特征
    if full in HISTORICAL_FACTS:
        face_spec = HISTORICAL_FACTS[full]
    else:
        h = HAIRSTYLE_POOL[oid % len(HAIRSTYLE_POOL)]
        f = FACIAL_HAIR_POOL[(oid // 7) % len(FACIAL_HAIR_POOL)]
        b = BUILD_POOL[(oid // 13) % len(BUILD_POOL)]
        face_spec = f"{h}, {f}, {b}, weathered campaign-worn skin"

    # 配色
    fam = o.get("surname", "")
    if fam in FAMILY_COLORS:
        armor, bg = FAMILY_COLORS[fam]
    else:
        armor, bg = PALETTE_POOL[oid % len(PALETTE_POOL)]

    # 家徽（史实纹章上甲；未收录用通用传统纹样）
    sname = fam
    if full in FAMILY_CRESTS:
        crest = FAMILY_CRESTS[full]
    elif sname in FAMILY_CRESTS:
        crest = FAMILY_CRESTS[sname]
    else:
        crest = GENERIC_CREST
    crest_spec = f"{crest} emblazoned on the chest armor"

    # 表情/气质沿用数值 trait_desc（武勇/统率/魅力等）
    expr = trait_desc(o)

    return (f"Japanese historical portrait, 16th century Sengoku warlord, "
            f"half-body formal portrait, semi-realistic painted game-art portrait in "
            f"classic Japanese strategy game style, gentle stylized rendering with slight "
            f"anime-inspired charm, refined stylized eyes, clean crisp contours, "
            f"clean solid {bg} gradient background, "
            f"{age_desc(o)}, {rank.format(armor=armor)}, "
            f"{face_spec}, {crest_spec}, {expr}, balanced vivid historical colors, "
            f"soft studio lighting, dignified composition, no text, no letters, no kanji")


def tier_of(o):
    """生成优先级：1=可选主角 2=知名武将 3=大名 4=其余"""
    if o.get("is_selectable"):
        return 1
    arch = o.get("archetype_name") or ""
    if arch and not arch.startswith("一般"):
        return 2
    if (o.get("rank_name") or "") == "大名":
        return 3
    return 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0, help="只看优先级最高的 N 条")
    args = ap.parse_args()

    officers, castles, provinces = load()
    real = [o for o in officers if not o.get("is_placeholder")]

    items = []
    for o in real:
        oid = int(o["id"])
        name = o.get("surname", "") + o.get("given", "")
        # 新命名规则：{id}_{姓名}.png（无后缀是默认；多张候选时为 {id}_{姓名}-N.png）
        # done 检测同时认主名和 -N 后缀（旧式纯 {id}.png 不再视为已生成 → 需走 finalize 重命名）
        primary = f"{oid}_{name}.png"
        candidates = [primary] + [f"{oid}_{name}-{i}.png" for i in range(1, 10)]
        exists = any(os.path.exists(os.path.join(PORTRAIT_DIR, c)) for c in candidates)
        items.append({
            "id": oid,
            "name": name,
            "rank": o.get("rank_name") or "",
            "province": province_name(o, castles, provinces),
            "tier": tier_of(o),
            "prompt": build_prompt(o, castles, provinces),
            "out_file": primary,
            "status": "done" if exists else "pending",
        })

    items.sort(key=lambda x: (x["tier"], x["id"]))

    done = sum(1 for i in items if i["status"] == "done")
    ledger = {
        "meta": {
            "style": STYLE,
            "gen_size": GEN_SIZE,
            "final_size": list(FINAL_SIZE),
            "background": BACKGROUND,
            "negative": NEGATIVE,
            "out_dir": "assets/sprites/portraits/",
            "loader": "res://assets/sprites/portraits/{id}.png (src/render/asset_loader.gd)",
            "total": len(items),
            "done": done,
            "pending": len(items) - done,
            "note": ("文件名是 {id}.png 不是 full_XXXX.png；"
                     "国名走 city→castle.province，勿用 officer.province"),
        },
        "items": items,
    }
    json.dump(ledger, open(OUT_LEDGER, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"[gen_portrait_prompts] 台账写入 {OUT_LEDGER}")
    print(f"  总武将 {len(items)}  已生成 {done}  待生成 {len(items) - done}")
    for t in (1, 2, 3, 4):
        n = sum(1 for i in items if i["tier"] == t)
        print(f"  tier{t}: {n}")
    if args.top:
        print(f"\n== 优先级最高 {args.top} 条 ==")
        for i in items[:args.top]:
            print(f"  [{i['id']:>3}] {i['name']:<8} {i['rank']:<5} {i['province']:<5} {i['status']}")


if __name__ == "__main__":
    main()
