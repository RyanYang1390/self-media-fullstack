#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目：财经自媒体博主「投资 × 内容 × 认知」反馈系统
脚本 3：audit_performance.py (多模态周期复盘引擎)
功能：
    - 预留使用 yt-dlp 抓取 YouTube/Bilibili 链接并一键提取本地 .mp3 的工具接口
    - 接受本地音频文件路径，以及视频表现数据 (包含完播率、播放量、前5秒流失率等指标)
    - 兼容调用 Google GenAI 最新 SDK (上传音频文件) 进行多模态长上下文分析
    - 模型根据音频表达节奏、语气语调，对照流失率数据，生成带有精准时间戳的“表达诊断报告”
    - 自动将复盘诊断报告存储至 5_audit_reports/ 目录，形成“内容-表现-认知”的双向反馈闭环
"""

import os
import sys
import json
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

# 1. 尝试导入最新的 google-genai SDK
try:
    from google import genai
    from google.genai import types
    NEW_SDK_AVAILABLE = True
except ImportError:
    NEW_SDK_AVAILABLE = False

# 2. 尝试导入传统的 google-generativeai SDK
try:
    import google.generativeai as genai_legacy
    LEGACY_SDK_AVAILABLE = True
except ImportError:
    LEGACY_SDK_AVAILABLE = False

# 3. 抉择最优的调用通道
if NEW_SDK_AVAILABLE:
    GEMINI_METHOD = "new_sdk"
elif LEGACY_SDK_AVAILABLE:
    GEMINI_METHOD = "legacy_sdk"
else:
    GEMINI_METHOD = "unavailable"


def setup_directories():
    """确保所需的本地目录均已创建"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(base_dir, "5_audit_reports")
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


def convert_video_link_to_mp3(video_url, output_dir):
    """
    预留工具函数：使用 yt-dlp 抓取视频并自动提取为本地高保真 .mp3 音频
    以便博主直接输入视频链接即可进行音频复盘
    """
    print(f"[+] 预备抓取视频链接: {video_url}")
    
    # 尝试导入 yt_dlp，未安装则打印指导
    try:
        import yt_dlp
    except ImportError:
        print("[-] 提示：未安装 yt-dlp。如果需要直接抓取视频，请在终端运行：")
        print("    pip install yt-dlp")
        print("    并确保系统安装了 ffmpeg (brew install ffmpeg)")
        return ""

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_template = os.path.join(output_dir, f"downloaded_{timestamp}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
    }
    
    try:
        print("[+] 正在调用 yt-dlp 和 ffmpeg 提取高音质音频...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            # 由于 ffmpeg 转换后后缀变为了 .mp3，做下替换
            mp3_filename = os.path.splitext(filename)[0] + ".mp3"
            print(f"[+] 音频提取成功！本地路径: {mp3_filename}")
            return mp3_filename
    except Exception as e:
        print(f"[-] 调用 yt-dlp 提取音频失败，报错: {e}")
        return ""


def call_gemini_audio_audit(audio_path, metrics_data, system_instruction, user_prompt):
    """
    上传音频并调用 Gemini API 进行多模态听音复盘。
    在没有配置 API 或本地无音频时，自动降级至高质量 Mock 复盘报告。
    """
    if not GEMINI_API_KEY:
        print("\n" + "="*80)
        print("[-] 警告：未检测到系统的 GEMINI_API_KEY 环境变量！")
        print("    系统目前已自动为您开启 [高仿真 Mock 多模态听音复盘模式]...")
        print("="*80 + "\n")
        return get_mock_audit_report(metrics_data)

    if not audio_path or not os.path.exists(audio_path):
        print(f"[-] 警告：未提供有效的本地音频文件路径或文件不存在。")
        print("    系统自动降级至 Mock 复盘分析演示...")
        return get_mock_audit_report(metrics_data)

    if GEMINI_METHOD == "new_sdk":
        print(f"[+] 正在使用全新 google-genai SDK 上传本地音频: {audio_path}")
        try:
            client = genai.Client()
            # 1. 上传音频文件到 Google Gemini 服务器 (适合长音频/多模态分析)
            print("[+] 正在将音频上传至 Gemini 临时云存储中，请稍候...")
            audio_file = client.files.upload(file=audio_path)
            print(f"[+] 上传成功！Gemini 文件 URI: {audio_file.uri}")
            
            # 2. 结合音频和指标数据进行多模态分析
            print("[+] 正在启动多模态长上下文分析，让模型“听”音频并对照流失率曲线...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[audio_file, user_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4, # 复盘诊断建议偏严谨，温度设低
                )
            )
            
            # 3. 诊断完成后，在 Gemini 端清理上传的文件
            try:
                client.files.delete(name=audio_file.name)
                print("[+] 已安全清理 Gemini 端的临时音频缓存。")
            except Exception as delete_error:
                print(f"[-] 清理临时音频缓存失败: {delete_error}")
                
            return response.text
            
        except Exception as e:
            print(f"[-] 全新 SDK 上传音频失败 ({e})，正在尝试经典 SDK...")
            
    if LEGACY_SDK_AVAILABLE:
        print(f"[+] 正在使用经典 google-generativeai 上传本地音频: {audio_path}")
        try:
            genai_legacy.configure(api_key=GEMINI_API_KEY)
            print("[+] 正在使用传统接口上传音频文件...")
            audio_file = genai_legacy.upload_file(path=audio_path)
            print(f"[+] 上传成功！Gemini 文件 URI: {audio_file.uri}")
            
            model = genai_legacy.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            
            print("[+] 正在启动经典接口的多模态长上下文听音分析...")
            response = model.generate_content(
                [audio_file, user_prompt],
                generation_config={"temperature": 0.4}
            )
            
            # 清理文件
            try:
                genai_legacy.delete_file(name=audio_file.name)
            except:
                pass
                
            return response.text
        except Exception as e:
            print(f"[-] 经典接口上传音频亦失败 ({e})。自动降级至 Mock 模式...")
    else:
        print("[-] 未检测到经典 Google AI 依赖包。即将为您展示高质量的 Mock 复盘诊断报告。")

    return get_mock_audit_report(metrics_data)


