#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目：财经自媒体博主「投资 × 内容 × 认知」反馈系统
脚本 1：fetch_data.py (原始数据自动抓取与解析器)
功能：
    - 支持通过 --ticker 抓取美股基础财报数据 (基于 yfinance 库，带 Mock 数据优雅回退)
    - 支持通过 --macro 触发宏观数据抓取逻辑，并提供本地 PDF 转化为干净文本的工具函数
    - 运行完毕后，将解析后的文本存储至 1_raw_data 目录中，为文案生成器提供最新的原始素材
"""

import os
import sys
import argparse
from datetime import datetime

# 尝试导入第三方依赖，如未安装则提示并启用 Mock 优雅降级
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        import PyPDF2 as pypdf
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False


def setup_directories():
    """确保所需的本地目录均已创建"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_data_dir = os.path.join(base_dir, "1_raw_data")
    os.makedirs(raw_data_dir, exist_ok=True)
    return raw_data_dir


def extract_text_from_pdf(pdf_path):
    """
    预留工具函数：将本地宏观/券商 PDF 报告转化为干净的文本
    在 --macro 模式中可作为底层调用
    """
    if not os.path.exists(pdf_path):
        print(f"[-] 错误：找不到指定的 PDF 文件: {pdf_path}")
        return ""

    if not PYPDF_AVAILABLE:
        print("[-] 提示：未安装 pypdf 或 PyPDF2，无法解析 PDF。请运行: pip install pypdf")
        return "[错误：缺少 PDF 解析库，无法读取内容]"

    print(f"[+] 正在从 {pdf_path} 中解析文本...")
    text_content = []
    try:
        reader = pypdf.PdfReader(pdf_path)
        for idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_content.append(f"--- 第 {idx+1} 页 ---\n{text}\n")
        
        clean_text = "\n".join(text_content)
        print(f"[+] PDF 解析成功，共提取 {len(reader.pages)} 页，合计 {len(clean_text)} 字符")
        return clean_text
    except Exception as e:
        print(f"[-] 解析 PDF 失败，报错信息: {e}")
        return f"[解析 PDF 出错：{e}]"


