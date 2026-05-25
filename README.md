# Dirty Braids Brain (脏辫大脑) 🧠 

> **硬核财经自媒体 AI 代理系统 (Agentic Self-Media System)**  
> 专注于美股、宏观流动性、全球前线供应链、以及美国生活一线体感的“去 AI 味”内容自动化生产与诊断引擎。

---

## 🌟 项目定位 (Core Moat)

**脏辫大脑** 并不是一个平庸的内容生成工具，而是一个拥有**巴菲特主义底层心法**、**宏观流动性硬核视角**以及**美国物理世界哨兵体感**的财经 IP 代理。它的核心价值在于**彻底消灭“AI 标志性废话”**（如“毫无疑问”、“双刃剑”、“简而言之”等），生成高度口语化、严谨且信息密度极高的人类级爆款财经文案。

### 🛡 核心三大支柱：
1. **巴菲特价值投资思想（底层心法）**：深度剖析商业模式（收租型 Tollbooth）、护城河（网络效应、转换成本）以及管理层的利益一致性。
2. **宏观流动性总水闸（流动性水位）**：紧密跟踪 FOMC 决议、CPI/PCE 粘性通胀、非农数据与密歇根消费信心指数，锁定安全边际。
3. **物理世界哨兵（美国一线体感）**：将华尔街的冷酷数字，与加州湾区 Costco 的促销、洛杉矶码头的卡车排队时长、以及硅谷真实的裁员体感有机对撞。

---

## 📁 目录结构 (Directory Architecture)

```bash
dirty_braids_brain/
├── 0_dialogue_logs/        # 运行对话交互日志，记录生成演进
├── 1_raw_data/             # 存放原始抓取数据（WMT、HIMS、Macro 等）
├── 2_core_essence/         # 从原始数据提炼出的核心商业与宏观认知精华
├── 3_history_scripts/      # 历史生成/精修过的自媒体视频文案与脚本
├── 4_cognitive_cards/      # 沉淀的细分领域认知卡片
├── 5_audit_reports/        # 多模态复盘诊断与“去AI味”审核报告
├── config/                 # 核心大脑法则配置
│   ├── persona.md          # 财经IP人设、语言风格与“去AI味”避坑指南
│   ├── Master_Rulebook.md  # 长期黄金流量法则与绝对红线避坑库
│   └── frameworks.md       # 巴菲特经济特许权、宏观流动性等独家解构框架
├── .env                    # 系统环境变量配置 (本地 API Key，已加入 gitignore)
├── fetch_data.py           # 模块一：原始财务与宏观数据获取引擎
├── generate_script.py      # 模块二：基于法则库的多级文案与脚本生成器
└── audit_performance.py    # 模块三：基于复盘诊断报告的文本审计与自我纠偏引擎
```

---

## ⚙️ 核心流程与运行说明 (Execution Workflow)

整个系统通过三级流水线运行：

### 1. 数据捕获与解构 (`fetch_data.py`)
自动获取或读取宏观、微观及企业财报的 raw 文本（如 Walmart、Hims 等数据），并根据 `config/frameworks.md` 的商业框架，提取出具有物理体感的关键数据指标，输出到 `1_raw_data/` 及 `2_core_essence/`。

### 2. 人设级文案生成 (`generate_script.py`)
加载 `config/persona.md` 与 `config/Master_Rulebook.md`，使用大语言模型（如 Gemini 3.5）进行多轮深度推理，规避八股文，采用“黄金5秒起手式”生成短句、高密度、第一人称体感的视频口语脚本，输出到 `3_history_scripts/`。

### 3. 多模态诊断与审计 (`audit_performance.py`)
对生成的初稿脚本进行无情审计，彻底扫描并清除任何漏网的 “AI 标志性词汇”，计算信息密度，对视频节奏进行微调，并将复盘经验写回 `5_audit_reports/` 与长期法典，实现系统的**自我进化**。

---

## 🚀 快速上手 (Quick Start)

### 1. 克隆与初始化
```bash
git clone <Your-Repository-URL>
cd dirty-braids-brain
```

### 2. 配置本地环境变量
在 `dirty_braids_brain/` 文件夹下创建 `.env` 文件（**注意：该文件包含 API Key，已被 `.gitignore` 自动忽略，绝不会上传至 GitHub 公开仓库**）：
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. 安装依赖与运行
```bash
pip install -r requirements.txt  # 如有
python dirty_braids_brain/fetch_data.py
python dirty_braids_brain/generate_script.py
python dirty_braids_brain/audit_performance.py
```

---

## 📝 长期演进规划 (Evolution Roadmap)
* [x] **第一版雏形 (V1.0)**：完成数据提取、人设风格脚本生成以及“去 AI 味”的本地审计进化闭环。
* [ ] **多模态匹配 (V1.5)**：自动生成与脚本节奏相匹配的物理世界 B-roll 画面分镜与剪辑建议。
* [ ] **自动化流水线 (V2.0)**：接入实时 API 爬虫，自动盯盘宏观异动，实现爆款选题全天候自动化捕获。