def get_mock_audit_report(metrics_data):
    """当无 API Key 或本地无音频时，提供极具专业水准的高仿真 Mock 听音诊断报告"""
    views = metrics_data.get("views", 12000)
    retention_5s = metrics_data.get("retention_5s", 0.45)
    completion_rate = metrics_data.get("completion_rate", 0.18)
    
    return f"""# 多模态音频复盘与诊断报告 (物理世界听音反馈)

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================================================

## 1. 核心表现数据分析 (Metrics Overview)
*   **本期视频播放量 (Views)**: {views}
*   **前 5 秒保留率 (5s Retention)**: {retention_5s * 100:.1f}% (⚠️ 存在预警，行业优秀线通常为 60%-70%)
*   **全片完播率 (Completion Rate)**: {completion_rate * 100:.1f}% (中规中矩)

---

## 2. 多模态表达诊断 (Speech & Tone Diagnostics)
模型通过对博主视频音频的深度声学特征、语气节奏、以及台词文本流失率进行交叉对撞，诊断出以下核心表达硬伤与亮点：

### 🚨 黄金 5 秒流失率暴跌诊断 (00:00 - 00:05)
*   **流失现象**：开场 5 秒内，有将近 {100 - retention_5s * 100:.1f}% 的观众直接滑走。
*   **音频听音诊断**：
    *   **声学特征**：开头的第 1 到第 3 秒，博主深吸了一口气，且说话前有明显的“呃，今天...”的吞吐感。背景噪音在没有说话的间隙被放大，说明底噪降噪没有处理好。
    *   **表达痛点**：语气过平，缺乏一种“有重大硬核事件发生”的紧迫感。
    *   **优化改进 [带时间戳]**：
        *   `[00:01]` 剪辑时必须直接把深呼吸和“呃”等语气词全部**无缝切掉 (Jump Cut)**。
        *   `[00:02]` **声调需要拔高 15%**。开场的第一句必须是一句极其抓人眼球的设问短句（例如：“美联储降息的大闸开了，但我的德州供应链兄弟却在疯狂裁员，这正常吗？”），而不是慢条斯理地打招呼。

### ⚠️ 内容节奏拖沓期诊断 (01:20 - 02:40)
*   **流失现象**：流失率曲线在此区间出现了一个比较平缓但持续下滑的“小滑梯”。
*   **音频听音诊断**：
    *   **语速监测**：此区间的平均语速下降到了每分钟 210 字左右（全片平均 250 字）。博主在念到“关于美国国债收益率的推导公式”时，语调变得像教科书，失去了咖啡馆里和老友聊天的轻松感。
    *   **AI味死灰复燃**：博主在这个区间居然说了一句“正如我们所知，硬币的另一面是...”。这太像大模型的教科书体了，观众的疲惫感瞬间上涌。
    *   **优化改进 [带时间戳]**：
        *   `[01:45]` 把关于美债收益率的复杂推导**极简化**。直接换成口语：“大家不需要去记那些复杂的公式，说句人话，就是水放出来了，但是管子堵了。”
        *   `[02:10]` **语速恢复到每分钟 260 字**。在这个枯燥的概念转换区间，必须插入一个真实的“一线体感故事”（例如提到 Costco 的热狗或者卡车司机的排队时长），用具体实物把观众注意力强行拉回来。

### ✅ 亮点区域诊断 (03:15 - 04:30)
*   **流失现象**：流失率曲线在此区间完全抹平，甚至出现了微弱的反弹回升。
*   **音频听音诊断**：
    *   **声学特征**：博主声音的情绪张力明显变强，多用了重音和坚定的语气，甚至有轻轻敲击桌子配合节奏的声音。
    *   **核心原因**：博主在这个区间讲述了他和德州电池工厂主管聊招工起薪暴跌的真实案例。第一视角极强，语言密度极高，给足了观众“认知情绪价值”。
    *   **优化建议**：保持这种“物理世界哨兵”的爆款表达风格。后续视频可以把这类“真实一线体感故事”**前置到视频的前 30 秒**中，而不是放在 3 分钟以后。

---

## 3. 下期迭代优化动作清单 (Action Items for Next Week)
1.  **物理切片优化**：开场直接切入冲突，消灭前 5 秒任何换气声、底噪和无意义的寒暄。
2.  **人设配音校准**：录音时，在电脑屏幕上贴一张 Costco 和卡车排队的照片，强迫自己进入“前线物理哨兵”的状态，用带点沙哑、坚定的口语录制，消灭任何像大模型念教科书的声音。
3.  **防雷词表复盘**：下期录制完，自动把音频丢进本系统进行转文字比对，如果在文本里检索到“毫无疑问”、“正如我们所知”等 AI 味词汇，直接重录该片段！
"""