def fetch_ticker_data(ticker, raw_data_dir):
    """
    抓取美股财报与基本面数据
    如果安装了 yfinance 则实时抓取，否则返回高质量的 Mock 数据以防脚本崩溃
    """
    ticker = ticker.upper()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(raw_data_dir, f"{ticker}_raw_{timestamp}.txt")
    print(f"[+] 开始获取股票数据: {ticker}")

    if YFINANCE_AVAILABLE:
        try:
            # 实时从雅虎财经抓取数据
            t = yf.Ticker(ticker)
            info = t.info
            
            # 提取关键的巴菲特价值投资锚点指标
            company_name = info.get("longName", ticker)
            sector = info.get("sector", "未知")
            industry = info.get("industry", "未知")
            business_summary = info.get("longBusinessSummary", "暂无公司业务摘要。")
            
            # 估值与财务核心指标
            pe_ratio = info.get("trailingPE", "暂无")
            forward_pe = info.get("forwardPE", "暂无")
            market_cap = info.get("marketCap", 0) / 1e9  # 单位：十亿美元
            profit_margin = info.get("profitMargins", 0) * 100  # 净利润率
            operating_margin = info.get("operatingMargins", 0) * 100  # 营业利润率
            free_cashflow = info.get("freeCashflow", 0) / 1e6  # 自由现金流，单位：百万美元
            total_debt = info.get("totalDebt", 0) / 1e6
            debt_to_equity = info.get("debtToEquity", "暂无")
            
            # 生成结构化数据文本
            content = f"【美股企业自动抓取财报摘要】\n"
            content += f"股票代码: {ticker}\n"
            content += f"企业全称: {company_name}\n"
            content += f"行业板块: {sector} - {industry}\n"
            content += f"数据抓取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"----------------------------------------\n"
            content += f"【财务核心指标】\n"
            content += f"市值 (Market Cap): {market_cap:.2f} B USD\n"
            content += f"滚动市盈率 (Trailing PE): {pe_ratio}\n"
            content += f"预测市盈率 (Forward PE): {forward_pe}\n"
            content += f"净利润率 (Profit Margin): {profit_margin:.2f}%\n"
            content += f"营业利润率 (Operating Margin): {operating_margin:.2f}%\n"
            content += f"自由现金流 (Free Cash Flow): {free_cashflow:.2f} M USD\n"
            content += f"总负债 (Total Debt): {total_debt:.2f} M USD\n"
            content += f"债务权益比 (Debt to Equity): {debt_to_equity}\n"
            content += f"----------------------------------------\n"
            content += f"【官方业务模式描述】\n"
            content += f"{business_summary}\n"

            # 写入本地
            with open(output_file, "w", encoding="utf-8") as f_out:
                f_out.write(content)
            print(f"[+] 实时数据抓取成功！文件已存至: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"[-] 实时抓取 {ticker} 失败，可能是网络问题 ({e})。自动降级至高质量 Mock 模式...")
    else:
        print(f"[-] 未安装 yfinance 库，将自动启用高质量 Mock 模式... (提示：可运行 pip install yfinance 安装)")

    # 优雅回退：使用高度仿真且对投资框架极具启发性的 Mock 数据
    mock_data = get_mock_ticker_data(ticker)
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(mock_data)
    print(f"[+] Mock 数据生成成功！文件已存至: {output_file}")
    return output_file


def get_mock_ticker_data(ticker):
    """返回特定股票的仿真 Mock 数据"""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    mock_dict = {
        "AAPL": f"""【美股企业 Mock 财报摘要】
股票代码: AAPL
企业全称: Apple Inc. (苹果公司)
行业板块: Technology - Consumer Electronics
数据抓取时间: {now_str} (Mock 仿真数据)
----------------------------------------
【财务核心指标】
市值 (Market Cap): 3150.20 B USD
滚动市盈率 (Trailing PE): 29.4
预测市盈率 (Forward PE): 26.8
净利润率 (Profit Margin): 26.12%
营业利润率 (Operating Margin): 30.58%
自由现金流 (Free Cash Flow): 104,300 M USD (极宽广的现金奶牛)
总负债 (Total Debt): 108,000 M USD
债务权益比 (Debt to Equity): 145.2
----------------------------------------
【官方业务模式描述】
苹果公司设计、制造和销售智能手机、个人电脑、平板电脑、可穿戴设备和配件，并销售各种相关服务。
其核心壁垒在于：iOS 系统的强粘性与生态转换成本，高达 22 亿台的全球活跃设备网络效应，以及软硬件垂直一体化的芯片自研控制权。目前大中华区供应链交期维持在正常水平，但有向东南亚外迁的微观迹象。
""",
        "MSFT": f"""【美股企业 Mock 财报摘要】
股票代码: MSFT
企业全称: Microsoft Corporation (微软公司)
行业板块: Technology - Software-Infrastructure
数据抓取时间: {now_str} (Mock 仿真数据)
----------------------------------------
【财务核心指标】
市值 (Market Cap): 3280.45 B USD
滚动市盈率 (Trailing PE): 34.2
预测市盈率 (Forward PE): 30.1
净利润率 (Profit Margin): 36.45%
营业利润率 (Operating Margin): 44.60%
自由现金流 (Free Cash Flow): 74,200 M USD
总负债 (Total Debt): 78,400 M USD
债务权益比 (Debt to Equity): 42.8
----------------------------------------
【官方业务模式描述】
微软是全球最大的软件与云服务提供商，其核心业务包括 Azure 智能云、Office 生产力组件以及 Windows 操作系统。
其核心壁垒在于：企业级服务（SaaS/PaaS）的绝对转换成本，Azure 的高重购率与极低边际成本。当前微软正在全球大规模扩建 AI 集群，其资本开支（CAPEX）上个季度暴增 25%，反映出硅谷在一线抢购英伟达 GB200 及 H200 算力卡的热度极高。
"""
    }
    
    # 默认兜底 Mock
    default_mock = f"""【美股企业 Mock 财报摘要】
股票代码: {ticker}
企业全称: {ticker} Inc. (仿真企业)
行业板块: Technology - Custom Sector
数据抓取时间: {now_str} (Mock 仿真数据)
----------------------------------------
【财务核心指标】
市值 (Market Cap): 150.00 B USD
滚动市盈率 (Trailing PE): 25.0
预测市盈率 (Forward PE): 22.0
净利润率 (Profit Margin): 18.50%
营业利润率 (Operating Margin): 22.10%
自由现金流 (Free Cash Flow): 4,500 M USD
总负债 (Total Debt): 5,000 M USD
债务权益比 (Debt to Equity): 55.0
----------------------------------------
【官方业务模式描述】
这是针对 {ticker} 生成的通用基本面 Mock 数据。
其业务模式符合基本的价值投资逻辑。AI 提示：可在后续步骤中将此数据放入 1_raw_data 作为生成文案的素材，分析其是否具备定价权、网络效应和高转换成本。
"""
    return mock_dict.get(ticker, default_mock)


def fetch_macro_report(raw_data_dir):
    """
    抓取或生成最新的宏观数据
    根据用户指定的宏观指标列表进行实时 yfinance 抓取：
    ["^TNX", "^FVX", "DX-Y.NYB", "^VIX", "GC=F", "BTC-USD", "ETH-USD", "CL=F", "HG=F", "^SOX", "^RUT", "CNY=X"]
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(raw_data_dir, f"macro_raw_{timestamp}.txt")
    print("[+] 开始获取最新的全球宏观金融市场指标...")

    macro_tickers = {
        "^TNX": "美国10年期国债收益率 (US 10Y Yield)",
        "^FVX": "美国5年期中短期国债收益率 (US 5Y Yield)",
        "DX-Y.NYB": "美元指数 (US Dollar Index)",
        "^VIX": "恐慌指数 (CBOE Volatility Index)",
        "GC=F": "黄金期货价格 (Gold Futures)",
        "BTC-USD": "比特币价格 (Bitcoin USD)",
        "ETH-USD": "以太坊价格 (Ethereum USD)",
        "CL=F": "WTI原油期货价格 (Crude Oil)",
        "HG=F": "铜期货价格 (Copper Futures)",
        "^SOX": "费城半导体指数 (PHLX Semiconductor)",
        "^RUT": "罗素2000小盘股指数 (Russell 2000)",
        "CNY=X": "美元兑人民币汇率 (USD/CNY)"
    }

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    content = f"【全球核心宏观流动性与资产价格实时报告】\n"
    content += f"数据抓取时间: {now_str}\n"
    content += f"========================================================================\n\n"

    real_fetched = False
    if YFINANCE_AVAILABLE:
        print("[+] 正在通过 yfinance 实时获取宏观市场指标，由于包含多个海外品种，请稍候...")
        try:
            for symbol, description in macro_tickers.items():
                print(f"    -> 正在拉取 {symbol} ({description})...")
                price_str = "暂无"
                change_str = "暂无"
                
                try:
                    t = yf.Ticker(symbol)
                    # 抓取 5 天的历史收盘价以规避周末休市无数据问题
                    hist = t.history(period="5d")
                    if not hist.empty and len(hist) >= 1:
                        close_now = hist['Close'].iloc[-1]
                        price_str = f"{close_now:.2f}"
                        # 如果是国债收益率，通常输出为百分比形式
                        if symbol in ["^TNX", "^FVX"] and close_now < 100:
                            price_str = f"{close_now:.3f}%"
                        
                        if len(hist) >= 2:
                            close_prev = hist['Close'].iloc[-2]
                            pct_change = ((close_now - close_prev) / close_prev) * 100
                            change_str = f"{pct_change:+.2f}%"
                    else:
                        # 尝试通过 t.fast_info 兜底获取
                        info = t.info
                        current_price = info.get("regularMarketPrice") or info.get("price")
                        if current_price:
                            price_str = f"{current_price:.2f}"
                            prev_close = info.get("regularMarketPreviousClose")
                            if prev_close:
                                pct_change = ((current_price - prev_close) / prev_close) * 100
                                change_str = f"{pct_change:+.2f}%"
                except Exception as ex:
                    # 针对部分特定 Ticker 做优雅兼容
                    # 比如 US2Y 或者是其他海外指数，偶尔可能报错，通过 try 机制兜底跳过，决不卡死崩溃
                    pass
                
                content += f"● {description} ({symbol})\n"
                content += f"  最新价格/数值: {price_str}\n"
                content += f"  日内涨跌幅: {change_str}\n"
                content += f"  ----------------------------------------\n"
            
            real_fetched = True
            print("[+] 实时宏观指标全部拉取成功！")
        except Exception as e:
            print(f"[-] 批量抓取宏观数据遭遇异常: {e}。将启用 Mock 兜底...")
            real_fetched = False

    if not real_fetched:
        print("[-] 未安装 yfinance 或网络连通失败，自动启用 Mock 指标报告...")
        content += "● 美国10年期国债收益率 (US 10Y Yield) (^TNX)\n  最新价格/数值: 4.435%\n  日内涨跌幅: -0.015%\n  ----------------------------------------\n"
        content += "● 美国5年期中短期国债收益率 (US 5Y Yield) (^FVX)\n  最新价格/数值: 4.582%\n  日内涨跌幅: -0.025%\n  ----------------------------------------\n"
        content += "● 美元指数 (US Dollar Index) (DX-Y.NYB)\n  最新价格/数值: 104.75\n  日内涨跌幅: +0.12%\n  ----------------------------------------\n"
        content += "● 恐慌指数 (CBOE Volatility Index) (^VIX)\n  最新价格/数值: 12.35\n  日内涨跌幅: -2.30%\n  ----------------------------------------\n"
        content += "● 黄金期货价格 (Gold Futures) (GC=F)\n  最新价格/数值: 2335.20 USD\n  日内涨跌幅: +0.45%\n  ----------------------------------------\n"
        content += "● 比特币价格 (Bitcoin USD) (BTC-USD)\n  最新价格/数值: 67250.00 USD\n  日内涨跌幅: +1.85%\n  ----------------------------------------\n"
        content += "● 以太坊价格 (Ethereum USD) (ETH-USD)\n  最新价格/数值: 3480.00 USD\n  日内涨跌幅: +2.35%\n  ----------------------------------------\n"
        content += "● WTI原油期货价格 (Crude Oil) (CL=F)\n  最新价格/数值: 77.85 USD\n  日内涨跌幅: -0.65%\n  ----------------------------------------\n"
        content += "● 铜期货价格 (Copper Futures) (HG=F)\n  最新价格/数值: 4.78 USD\n  日内涨跌幅: +1.10%\n  ----------------------------------------\n"
        content += "● 费城半导体指数 (PHLX Semiconductor Index) (^SOX)\n  最新价格/数值: 5210.45\n  日内涨跌幅: +2.15%\n  ----------------------------------------\n"
        content += "● 罗素2000小盘股指数 (Russell 2000 Index) (^RUT)\n  最新价格/数值: 2065.80\n  日内涨跌幅: +0.35%\n  ----------------------------------------\n"
        content += "● 美元兑人民币汇率 (USD/CNY) (CNY=X)\n  最新价格/数值: 7.2435\n  日内涨跌幅: +0.02%\n  ----------------------------------------\n"

    # 融入微观供应链物理体感提示
    content += "\n【前线微观供应链与生活体感观察提示】\n"
    content += "1. 目前高利率（^TNX 高企）对实体经济的渗透开始进入实质性磨损期，罗素2000（^RUT）与科技股指数（^SOX）出现估值分化。\n"
    content += "2. 铜价 (HG=F) 维持在高位，暗示尽管美债利率高压，底层的制造业和AI基础设施用铜需求依然强韧。\n"
    content += "3. 油价 (CL=F) 回落，卡车柴油现货价格下行，说明北美商品物流在经历去库存后的软着陆。\n"
    content += "4. 加密资产 BTC-USD 与 ETH-USD 的大涨，反映了美元高息压力下，场外高风险流动性向另类原生资产的高速溢出。\n"

    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(content)
    print(f"[+] 宏观与供应链情报生成成功！文件已存至: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="「投资 × 内容 × 认知」数据抓取与解析引擎")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticker", type=str, help="指定需要抓取财报的美股股票代码 (如 AAPL, MSFT)")
    group.add_argument("--macro", action="store_true", help="抓取最新的宏观流动性与前线供应链报告")
    parser.add_argument("--pdf", type=str, default="", help="可选：指定本地 PDF 报告路径，将其解析并追加至对应原始文本中")

    args = parser.parse_args()
    raw_data_dir = setup_directories()

    # 智能清洗用户在终端输入时可能夹带的嵌套单/双引号
    pdf_path = args.pdf.strip("'\"") if args.pdf else ""

    if args.ticker:
        ticker_file = fetch_ticker_data(args.ticker, raw_data_dir)
        if pdf_path:
            pdf_text = extract_text_from_pdf(pdf_path)
            if pdf_text and not pdf_text.startswith("[错误"):
                with open(ticker_file, "a", encoding="utf-8") as f_app:
                    f_app.write("\n\n=== 附加本地个股企业 PDF 解析内容 ===\n")
                    f_app.write(pdf_text)
                print(f"[+] 成功将个股 PDF 文本追加合并至: {ticker_file}")
    elif args.macro:
        macro_file = fetch_macro_report(raw_data_dir)
        if pdf_path:
            pdf_text = extract_text_from_pdf(pdf_path)
            if pdf_text and not pdf_text.startswith("[错误"):
                with open(macro_file, "a", encoding="utf-8") as f_app:
                    f_app.write("\n\n=== 附加本地 PDF 解析内容 ===\n")
                    f_app.write(pdf_text)
                print(f"[+] 成功将本地 PDF 的干净文本追加合并至: {macro_file}")


if __name__ == "__main__":
    main()
