# 🚀 Solana Token Analyzer

A comprehensive Solana token analysis tool that combines on-chain data with social media sentiment analysis using Exa AI to search X.com (Twitter) for token mentions and engagement metrics.

## Features

- **Token Information**: Fetches basic token data from Solscan API
- **Market Data**: Real-time price, volume, and liquidity from DEX aggregators
- **Social Media Analysis**: X.com mention tracking and engagement scoring using Exa AI
- **Notable Account Detection**: Identifies influential crypto accounts promoting tokens
- **Risk Assessment**: AI-powered investment recommendations based on multiple factors
- **User-Friendly Interface**: Clean Streamlit web app with real-time analysis

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Exa API key:
   - Copy `.streamlit/secrets.toml.template` to `.streamlit/secrets.toml`
   - Get your API key from [https://exa.ai](https://exa.ai)
   - Add your key to the secrets file:
   ```toml
   EXA_API_KEY = "your_actual_api_key_here"
   ```

3. Run the app:
```bash
streamlit run app.py
```

## Usage

1. Enter a Solana contract address (32-44 characters, base58 encoded)
2. Click "Analyze Token" to start the analysis
3. Review the comprehensive report including:
   - Token metadata and market data
   - Social media mentions and engagement scores
   - Notable accounts promoting the token
   - AI-powered investment recommendation

## Example Analysis

The app analyzes tokens across multiple dimensions:

- **Social Media (40% weight)**: X.com mentions, engagement, sentiment
- **Notable Accounts (20% weight)**: Influential crypto personalities promoting
- **Market Metrics (40% weight)**: Liquidity, trading volume, price action

## Disclaimer

⚠️ **This tool is for educational and research purposes only.** 

Not financial advice. Cryptocurrency investments are extremely risky and volatile. Always conduct your own research and never invest more than you can afford to lose.