def main():
    parser = argparse.ArgumentParser(description="多模态周期复盘诊断引擎")
    parser.add_argument("--audio", type=str, default="", help="本地 .mp3 音频文件路径")
    parser.add_argument("--video_url", type=str, default="", help="可选：线上视频链接 (使用 yt-dlp 一键抓取音频)")
    parser.add_argument("--metrics", type=str, default="", help="传入视频的表现指标 (JSON 字符串，包含播放量 views, 前5s保留率 retention_5s, 完播率 completion_rate 等)")
    parser.add_argument("--metrics_file", type=str, default="", help="可选：存放表现指标的本地 CSV/JSON 文件路径")

    args = parser.parse_args()
    reports_dir = setup_directories()

    # 1. 抓取与转换音频
    audio_path = args.audio
    if args.video_url:
        print("[+] 检测到视频链接，开始调用 yt-dlp 抓取...")
        downloaded_mp3 = convert_video_link_to_mp3(args.video_url, reports_dir)
        if downloaded_mp3:
            audio_path = downloaded_mp3

    # 2. 解析指标数据
    metrics_data = {
        "views": 12000,
        "retention_5s": 0.45,
        "completion_rate": 0.18
    }

    if args.metrics:
        try:
            parsed = json.loads(args.metrics)
            metrics_data.update(parsed)
            print("[+] 成功解析命令行传入的指标数据。")
        except Exception as e:
            print(f"[-] 解析 --metrics 参数失败 ({e})，使用默认参考指标。")
            
    elif args.metrics_file:
        if os.path.exists(args.metrics_file):
            try:
                with open(args.metrics_file, "r", encoding="utf-8") as f_m:
                    parsed = json.load(f_m)
                    metrics_data.update(parsed)
                print(f"[+] 成功从文件 {args.metrics_file} 中读取指标数据。")
            except Exception as e:
                print(f"[-] 读取指标文件失败 ({e})，正在尝试 CSV 格式简易解析...")
                # 简单兜底 CSV 解析
                try:
                    with open(args.metrics_file, "r", encoding="utf-8") as f_m:
                        lines = f_m.readlines()
                        if len(lines) > 1:
                            headers = lines[0].strip().split(',')
                            values = lines[1].strip().split(',')
                            temp_dict = dict(zip(headers, values))
                            for k, v in temp_dict.items():
                                try:
                                    metrics_data[k] = float(v) if '.' in v else int(v)
                                except:
                                    metrics_data[k] = v
                            print("[+] 成功从 CSV 文件中解析指标数据。")
                except Exception as csv_err:
                    print(f"[-] 降级 CSV 解析亦失败 ({csv_err})。使用默认参考指标。")

    # 3. 组装 System Instruction 与 User Prompt
    system_instruction = """
你是一个身经百战的财经自媒体制作人、也是一个挑剔的音频导演。
现在你需要对博主上周发布的视频音频进行“听音复盘”。你将获得该视频的录音文件，以及该视频在平台上的播放数据（包含播放量、完播率以及前 5 秒流失率）。

你的任务是：
1. 对照表现数据，仔细聆听博主说话的语气语调、语速快慢、底噪、吞吐吸气以及用词是否生硬。
2. 结合博主独特的“前哨供应链 + 巴菲特价值投资 + 去AI味口语”人设标准，诊断视频的优缺点。
3. 必须输出带有精准时间戳（例如 `[00:15]`、`[02:30]`）的具体表达细节诊断，并给出实操性极强的修改意见。
4. 诊断报告要分为：前 5 秒黄金流失区诊断、内容节奏拖沓区诊断、以及高光表现区诊断。
"""

    user_prompt = f"""
请帮我诊断上周视频音频。以下是视频的后台表现数据：
----------------------------------------
{json.dumps(metrics_data, indent=4, ensure_ascii=False)}
----------------------------------------

请“听”一下我上传的音频文件，并对照上述数据，生成一份多模态复盘与表达诊断报告。
重点帮我定位：
- 为什么前 5 秒人流失了这么多？我的开场有什么声学上或者台词上的硬伤？
- 全片完播率中规中矩，哪些地方我说话像大模型在念教科书？哪些时间点我的语速和情绪太拖沓了？
- 哪些片段的表现最好，我应该如何把它发扬光大？
"""

    print("[+] 正在启动多模态周期复盘引擎，分析可能需要约 1-2 分钟...")
    
    # 4. 调用 API 进行多模态复盘
    audit_report = call_gemini_audio_audit(audio_path, metrics_data, system_instruction, user_prompt)

    # 5. 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f"report_{timestamp}.md"
    report_path = os.path.join(reports_dir, report_filename)

    with open(report_path, "w", encoding="utf-8") as f_rep:
        f_rep.write(audit_report)

    print("\n" + "="*40 + " [多模态音频与数据复盘诊断报告] " + "="*40)
    print(audit_report)
    print("="*109)
    print(f"[+] 复盘诊断报告已自动保存至: 5_audit_reports/{report_filename}")


if __name__ == "__main__":
    main()
