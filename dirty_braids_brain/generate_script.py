#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目：财经自媒体博主「投资 × 内容 × 认知」反馈系统
脚本 2：generate_script.py (自媒体文案对撞生成引擎)
重构版本功能：
    1. 加载全局基石配置：
       - config/persona.md (人设指南)
       - config/frameworks.md (投资框架)
       - config/Master_Rulebook.md (长期流量防雷法典)
    2. 自动载入最新输入：
       - 1_raw_data/ 最新的原始素材
       - 2_core_essence/ 最新的深度对撞核心精髓结论
    3. 短期语感自适应学习 (Few-shot 强化学习)：
       - 自动遍历 3_history_scripts/ 下的所有子文件夹
       - 提取最新的 3 个子文件夹，成对提取并拼装 v1_AI.md 与 v2_Ryan.md 作为修改对照样本
    4. 自动调用 Gemini 2.5 Flash API (支持新旧 SDK 智能兼容与 Mock 本地降级)
    5. 正则剥离 <CognitiveCard> 认知卡片并存入 4_cognitive_cards/
    6. [强化学习闭环]：自动在 3_history_scripts/ 下为本次创作创建新子目录 `{主题}_{日期}`，
       并自动将本次生成的纯净初稿保存为 v1_AI.md，静候博主在同目录下编写 v2_Ryan.md。
"""

import os
import re
import sys
import glob
import argparse
from datetime import datetime

# ----------------- 自动寻路加载本地 .env 配置文件 -----------------
def load_env_file():
    """自动检测并加载当前目录、脚本目录或上级目录下的 .env 环境变量文件"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_paths = [
        os.path.join(base_dir, ".env"),
        os.path.join(base_dir, "..", ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "dirty_braids_brain", ".env"),
    ]
    for path in env_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            os.environ[k.strip()] = v.strip()
                break
            except Exception:
                pass

# 执行加载
load_env_file()

# ----------------- Gemini SDK 智能适配与兼容层 -----------------
GEMINI_METHOD = None
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

try:
    from google import genai
    from google.genai import types
    GEMINI_METHOD = "new_sdk"
except ImportError:
    try:
        import google.generativeai as genai_legacy
        GEMINI_METHOD = "legacy_sdk"
    except ImportError:
        GEMINI_METHOD = "unavailable"


def load_config_file(filepath):
    """加载文本配置文件"""
    if not os.path.exists(filepath):
        print(f"[-] 警告：找不到配置文件: {filepath}")
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def get_latest_raw_data(raw_data_dir):
    """自动获取 1_raw_data/ 下最新修改的原始素材"""
    if not os.path.exists(raw_data_dir):
        os.makedirs(raw_data_dir, exist_ok=True)
        return "", "无素材"

    txt_files = glob.glob(os.path.join(raw_data_dir, "*.txt")) + glob.glob(os.path.join(raw_data_dir, "*.md"))
    if not txt_files:
        return "", "无素材"

    # 获取最新修改的文件
    txt_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = txt_files[0]
    print(f"[+] 自动检测到最新的原始素材: {os.path.basename(latest_file)}")
    
    with open(latest_file, "r", encoding="utf-8") as f:
        return f.read(), os.path.basename(latest_file)


def get_source_label(filename):
    """智能解析提取素材的文本主题标签，过滤日期和常见前缀，用于智能匹配与子目录建档"""
    name = filename.lower()
    for ext in ['.txt', '.md', '_raw']:
        name = name.replace(ext, "")
    name = name.replace("dialogue_log_", "").replace("essence_", "")
    # 正则清洗 YYYYMMDD 及 YYYYMMDD_HHMMSS 格式的时间戳
    name = re.sub(r'\d{8}(_\d{6})?', '', name)
    # 清洗多余的下划线
    name = re.sub(r'_+', '_', name).strip('_')
    return name.upper() if name else "TOPIC"


