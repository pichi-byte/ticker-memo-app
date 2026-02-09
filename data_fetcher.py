import yfinance as yf

def get_company_data(ticker):

    stock = yf.Ticker(ticker)

    info = stock.info
    financials = stock.financials

    data = {
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "description": info.get("longBusinessSummary"),
        "revenue": financials.loc["Total Revenue"].to_dict()
        if "Total Revenue" in financials.index else {}
    }

    return data


if __name__ == "__main__":
    ticker = input("Enter ticker: ")
    print(get_company_data(ticker))
