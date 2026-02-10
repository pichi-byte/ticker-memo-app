import streamlit as st
import subprocess
import yfinance as yf
import json
import os
import re
import random
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import LETTER

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Institutional Research Engine",
    layout="wide",
    page_icon="🏛️"
)

# --------------------------------------------------
# SIDEBAR — INSTITUTIONAL CONTROL PANEL
# --------------------------------------------------
st.sidebar.title("🏛️ Research Control Panel")

theme = st.sidebar.selectbox(
    "UI Mode",
    ["Institutional Light", "Institutional Dark"]
)

ticker = st.sidebar.text_input("Enter Ticker")

generate = st.sidebar.button("Generate Institutional Memo")

st.sidebar.markdown("---")
st.sidebar.caption("Institutional Research Engine v2")

# --------------------------------------------------
# THEMES
# --------------------------------------------------
if theme == "Institutional Dark":
    background = "#020617"
    text = "#e2e8f0"
    card = "#111827"
    header = "#111827"
else:
    background = "#f8fafc"
    text = "#0f172a"
    card = "#ffffff"
    header = "#e5e7eb"

st.markdown(f"""
<style>

.stApp {{
    background-color: {background};
    color: {text};
}}

.header-box {{
    background-color: {header};
    padding:18px;
    border-radius:10px;
    margin-bottom:20px;
}}

.metric-card {{
    background-color:{card};
    padding:15px;
    border-radius:12px;
    border:1px solid #e2e8f0;
}}

.memo-box {{
    background-color:{card};
    padding:25px;
    border-radius:12px;
    border:1px solid #e2e8f0;
    margin-top:20px;
}}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.markdown("""
<div class="header-box">
<h1>🏛️ Institutional Research Engine</h1>
<p>AI Equity Research • Factor Models • Monte Carlo • Institutional Memo Generation</p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# CLEAN OUTPUT
# --------------------------------------------------
def clean_output(text, ticker):

    if text is None:
        return ""

    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`.*?`", "", text)
    text = re.sub(r"<.*?>", "", text)

    cleaned = []
    for line in text.split("\n"):
        if "Ticker:" in line and ticker not in line:
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()

# --------------------------------------------------
# STOCK DATA
# --------------------------------------------------
def get_stock_data(ticker):

    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "price": info.get("currentPrice"),
        "eps": info.get("trailingEps"),
        "pe": info.get("trailingPE"),
        "growth": info.get("revenueGrowth"),
        "margin": info.get("profitMargins"),
        "roe": info.get("returnOnEquity")
    }

# --------------------------------------------------
# FACTOR MODEL
# --------------------------------------------------
def build_factor_scores(data):

    growth = min(max((data["growth"] or 0)*100,0),10)
    value = min(max(10-(data["pe"] or 20)/5,0),10)
    quality = min(max((data["roe"] or 0)*100,0),10)
    momentum = random.uniform(4,9)
    risk = 10-quality

    return {
        "growth": round(growth,1),
        "value": round(value,1),
        "quality": round(quality,1),
        "momentum": round(momentum,1),
        "risk": round(risk,1)
    }

# --------------------------------------------------
# MONTE CARLO
# --------------------------------------------------
def monte_carlo(price):

    sims = []
    for _ in range(300):
        p = price
        for _ in range(12):
            p *= random.uniform(0.92,1.08)
        sims.append(p)

    upside = sum(1 for x in sims if x>price)/len(sims)*100
    downside = sum(1 for x in sims if x<price*0.8)/len(sims)*100

    return {
        "prob_upside": round(upside,1),
        "prob_crash": round(downside,1)
    }

# --------------------------------------------------
# VALUATION
# --------------------------------------------------
def build_valuation(data):

    if not data["price"] or not data["eps"] or not data["pe"]:
        return None

    base = data["eps"]*data["pe"]
    bull = base*1.25
    bear = base*0.75
    upside = ((base-data["price"])/data["price"])*100

    conviction = min(max(upside/10,1),10)

    return {
        "target": round(base,2),
        "bull": round(bull,2),
        "bear": round(bear,2),
        "upside": round(upside,2),
        "conviction": round(conviction,1)
    }

# --------------------------------------------------
# PDF
# --------------------------------------------------
def create_pdf(text, filename):

    doc = SimpleDocTemplate(filename,pagesize=LETTER)
    styles = getSampleStyleSheet()
    story=[]

    for line in text.split("\n"):
        story.append(Paragraph(line,styles["Normal"]))
        story.append(Spacer(1,8))

    doc.build(story)

# --------------------------------------------------
# MEMO GENERATOR
# --------------------------------------------------
def generate_memo(ticker,data,val,factors,mc):

    prompt=f"""
You are an institutional hedge fund analyst.

STRICT RULES:
- Output ONLY memo text
- NO code
- Analyze ONLY ticker {ticker}

Company:{data['name']}
Price:{data['price']}
Valuation:{val}
Factors:{factors}
MonteCarlo:{mc}

FORMAT:

## Company Overview
## Institutional Factor Analysis
## Valuation
## Monte Carlo Risk
## Catalysts
## Risks
## Investment Thesis
"""

    result=subprocess.run(
        ["ollama","run","llama3:8b"],
        input=prompt,
        text=True,
        capture_output=True
    )

    output=result.stdout if result.stdout else ""
    return clean_output(output,ticker)

# --------------------------------------------------
# MAIN ENGINE
# --------------------------------------------------
if generate:

    ticker = ticker.upper()

    with st.spinner("Pulling Institutional Financial Data..."):
        data = get_stock_data(ticker)

    if data["name"] is None:
        st.error("Invalid ticker")
        st.stop()

    valuation = build_valuation(data)

    if valuation is None:
        st.error("Not enough valuation data")
        st.stop()

    factors = build_factor_scores(data)
    mc = monte_carlo(data["price"])

    # Bloomberg style ticker bar
    st.success(f"{ticker} | {data['name']} | {data['sector']} | ${data['price']}")

    st.subheader("📊 Institutional Snapshot")

    col1,col2,col3 = st.columns(3)

    with col1:
        st.markdown('<div class="metric-card">',unsafe_allow_html=True)
        st.metric("Target",valuation["target"])
        st.metric("Upside",f"{valuation['upside']}%")
        st.markdown('</div>',unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card">',unsafe_allow_html=True)
        st.metric("Bull",valuation["bull"])
        st.metric("Bear",valuation["bear"])
        st.markdown('</div>',unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card">',unsafe_allow_html=True)
        st.metric("Growth Score",factors["growth"])
        st.metric("Quality Score",factors["quality"])
        st.markdown('</div>',unsafe_allow_html=True)

    with st.spinner("Generating Institutional Memo..."):
        memo = generate_memo(ticker,data,valuation,factors,mc)

    st.markdown('<div class="memo-box">',unsafe_allow_html=True)
    st.markdown(memo)
    st.markdown('</div>',unsafe_allow_html=True)

    pdf_file=f"{ticker}_memo.pdf"
    create_pdf(memo,pdf_file)

    with open(pdf_file,"rb") as f:
        st.download_button(
            label="Download Institutional PDF Memo",
            data=f,
            file_name=pdf_file,
            mime="application/pdf"
        )