def get_paired_essence(essence_dir, source_label):
    """
    智能精髓结论匹配引擎：
    根据当前素材的主题标签（source_label），在 2_core_essence/ 下智能寻找包含该主题关键字的讨论文件，
    实现精准对撞。若无匹配，降级为读取修改时间最新的精髓文件。
    """
    if not os.path.exists(essence_dir):
        os.makedirs(essence_dir, exist_ok=True)
        return "", "无"

    essence_files = glob.glob(os.path.join(essence_dir, "*.txt")) + glob.glob(os.path.join(essence_dir, "*.md"))
    if not essence_files:
        return "", "无"

    # 提取提取出 source_label 里的关键字
    label_lower = source_label.lower()
    keywords = [k for k in label_lower.split('_') if len(k) > 1]
    
    # 增加金融缩写词智能匹配（如 WMT ➔ walmart，AAPL ➔ apple）
    if 'wmt' in label_lower:
        keywords.append('walmart')
    elif 'walmart' in label_lower:
        keywords.append('wmt')

    matched_files = []
    for f in essence_files:
        f_lower = os.path.basename(f).lower()
        if any(kw in f_lower for kw in keywords):
            matched_files.append(f)

    if matched_files:
        # 如果找到匹配的文件，取其中修改时间最新的
        matched_files.sort(key=os.path.getmtime, reverse=True)
        latest_match = matched_files[0]
        print(f"[+] 🎯 智能匹配：检测到与素材 [{source_label}] 相关的专属讨论精髓: {os.path.basename(latest_match)}")
        with open(latest_match, "r", encoding="utf-8") as file:
            return file.read(), os.path.basename(latest_match)

    # 无匹配时，降级读取最新的
    essence_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = essence_files[0]
    print(f"[+] ⚠️ 提示：未找到与 [{source_label}] 相关的专属对撞结论。降级使用最新讨论精髓: {os.path.basename(latest_file)}")
    with open(latest_file, "r", encoding="utf-8") as f:
        return f.read(), os.path.basename(latest_file)


def get_new_few_shot_samples(history_dir):
    """
    自适应强化语感读取逻辑：
    遍历 3_history_scripts/ 下的所有子文件夹，按修改时间倒序，获取最新的 3 个子文件夹。
    在每个子文件夹中成对读取 v1_AI.md (初稿) 和 v2_Ryan.md (精修终稿)，拼装为 Few-shot 语料。
    """
    if not os.path.exists(history_dir):
        os.makedirs(history_dir, exist_ok=True)
        return ""

    # 遍历获取所有子文件夹
    subdirs = [os.path.join(history_dir, d) for d in os.listdir(history_dir)
               if os.path.isdir(os.path.join(history_dir, d)) and not d.startswith('.')]

    if not subdirs:
        print("[-] 提示：3_history_scripts/ 下尚无历史对比子目录。将仅基于人设和法则进行生成。")
        return ""

    # 按照子文件夹中文件的最后修改时间（或者子目录本身的修改时间）进行倒序排序
    subdirs.sort(key=os.path.getmtime, reverse=True)
    latest_3_dirs = subdirs[:3]

    print("[+] 开始从历史成片库中提取最新的 3 次「AI初稿 V1 ➔ 终稿 V2」修改样本进行语感对照学习:")
    few_shot_prompt = "\n===【语感强化对比学习：以下是博主最近 3 次的初稿(V1)与最终人工精修终稿(V2)的修改对照】===\n"
    few_shot_prompt += "【请仔细揣摩：博主是如何大刀阔斧地删减AI虚浮废话、把句子改得极度短小口语化、以及增强真实美国生活/物理体感的】\n\n"

    count = 0
    for s_dir in latest_3_dirs:
        dir_name = os.path.basename(s_dir)
        v1_path = os.path.join(s_dir, "v1_AI.md")
        v2_path = os.path.join(s_dir, "v2_Ryan.md")

        if os.path.exists(v1_path) and os.path.exists(v2_path):
            count += 1
            print(f"    -> 成功装载修改样本 {count}: {dir_name}")
            with open(v1_path, "r", encoding="utf-8") as f1, open(v2_path, "r", encoding="utf-8") as f2:
                v1_text = f1.read()
                v2_text = f2.read()
                few_shot_prompt += f"【修改对照案例 {count}：{dir_name}】\n"
                few_shot_prompt += f"--- 你的粗糙初稿 (v1_AI.md) ---\n{v1_text}\n\n"
                few_shot_prompt += f"--- 我的发布终稿 (v2_Ryan.md) ---\n{v2_text}\n"
                few_shot_prompt += f"========================================================================\n\n"

    if count == 0:
        print("[-] 提示：虽然找到了子文件夹，但其中未能提取出成对的 v1_AI.md 和 v2_Ryan.md。")
        return ""

    return few_shot_prompt


