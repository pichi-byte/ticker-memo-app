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

PORTFOLIO_FILE="portfolio.json"

# -------------------------
# FILE STORAGE
# -------------------------
def load_json(file):
    if os.path.exists(file):
        with open(file,"r",encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(file,data):
    with open(file,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=4)

# -------------------------
# CLEAN OUTPUT (ANTI CODE / ANTI HALLUCINATION)
# -------------------------
def clean_output(text,ticker):

    if text is None:
        return ""

    text=re.sub(r"```.*?```","",text,flags=re.DOTALL)
    text=re.sub(r"`.*?`","",text)
    text=re.sub(r"<.*?>","",text)

    cleaned=[]
    for line in text.split("\n"):
        if "Ticker:" in line and ticker not in line:
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()

# -------------------------
# STOCK DATA
# -------------------------
def get_stock_data(ticker):

    stock=yf.Ticker(ticker)
    info=stock.info

    return{
        "name":info.get("longName"),
        "sector":info.get("sector"),
        "industry":info.get("industry"),
        "price":info.get("currentPrice"),
        "eps":info.get("trailingEps"),
        "pe":info.get("trailingPE"),
        "growth":info.get("revenueGrowth"),
        "margin":info.get("profitMargins"),
        "roe":info.get("returnOnEquity")
    }

# -------------------------
# FACTOR MODEL
# -------------------------
def build_factor_scores(data):

    growth=min(max((data["growth"] or 0)*100,0),10)
    value=min(max(10-(data["pe"] or 20)/5,0),10)
    quality=min(max((data["roe"] or 0)*100,0),10)
    momentum=random.uniform(4,9)
    risk=10-quality

    return{
        "growth":round(growth,1),
        "value":round(value,1),
        "quality":round(quality,1),
        "momentum":round(momentum,1),
        "risk":round(risk,1)
    }

# -------------------------
# MONTE CARLO
# -------------------------
def monte_carlo(price):

    sims=[]
    for _ in range(300):
        p=price
        for _ in range(12):
            p*=random.uniform(0.92,1.08)
        sims.append(p)

    upside=sum(1 for x in sims if x>price)/len(sims)*100
    downside=sum(1 for x in sims if x<price*0.8)/len(sims)*100

    return{
        "prob_upside":round(upside,1),
        "prob_crash":round(downside,1)
    }

# -------------------------
# VALUATION
# -------------------------
def build_valuation(data):

    if not data["price"] or not data["eps"] or not data["pe"]:
        return None

    base=data["eps"]*data["pe"]
    bull=base*1.25
    bear=base*0.75
    upside=((base-data["price"])/data["price"])*100

    conviction=min(max(upside/10,1),10)

    return{
        "target":round(base,2),
        "bull":round(bull,2),
        "bear":round(bear,2),
        "upside":round(upside,2),
        "conviction":round(conviction,1)
    }

# -------------------------
# PDF GENERATION
# -------------------------
def create_pdf(text,filename):

    doc=SimpleDocTemplate(filename,pagesize=LETTER)
    styles=getSampleStyleSheet()
    story=[]

    for line in text.split("\n"):
        story.append(Paragraph(line,styles["Normal"]))
        story.append(Spacer(1,8))

    doc.build(story)

# -------------------------
# MEMO GENERATOR (FIXED)
# -------------------------
def generate_memo(ticker,data,val,factors,mc):

    prompt=f"""
You are an institutional hedge fund analyst.

STRICT RULES:
- Output ONLY memo text
- NO code
- NO markdown fences
- Analyze ONLY ticker {ticker}

Ticker:{ticker}
Company:{data['name']}
Sector:{data['sector']}
Industry:{data['industry']}
Price:{data['price']}

Valuation Target:{val['target']}
Upside:{val['upside']}%
Bull:{val['bull']}
Bear:{val['bear']}

Factor Scores:{factors}
Monte Carlo:{mc}

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

    if output.strip()=="":
        return "⚠️ Model returned empty output. Verify Ollama is running."

    return clean_output(output,ticker)

# -------------------------
# STREAMLIT UI
# -------------------------
st.set_page_config(page_title="Institutional Research Engine",layout="wide")

st.title("🏛️ Institutional Hedge Fund Research Engine — Phase 9")

# -------------------------
# SCORE EXPLANATION PANEL
# -------------------------
with st.expander("📘 How Institutional Scores Work (Methodology Summary)"):

    st.markdown("""
**These scores are internal research heuristics designed to quickly summarize company fundamentals.  
They are NOT standardized financial ratings.**

**Growth Score**
- Based on Revenue Growth
- Higher growth = higher score
- Scaled from 0–10

**Quality Score**
- Based on Return on Equity (ROE)
- Measures profitability and capital efficiency
- Higher ROE = higher quality score

**Value Score**
- Based on Price-to-Earnings (PE) ratio
- Lower PE implies stronger value attractiveness
- Adjusted into a 0–10 range

⚠️ Scores are simplified research indicators used for internal memo generation only.
""")

ticker=st.text_input("Enter Stock Ticker")
generate=st.button("Generate Institutional Memo")

if generate:

    if ticker.strip()=="":
        st.warning("Enter ticker")
        st.stop()

    ticker=ticker.upper()

    with st.spinner("Pulling Institutional Financial Data..."):
        data=get_stock_data(ticker)

    if data["name"] is None:
        st.error("Invalid ticker")
        st.stop()

    valuation=build_valuation(data)

    if valuation is None:
        st.error("Not enough valuation data.")
        st.stop()

    factors=build_factor_scores(data)
    mc=monte_carlo(data["price"])

    st.subheader("📊 Institutional Snapshot")

    col1,col2,col3=st.columns(3)

    col1.metric("Target",valuation["target"])
    col1.metric("Upside",f"{valuation['upside']}%")

    col2.metric("Bull",valuation["bull"])
    col2.metric("Bear",valuation["bear"])

    col3.metric("Growth Score",factors["growth"])
    col3.metric("Quality Score",factors["quality"])

    with st.spinner("Generating Institutional Memo..."):
        memo=generate_memo(ticker,data,valuation,factors,mc)

    st.markdown(memo)

    pdf_file=f"{ticker}_memo.pdf"
    create_pdf(memo,pdf_file)

    with open(pdf_file,"rb") as f:
        st.download_button(
            label="Download Institutional PDF Memo",
            data=f,
            file_name=pdf_file,
            mime="application/pdf"
        )
