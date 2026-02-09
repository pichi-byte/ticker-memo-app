import ollama
from data_fetcher import get_company_data

SECTIONS = [
    "Company Overview",
    "Business Model",
    "Industry & Market",
    "Financial Analysis",
    "Catalysts",
    "Risks",
    "Investment Thesis"
]

def load_prompt():
    with open("prompts/memo_prompt.txt", "r") as f:
        return f.read()

def generate_section(ticker, section):

    data = get_company_data(ticker)
    base_prompt = load_prompt()

    full_prompt = f"""
    {base_prompt}

    Section to write:
    {section}

    Company Data:
    {data}
    """

    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": full_prompt}]
    )

    return response["message"]["content"]

def generate_full_memo(ticker):

    memo = ""

    for section in SECTIONS:
        print(f"Generating {section}...")
        content = generate_section(ticker, section)
        memo += f"\n\n## {section}\n{content}\n"

    return memo


if __name__ == "__main__":
    ticker = input("Enter ticker: ")
    print(generate_full_memo(ticker))