def extract_cognitive_cards(response_text, cards_dir, source_topic):
    """
    从模型输出中正则提取被 <CognitiveCard> 标签包裹的认知卡片
    将其完美剥离后，自动写入 4_cognitive_cards/
    """
    os.makedirs(cards_dir, exist_ok=True)

    # 提取 <CognitiveCard> 标签中的内容
    cards = re.findall(r'<CognitiveCard>(.*?)</CognitiveCard>', response_text, re.DOTALL)

    # 从主生成物中彻底剔除标签及卡片内容，换取绝对纯净的口播逐字稿
    clean_script = re.sub(r'<CognitiveCard>.*?</CognitiveCard>', '', response_text, flags=re.DOTALL).strip()
    clean_script = re.sub(r'\n{3,}', '\n\n', clean_script)

    if not cards:
        print("[-] 提示：未在生成内容中解析到被 <CognitiveCard> 标签包裹的认知卡片。")
        return clean_script, 0

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    card_filename = f"card_{timestamp}_{source_topic}.md"
    card_path = os.path.join(cards_dir, card_filename)

    card_content = f"# 认知提炼自：{source_topic}\n"
    card_content += f"沉淀时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    card_content += "---\n\n"

    for idx, card in enumerate(cards):
        card_clean = card.strip()
        card_content += f"### 💡 硬核认知卡片 {idx+1}\n{card_clean}\n\n---\n\n"

    with open(card_path, "w", encoding="utf-8") as f:
        f.write(card_content)

    print(f"[+] 成功剥离出 {len(cards)} 条投资认知卡片，已自动归档至: 4_cognitive_cards/{card_filename}")
    return clean_script, len(cards)


def call_gemini_api(system_instruction, user_prompt):
    """
    调用 Gemini 2.5 Flash API。
    自动兼容新老 SDK 与 Mock 优雅降级。
    """
    if not GEMINI_API_KEY:
        print("\n" + "="*80)
        print("[-] 警告：未检测到系统的 GEMINI_API_KEY 环境变量！")
        print("    请在 dirty_braids_brain/.env 文件中正确配置 API KEY。")
        print("    系统目前已自动为您开启 [高仿真 Mock 本地演练模式]...")
        print("="*80 + "\n")
        return get_mock_response(user_prompt)

    if GEMINI_METHOD == "new_sdk":
        print("[+] 正在使用全新 google-genai SDK 接口与 Gemini 2.5 Flash 通信...")
        try:
            client = genai.Client()
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            print(f"[-] 调用最新 SDK 失败 ({e})，正在尝试回退至经典 SDK...")

    if GEMINI_METHOD == "legacy_sdk" or GEMINI_METHOD == "new_sdk":
        print("[+] 正在使用经典 google-generativeai 接口与 Gemini 2.5 Flash 通信...")
        try:
            genai_legacy.configure(api_key=GEMINI_API_KEY)
            model = genai_legacy.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            response = model.generate_content(
                user_prompt,
                generation_config={"temperature": 0.7}
            )
            return response.text
        except Exception as e:
            print(f"[-] 经典接口调用亦失败 ({e})。自动降级至 Mock 模式...")
    else:
        print("[-] 未检测到任何 Google AI 依赖包。即将为您展示高质量的 Mock 脚本。")

    return get_mock_response(user_prompt)


def get_mock_response(user_prompt):
    """当无 API Key 或网络失败时，返回高仿真的 Mock 对撞成文案，确保演示丝滑"""
    return """# 沃尔玛大涨背后的残酷真相：中产阶级的“防御性位移”

今天不跟大家聊那些花里胡哨的宏观财报公式，只聊一个这周我去超市买牛肉碰出来的真实体感。

沃尔玛刚发了最新的财报，数字大涨，华尔街一片欢呼，觉得美国消费依然韧性十足。
但我建议你先冷下来，把这层皮剥掉，看一看物理世界的资金流向。

财报里有个极度关键的细节：沃尔玛本季度大涨的营收里，有超过 60% 都是来自年收入 10 万美金以上的高收入中产家庭。
这正常吗？这根本不是消费强劲，这叫商超行业的“防御性位移”。
说句人话，就是原本在 Whole Foods 闭眼买高端有机食品的中产，现在也开始精打细算，被迫跑到沃尔玛来抢大包装的自营平价鸡肉和面包了。

上周我跟在德州搞食品分销的一个兄弟聊。他跟我透露，沃尔玛的自营品牌 Great Value 本季度销量直接爆棚。这说明美国人现在连品牌溢价都不要了，彻底退守到了极致的实用主义防线。

而且更深的一层是，沃尔玛现在根本不是一家简单的商超，它在加速利用“Walmart+”会员锁死用户。这和巴菲特说的 Costco 会员逻辑如出一辙。你交了 98 美金的年票，你就彻底被锁死在了它的免邮和配送飞轮里，转换成本高得吓人。

所以，别看着降息预期来了就跟风乱投。
在全球中枢利率依然偏紧的这几年，拥抱像沃尔玛、Costco 这种能帮老百姓省钱、自由现金流极其强悍的“全天候收租型大印钞机”，才是咱们普通人唯一的防守底牌。下期聊。

<CognitiveCard>
**商超行业的“防御性位移”是通胀渗透的终极滞后指标。**
华尔街看宏观只盯着冷冰冰的零售销售总额，觉得只要总额在涨，消费就安全。但真正的供应链冷暖在“购物车结构”。高净值中产家庭向低毛利商超（如沃尔玛）进行大比例位移，说明中产层级的实质性消费降温已经见底。投资必须紧跟这种“消费层级退守”的一线方向。
</CognitiveCard>

<CognitiveCard>
**“Walmart+”是沃尔玛在数字时代挖出的第二条无形护城河。**
它利用高复购率与极低数字边际成本，将传统的货架销售升华为“年费收租模型”。98 美金的会员年费锁定的是用户的无限次黏性。在去库存逆风期，会员制构筑了极高壁垒的“高转换成本”，也是抵御 Amazon 蚕食最硬的底牌。
</CognitiveCard>

<CognitiveCard>
**抛弃任何不带定价权的泡沫型垃圾消费股。**
在这个现金重回王者的周期中，只有能像沃尔玛一样依靠极致 SKU 采购规模拿到全行最低批发价、形成成本碾压、并能稳定输出自由现金流的企业才能活得极度滋润。没有高壁垒和定价权的小消费个股，会在通缩和降级双重逆风里一两季度内直接归零。
</CognitiveCard>
"""


def main():
    parser = argparse.ArgumentParser(description="「投资 × 内容 × 认知」核心对撞机文案生成器 (V2)")
    parser.add_argument("--input", type=str, default="", help="指定 1_raw_data/ 下特定的素材文件名，或传入绝对/相对文件路径")
    parser.add_argument("--essence", type=str, default="", help="指定 2_core_essence/ 下特定的讨论结论文件名，实现专属精准对撞")
    parser.add_argument("--idea", type=str, default="", help="博主当前的灵感想法或视频切入点")
    args = parser.parse_args()

    # 确定各重构目录路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, "config")
    dialogue_logs_dir = os.path.join(base_dir, "0_dialogue_logs")
    raw_data_dir = os.path.join(base_dir, "1_raw_data")
    essence_dir = os.path.join(base_dir, "2_core_essence")
    history_dir = os.path.join(base_dir, "3_history_scripts")
    cards_dir = os.path.join(base_dir, "4_cognitive_cards")

    # 1. 自动读取全局基石配置与长期记忆
    persona = load_config_file(os.path.join(config_dir, "persona.md"))
    frameworks = load_config_file(os.path.join(config_dir, "frameworks.md"))
    master_rulebook = load_config_file(os.path.join(config_dir, "Master_Rulebook.md"))

    if not persona or not frameworks or not master_rulebook:
        print("[-] 错误：无法完整读取全局基石配置！请确保 config/ 下含有 persona.md, frameworks.md, Master_Rulebook.md")
        sys.exit(1)

    # 2. 自动载入最新输入底料：原材料与核心讨论精髓结论
    raw_data = ""
    source_label = "MANUAL"
    if args.input:
        # 防护性路径兼容：支持直接传入绝对/相对路径，或仅传入 1_raw_data 下的文件名
        if os.path.exists(args.input):
            input_path = args.input
        else:
            input_path = os.path.join(raw_data_dir, args.input)

        if os.path.exists(input_path):
            with open(input_path, "r", encoding="utf-8") as f:
                raw_data = f.read()
            source_label = get_source_label(os.path.basename(input_path))
            print(f"[+] 成功读取指定的素材文件: {input_path}")
        else:
            print(f"[-] 警告：指定的素材文件 {args.input} 不存在，切换为自动寻找 1_raw_data/ 最新素材。")

    if not raw_data:
        raw_data, filename = get_latest_raw_data(raw_data_dir)
        if raw_data:
            source_label = get_source_label(filename)

    if not raw_data:
        raw_data = "[无最新输入原材料：系统将仅依靠你的想法 and 你的讨论精髓直接对撞生成]"
        source_label = "RAW_THOUGHT"

    # 获取核心讨论精髓结论：优先采用指定参数，未指定时采用智能对撞匹配
    core_essence = ""
    essence_filename = "未指定"
    if args.essence:
        essence_path = os.path.join(essence_dir, args.essence)
        if not os.path.exists(essence_path) and os.path.exists(args.essence):
            essence_path = args.essence
            
        if os.path.exists(essence_path):
            with open(essence_path, "r", encoding="utf-8") as f_ess:
                core_essence = f_ess.read()
            essence_filename = os.path.basename(essence_path)
            print(f"[+] 🎯 成功读取指定的讨论精髓文件: {essence_filename}")
        else:
            print(f"[-] 警告：指定的讨论精髓文件 {args.essence} 不存在，启动自动智能匹配...")

    if not core_essence:
        core_essence, essence_filename = get_paired_essence(essence_dir, source_label)

    if not core_essence:
        core_essence = "[无最新的对撞精髓：系统将仅基于原始数据和你的实时想法进行生成]"
        essence_filename = "无对撞精髓"

    # 3. 提取最新的 3 篇 V1/V2 语感成对样本进行强化学习 (短期记忆)
    few_shot_data = get_new_few_shot_samples(history_dir)

    # 4. 构建 System Instruction (全局指导红线)
    system_instruction = f"""
你是一个具备极高宏观经济认知、身处美国拥有真实生活体感的财经自媒体主理人。
你的目标是：把枯燥的财务/宏观数据，通过你独特的第一人称物理哨兵体感和巴菲特投资框架，重组为高语言密度、口语化极强、情绪饱满但严谨理性的视频逐字口播稿。

【你的核心人设与分析框架】：
{persona}
{frameworks}

【你绝对不可触碰的流量法则与避坑红线 (Master Rulebook)】：
{master_rulebook}

【语感强化对照表】：
下面是我最近 3 次在子文件夹中保留的修改对比记录。请你以敏锐的嗅觉，仔细观察我是如何疯狂删减你的修饰废话、如何把长句拆成利落的短句、以及我是如何在 V2 终稿中塞入最接地气的美国一线供应链物理体感的。
你本次生成的初稿文案，必须直接、尽最大可能逼近 V2 Ryan 的说话腔调！
"""

    # 5. 构建 User Prompt
    user_prompt = f"""
{few_shot_data}

========================================================================
【本次创作指定的原始素材数据】
{raw_data}

【博主与网页版 AI 深度讨论后提炼的“核心精髓结论”】
{core_essence}

【博主当前的实时内容侧重点与切入灵感】
{args.idea if args.idea else "请将上面的核心精髓与原始财务数据进行深度对撞，帮我写出一份有极高第一视角故事张力和长期防守认知的爆款口播稿。"}
========================================================================

【你现在的具体写作任务】：
请你严格输出两个部分，格式必须清晰对齐：

1. 一份可以直接面对镜头录音的视频逐字口播稿（直接进入正题，以 Master Rulebook 里的黄金起手式开头，彻底消灭 AI 腔调）。
2. 从中提炼出 3 条纯粹的 Markdown 格式“硬核投资认知卡片”。

【认知卡片格式容错规范】：
每一条认知卡片，必须严格、单独使用 `<CognitiveCard>` 和 `</CognitiveCard>` 标签包裹起来。例如：
<CognitiveCard>
**卡片标题**
卡片具体观点内容...
</CognitiveCard>

千万不要将卡片写入你的主文案中，必须严格隔离在标签里！主文案里绝对不能含有任何 `<CognitiveCard>` 标签。
"""

    print("[+] 正在召唤全新 Gemini 2.5 Flash 核心对撞机，启动长期与短期语感混合推理...")
    
    # 6. 调用 API 生成
    raw_response = call_gemini_api(system_instruction, user_prompt)

    # 7. 正则剥离认知卡片
    clean_script, num_cards = extract_cognitive_cards(raw_response, cards_dir, source_label)

    # 8. [长期强化学习闭环]：自动在 3_history_scripts 下创建本次创作的主题子文件夹
    timestamp_dir = datetime.now().strftime('%Y%m%d_%H%M%S')
    topic_folder_name = f"{source_label}解析_{timestamp_dir}"
    target_folder_path = os.path.join(history_dir, topic_folder_name)
    os.makedirs(target_folder_path, exist_ok=True)

    # 将剥离标签后的干净初稿写入该文件夹的 v1_AI.md 中，供博主精修
    v1_file_path = os.path.join(target_folder_path, "v1_AI.md")
    with open(v1_file_path, "w", encoding="utf-8") as f_v1:
        f_v1.write(clean_script)

    # 9. 自动保存本次的 dialogue logs (深度讨论完整思考过程日志)
    log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"dialogue_log_{log_timestamp}_{source_label}.txt"
    log_filepath = os.path.join(dialogue_logs_dir, log_filename)
    
    with open(log_filepath, "w", encoding="utf-8") as f_log:
        f_log.write(f"=== SYSTEM INSTRUCTION ===\n{system_instruction}\n\n")
        f_log.write(f"=== USER PROMPT ===\n{user_prompt}\n\n")
        f_log.write(f"=== MODEL RAW RESPONSE ===\n{raw_response}\n")

    print("\n" + "="*40 + " [生成完成的去AI味纯视频逐字稿] " + "="*40)
    print(clean_script)
    print("="*105)
    print(f"[+] 视频逐字稿已自动归档至: 3_history_scripts/{topic_folder_name}/v1_AI.md (请直接去该文件夹下编写您的微调版本 v2_Ryan.md)")
    print(f"[+] 3 张认知卡片已自动剥离并沉淀至 4_cognitive_cards 目录下")
    print(f"[+] 本次对话运行日志已记录在: 0_dialogue_logs/{log_filename}")


if __name__ == "__main__":
    main()
