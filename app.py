import streamlit as st
import requests
import json
import re
from datetime import datetime
import pandas as pd
from typing import Dict, List, Optional, Tuple
import time

# Import the MCP Exa functions (you'll need to install the exa-py package)
# pip install exa-py
try:
    from exa_py import Exa
except ImportError:
    st.error("Please install exa-py: pip install exa-py")
    st.stop()

class SolanaTokenAnalyzer:
    def __init__(self):
        self.exa_client = None
        self.setup_exa_client()
    
    def setup_exa_client(self):
        """Initialize Exa client for social media searches"""
        # You'll need to set your Exa API key as environment variable or Streamlit secret
        try:
            exa_api_key = st.secrets.get("EXA_API_KEY", None)
            if exa_api_key:
                self.exa_client = Exa(api_key=exa_api_key)
            else:
                st.warning("Exa API key not found. Social media analysis will be limited.")
        except Exception as e:
            st.error(f"Error setting up Exa client: {e}")
    
    def validate_solana_contract(self, contract_address: str) -> bool:
        """Validate if the contract address is a valid Solana address"""
        if not contract_address:
            return False
        
        # Basic Solana address validation (base58, 32-44 characters)
        if len(contract_address) < 32 or len(contract_address) > 44:
            return False
        
        # Check if it contains only valid base58 characters
        valid_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        return all(c in valid_chars for c in contract_address)
    
    def get_token_info_from_solscan(self, contract_address: str) -> Dict:
        """Fetch token information from multiple sources"""
        # Try multiple endpoints
        endpoints = [
            f"https://api.solscan.io/token/meta?token={contract_address}",
            f"https://public-api.solscan.io/token/meta?tokenAddress={contract_address}"
        ]
        
        for url in endpoints:
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "name": data.get("name", data.get("symbol", "Unknown Token")),
                        "symbol": data.get("symbol", "UNKNOWN"),
                        "decimals": data.get("decimals", 9),
                        "supply": data.get("supply", data.get("totalSupply", "Unknown")),
                        "success": True
                    }
                elif response.status_code == 429:
                    st.warning("⚠️ API rate limit reached, trying alternative...")
                    continue
            except requests.exceptions.Timeout:
                st.warning("⚠️ API timeout, trying alternative...")
                continue
            except Exception as e:
                st.warning(f"⚠️ API error: {str(e)[:100]}...")
                continue
        
        # Fallback: Return basic info if all APIs fail
        return {
            "name": f"Token {contract_address[:8]}...",
            "symbol": "UNKNOWN",
            "decimals": 9,
            "supply": "Unknown",
            "success": False,
            "fallback": True
        }
    
    def get_token_price_data(self, contract_address: str) -> Dict:
        """Fetch token price and market data from multiple sources"""
        # Try DexScreener first
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("pairs") and len(data["pairs"]) > 0:
                    pair = data["pairs"][0]
                    return {
                        "price_usd": pair.get("priceUsd", "0"),
                        "market_cap": pair.get("fdv", "Unknown"),
                        "liquidity": pair.get("liquidity", {}).get("usd", "Unknown"),
                        "volume_24h": pair.get("volume", {}).get("h24", "Unknown"),
                        "price_change_24h": pair.get("priceChange", {}).get("h24", "Unknown"),
                        "dex": pair.get("dexId", "Unknown"),
                        "success": True
                    }
                else:
                    # Token exists but no trading pairs found
                    return {
                        "price_usd": "0",
                        "market_cap": "No trading data",
                        "liquidity": "No liquidity",
                        "volume_24h": "0",
                        "price_change_24h": "0",
                        "dex": "None",
                        "success": False,
                        "fallback": True
                    }
        except requests.exceptions.Timeout:
            st.warning("⚠️ Price API timeout")
        except Exception as e:
            st.warning(f"⚠️ Price fetch error: {str(e)[:50]}...")
        
        # Fallback response
        return {
            "price_usd": "Unknown",
            "market_cap": "Unknown",
            "liquidity": "Unknown", 
            "volume_24h": "Unknown",
            "price_change_24h": "Unknown",
            "dex": "Unknown",
            "success": False,
            "fallback": True
        }
    
    def search_x_mentions(self, contract_address: str, token_name: str = "", token_symbol: str = "") -> Dict:
        """Search X.com for mentions of the token using Exa MCP"""
        if not self.exa_client:
            return {"success": False, "error": "Exa client not initialized"}
        
        try:
            # Create search queries
            queries = []
            
            # Add contract address query
            queries.append(f'site:x.com "{contract_address}"')
            
            # Add token name and symbol queries if available
            if token_name and token_name != "Unknown":
                queries.append(f'site:x.com "{token_name}" Solana token')
            
            if token_symbol and token_symbol != "Unknown":
                queries.append(f'site:x.com "${token_symbol}" Solana memecoin')
            
            all_results = []
            
            for query in queries:
                try:
                    # Use Exa to search
                    results = self.exa_client.search(
                        query=query,
                        num_results=10,
                        include_domains=["x.com", "twitter.com"]
                    )
                    
                    if results.results:
                        all_results.extend(results.results)
                        time.sleep(0.5)  # Rate limiting
                
                except Exception as e:
                    st.warning(f"Search query failed: {query} - {e}")
                    continue
            
            return {
                "success": True,
                "total_mentions": len(all_results),
                "results": all_results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_social_engagement(self, search_results: List) -> Dict:
        """Analyze the social media engagement from search results"""
        if not search_results:
            return {
                "engagement_score": 0,
                "notable_accounts": [],
                "total_mentions": 0,
                "engagement_level": "None",
                "risk_assessment": "Very High"
            }
        
        # Notable accounts patterns - major crypto influencers and exchanges
        notable_patterns = [
            # Major influencers
            r"@elonmusk", r"@stoolpresidente", r"@VitalikButerin", 
            # Major exchanges
            r"@binance", r"@coinbase", r"@cz_binance", r"@krakenfx", r"@okx",
            # Crypto personalities
            r"@justinsuntron", r"@bgarlinghouse", r"@saylor", r"@novogratz",
            # Crypto analysts/traders
            r"@altcoingordon", r"@whalechart", r"@thecryptolark", r"@cryptocobain", 
            r"@pentosh1", r"@hsaka", r"@scottmelker", r"@cryptokaleo",
            # Solana ecosystem
            r"@solana", r"@aeyakovenko", r"@rajgokal", r"@stepnofficial",
            # Other notable crypto accounts
            r"@cointelegraph", r"@coindesk", r"@blockchain", r"@crypto"
        ]
        
        notable_accounts = []
        engagement_indicators = []
        
        for result in search_results:
            # Check for notable accounts with null safety
            title = getattr(result, 'title', '') or ""
            text = getattr(result, 'text', '') or ""
            content = (title + " " + text).lower()
            
            for pattern in notable_patterns:
                if pattern.lower() in content:
                    notable_accounts.append(pattern)
            
            # Look for engagement indicators with more comprehensive patterns
            positive_words = [
                "viral", "moon", "pump", "trending", "bullish", "gem", "diamond", 
                "hold", "hodl", "rocket", "lambo", "ath", "breakout", "rally", 
                "surge", "exploding", "fire", "huge", "massive"
            ]
            negative_words = [
                "scam", "rug", "dump", "bearish", "avoid", "dead", "rekt", 
                "crash", "tanking", "falling", "losing", "panic", "sell", 
                "warning", "caution", "sketchy", "sus"
            ]
            
            if any(word in content for word in positive_words):
                engagement_indicators.append("positive")
            elif any(word in content for word in negative_words):
                engagement_indicators.append("negative")
        
        # Calculate engagement score
        base_score = min(len(search_results) * 10, 100)
        notable_bonus = len(set(notable_accounts)) * 20
        engagement_score = min(base_score + notable_bonus, 100)
        
        # Determine engagement level
        if engagement_score >= 70:
            engagement_level = "High"
            risk_level = "Low"
        elif engagement_score >= 40:
            engagement_level = "Medium"
            risk_level = "Medium"
        elif engagement_score >= 10:
            engagement_level = "Low"
            risk_level = "High"
        else:
            engagement_level = "None"
            risk_level = "Very High"
        
        return {
            "engagement_score": engagement_score,
            "notable_accounts": list(set(notable_accounts)),
            "total_mentions": len(search_results),
            "engagement_level": engagement_level,
            "risk_assessment": risk_level,
            "positive_indicators": engagement_indicators.count("positive"),
            "negative_indicators": engagement_indicators.count("negative")
        }
    
    def generate_investment_recommendation(self, token_data: Dict, price_data: Dict, social_data: Dict) -> Dict:
        """Generate investment recommendation based on all analyzed data"""
        score = 0
        reasons = []
        
        # Social media score (40% weight)
        social_score = social_data.get("engagement_score", 0)
        score += social_score * 0.4
        
        if social_score >= 70:
            reasons.append("✅ Strong social media presence")
        elif social_score >= 40:
            reasons.append("⚠️ Moderate social media presence")
        else:
            reasons.append("❌ Weak or no social media presence")
        
        # Notable accounts (20% weight)
        notable_accounts = social_data.get("notable_accounts", [])
        if len(notable_accounts) >= 3:
            score += 20
            reasons.append(f"✅ {len(notable_accounts)} notable accounts promoting")
        elif len(notable_accounts) >= 1:
            score += 10
            reasons.append(f"⚠️ {len(notable_accounts)} notable account(s) promoting")
        else:
            reasons.append("❌ No notable accounts promoting")
        
        # Market metrics (40% weight)
        try:
            liquidity = float(price_data.get("liquidity", "0"))
            if liquidity >= 100000:  # $100k+
                score += 20
                reasons.append("✅ Strong liquidity")
            elif liquidity >= 50000:  # $50k+
                score += 10
                reasons.append("⚠️ Moderate liquidity")
            else:
                reasons.append("❌ Low liquidity")
        except:
            reasons.append("❌ Unknown liquidity")
        
        # Volume check
        try:
            volume = float(price_data.get("volume_24h", "0"))
            if volume >= 50000:  # $50k+ daily volume
                score += 20
                reasons.append("✅ Good trading volume")
            elif volume >= 10000:  # $10k+ daily volume
                score += 10
                reasons.append("⚠️ Moderate trading volume")
            else:
                reasons.append("❌ Low trading volume")
        except:
            reasons.append("❌ Unknown trading volume")
        
        # Generate recommendation
        if score >= 80:
            recommendation = "🟢 STRONG BUY"
            risk_level = "Low"
        elif score >= 60:
            recommendation = "🟡 MODERATE BUY"
            risk_level = "Medium"
        elif score >= 40:
            recommendation = "🟠 CAUTION"
            risk_level = "High"
        else:
            recommendation = "🔴 AVOID"
            risk_level = "Very High"
        
        return {
            "recommendation": recommendation,
            "score": round(score, 1),
            "risk_level": risk_level,
            "reasons": reasons
        }

def main():
    st.set_page_config(
        page_title="Solana Token Analyzer",
        page_icon="🚀",
        layout="wide"
    )
    
    # Custom CSS for dark hacker theme
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0d1117, #161b22, #21262d);
        color: #00ff41 !important;
    }
    
    /* Fix all text colors */
    .stApp * {
        color: #00ff41 !important;
    }
    
    /* Override specific text elements */
    p, span, div, label {
        color: #00ff41 !important;
    }
    
    .main .block-container {
        background: rgba(13, 17, 23, 0.8);
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 2rem;
        margin-top: 1rem;
    }
    
    .stSelectbox, .stTextInput {
        background-color: #161b22 !important;
        color: #00ff41 !important;
        border: 1px solid #30363d !important;
    }
    
    .stTextInput > div > div > input {
        background-color: #161b22 !important;
        color: #00ff41 !important;
        border: 1px solid #30363d !important;
    }
    
    .stTextInput > label {
        color: #00ff41 !important;
        font-weight: bold !important;
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #238636, #2ea043) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        box-shadow: 0 4px 15px rgba(46, 160, 67, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #2ea043, #3fb950) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(46, 160, 67, 0.4) !important;
    }
    
    .stMetric {
        background: rgba(33, 38, 45, 0.8) !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        box-shadow: 0 2px 10px rgba(0, 255, 65, 0.1) !important;
    }
    
    .stMetric > div {
        color: #00ff41 !important;
    }
    
    .stMetric [data-testid="metric-container"] > div:first-child {
        color: #58a6ff !important;
        font-size: 0.9rem !important;
        font-weight: bold !important;
    }
    
    .stMetric [data-testid="metric-container"] > div:nth-child(2) {
        color: #00ff41 !important;
        font-size: 1.5rem !important;
        font-weight: bold !important;
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.3) !important;
    }
    
    .stSidebar {
        background: linear-gradient(180deg, #0d1117, #161b22) !important;
        border-right: 2px solid #30363d !important;
    }
    
    .stSidebar > div {
        color: #00ff41 !important;
    }
    
    .stSidebar * {
        color: #00ff41 !important;
    }
    
    /* Fix spinner and other dynamic elements */
    .stSpinner > div {
        color: #00ff41 !important;
    }
    
    /* Fix expander text */
    .stExpander summary {
        color: #00ff41 !important;
        font-weight: bold !important;
    }
    
    /* Fix general text contrast */
    .markdown-text-container, .stMarkdown {
        color: #00ff41 !important;
    }
    
    /* Fix help text and placeholders */
    .help-text, ::placeholder {
        color: #7d8590 !important;
        opacity: 0.8 !important;
    }
    
    h1, h2, h3 {
        color: #00ff41 !important;
        text-shadow: 0 0 15px rgba(0, 255, 65, 0.4) !important;
        font-family: 'Courier New', monospace !important;
    }
    
    .stSuccess {
        background: rgba(46, 160, 67, 0.3) !important;
        border: 1px solid #2ea043 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    .stError {
        background: rgba(248, 113, 113, 0.3) !important;
        border: 1px solid #f87171 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    .stWarning {
        background: rgba(251, 191, 36, 0.3) !important;
        border: 1px solid #fbbf24 !important;
        color: #1f2937 !important;
        font-weight: bold !important;
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.3) !important;
        border: 1px solid #3b82f6 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    .terminal-text {
        font-family: 'Courier New', monospace;
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 5px;
        padding: 1rem;
        color: #00ff41;
        text-shadow: 0 0 5px rgba(0, 255, 65, 0.3);
    }
    
    .token-card {
        background: linear-gradient(135deg, #161b22, #21262d);
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0, 255, 65, 0.1);
    }
    
    .recommendation-strong-buy {
        background: linear-gradient(45deg, #2ea043, #3fb950) !important;
        color: #ffffff !important;
        padding: 1rem !important;
        border-radius: 10px !important;
        border: 1px solid #3fb950 !important;
        box-shadow: 0 0 20px rgba(46, 160, 67, 0.4) !important;
    }
    
    .recommendation-moderate-buy {
        background: linear-gradient(45deg, #fbbf24, #f59e0b) !important;
        color: #1f2937 !important;
        padding: 1rem !important;
        border-radius: 10px !important;
        border: 1px solid #f59e0b !important;
        box-shadow: 0 0 20px rgba(251, 191, 36, 0.4) !important;
    }
    
    .recommendation-caution {
        background: linear-gradient(45deg, #f97316, #ea580c) !important;
        color: #ffffff !important;
        padding: 1rem !important;
        border-radius: 10px !important;
        border: 1px solid #ea580c !important;
        box-shadow: 0 0 20px rgba(249, 115, 22, 0.4) !important;
    }
    
    .recommendation-avoid {
        background: linear-gradient(45deg, #dc2626, #b91c1c) !important;
        color: #ffffff !important;
        padding: 1rem !important;
        border-radius: 10px !important;
        border: 1px solid #b91c1c !important;
        box-shadow: 0 0 20px rgba(220, 38, 38, 0.4) !important;
    }
    
    .stExpander {
        background: rgba(33, 38, 45, 0.8) !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    
    .stExpander > div:first-child {
        color: #00ff41 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with enhanced styling
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3.5rem; color: #00ff41; text-shadow: 0 0 20px rgba(0, 255, 65, 0.6); 
                   font-family: 'Courier New', monospace; margin-bottom: 0;">
            🚀 SOLANA TOKEN ANALYZER
        </h1>
        <p style="font-size: 1.2rem; color: #7d8590; margin-top: 0; font-family: 'Courier New', monospace;">
            > REAL-TIME BLOCKCHAIN & SOCIAL SENTIMENT ANALYSIS_
        </p>
        <div style="height: 2px; background: linear-gradient(90deg, transparent, #00ff41, transparent); 
                    margin: 1rem auto; width: 60%;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize analyzer
    analyzer = SolanaTokenAnalyzer()
    
    # Enhanced sidebar
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h2 style="color: #00ff41; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(0, 255, 65, 0.4);">
            🔍 SCANNER INTERFACE
        </h2>
        <div style="height: 1px; background: #00ff41; margin: 1rem 0;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("""
    <div class="terminal-text" style="margin-bottom: 1rem;">
        <p>📡 BLOCKCHAIN SCANNER READY</p>
        <p>🔎 INPUT TARGET CONTRACT</p>
    </div>
    """, unsafe_allow_html=True)
    
    contract_address = st.sidebar.text_input(
        "🎯 TARGET CONTRACT ADDRESS:",
        placeholder="Enter Solana contract address...",
        help="Paste the Solana token contract address to analyze"
    )
    
    analyze_button = st.sidebar.button("🚀 INITIATE SCAN", type="primary")
    
    if analyze_button and contract_address:
        if not analyzer.validate_solana_contract(contract_address):
            st.error("❌ Invalid Solana contract address format")
            return
        
        # Create main columns
        col1, col2 = st.columns([1, 1])
        
        with st.spinner("🔍 Analyzing token..."):
            # Fetch token information
            with col1:
                st.markdown("""
                <div class="token-card">
                    <h3 style="color: #00ff41; font-family: 'Courier New', monospace; margin-bottom: 1rem;">
                        📊 TOKEN INTELLIGENCE
                    </h3>
                </div>
                """, unsafe_allow_html=True)
                token_info = analyzer.get_token_info_from_solscan(contract_address)
                
                if token_info.get("success"):
                    st.success("✅ TOKEN DATA ACQUIRED")
                elif token_info.get("fallback"):
                    st.info("ℹ️ USING FALLBACK DATA")
                else:
                    st.warning("⚠️ TOKEN SCAN FAILED")
                
                # Always display available information
                info_data = {
                    "Name": token_info.get("name", "Unknown"),
                    "Symbol": token_info.get("symbol", "Unknown"),
                    "Contract": contract_address,
                    "Decimals": token_info.get("decimals", "Unknown"),
                    "Supply": token_info.get("supply", "Unknown")
                }
                
                for key, value in info_data.items():
                    st.metric(key, value)
            
            # Fetch price data
            with col2:
                st.markdown("""
                <div class="token-card">
                    <h3 style="color: #00ff41; font-family: 'Courier New', monospace; margin-bottom: 1rem;">
                        💰 MARKET ANALYTICS
                    </h3>
                </div>
                """, unsafe_allow_html=True)
                price_data = analyzer.get_token_price_data(contract_address)
                
                if price_data.get("success"):
                    st.success("✅ MARKET DATA ACQUIRED")
                elif price_data.get("fallback"):
                    st.info("ℹ️ USING FALLBACK DATA") 
                else:
                    st.warning("⚠️ MARKET SCAN FAILED")
                
                # Always display available information
                price_usd = price_data.get('price_usd', 'Unknown')
                if price_usd not in ['Unknown', '0', 'No trading data']:
                    st.metric("Price (USD)", f"${price_usd}")
                else:
                    st.metric("Price (USD)", price_usd)
                
                market_cap = price_data.get('market_cap', 'Unknown')
                if market_cap not in ['Unknown', 'No trading data']:
                    st.metric("Market Cap", f"${market_cap}")
                else:
                    st.metric("Market Cap", market_cap)
                
                liquidity = price_data.get('liquidity', 'Unknown')
                if liquidity not in ['Unknown', 'No liquidity']:
                    st.metric("Liquidity", f"${liquidity}")
                else:
                    st.metric("Liquidity", liquidity)
                
                volume = price_data.get('volume_24h', 'Unknown')
                if volume not in ['Unknown', '0']:
                    st.metric("24h Volume", f"${volume}")
                else:
                    st.metric("24h Volume", volume)
                
                price_change = price_data.get("price_change_24h", "Unknown")
                if price_change not in ['Unknown', '0']:
                    try:
                        change_float = float(price_change)
                        delta_color = "normal" if change_float >= 0 else "inverse"
                        st.metric("24h Change", f"{price_change}%", delta=f"{price_change}%")
                    except:
                        st.metric("24h Change", price_change)
                else:
                    st.metric("24h Change", price_change)
        
        # Social media analysis
        st.markdown("""
        <div style="text-align: center; margin: 2rem 0;">
            <h2 style="color: #00ff41; font-family: 'Courier New', monospace; text-shadow: 0 0 15px rgba(0, 255, 65, 0.4);">
                📱 SOCIAL INTELLIGENCE SCAN
            </h2>
            <div style="height: 2px; background: linear-gradient(90deg, transparent, #00ff41, transparent); 
                        margin: 1rem auto; width: 40%;"></div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.spinner("🔍 SCANNING X.COM NETWORK..."):
            social_results = analyzer.search_x_mentions(
                contract_address,
                token_info.get("name", ""),
                token_info.get("symbol", "")
            )
            
            if social_results.get("success"):
                search_data = social_results.get("results", [])
                engagement_analysis = analyzer.analyze_social_engagement(search_data)
                
                # Display social metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Mentions", engagement_analysis["total_mentions"])
                
                with col2:
                    st.metric("Engagement Score", f"{engagement_analysis['engagement_score']}/100")
                
                with col3:
                    st.metric("Notable Accounts", len(engagement_analysis["notable_accounts"]))
                
                with col4:
                    st.metric("Risk Level", engagement_analysis["risk_assessment"])
                
                # Show notable accounts
                if engagement_analysis["notable_accounts"]:
                    st.subheader("🌟 Notable Accounts Promoting")
                    for account in engagement_analysis["notable_accounts"]:
                        st.badge(account)
                else:
                    st.warning("❌ No notable accounts found promoting this token")
                
                # Show recent mentions
                if search_data:
                    st.markdown("""
                    <div style="margin: 2rem 0;">
                        <h3 style="color: #00ff41; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(0, 255, 65, 0.4);">
                            🐦 RECENT X.COM MENTIONS
                        </h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for i, result in enumerate(search_data[:5]):  # Show top 5
                        # Safely get title and text
                        title = getattr(result, 'title', '') or f"Mention {i+1}"
                        text = getattr(result, 'text', '') or "No content available"
                        url = getattr(result, 'url', '') or "No URL available"
                        
                        # Truncate title for display
                        display_title = title[:100] + "..." if len(title) > 100 else title
                        
                        with st.expander(f"🔍 {display_title}"):
                            st.markdown(f"""
                            <div class="terminal-text">
                                <p><strong>URL:</strong> {url}</p>
                                <p><strong>Content:</strong> {text[:500]}{"..." if len(text) > 500 else ""}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if hasattr(result, 'published_date') and result.published_date:
                                st.write(f"**Date:** {result.published_date}")
                
            else:
                st.error(f"❌ Social media search failed: {social_results.get('error', 'Unknown error')}")
                engagement_analysis = {
                    "engagement_score": 0,
                    "notable_accounts": [],
                    "total_mentions": 0,
                    "risk_assessment": "Very High"
                }
        
        # Generate investment recommendation
        st.markdown("""
        <div style="text-align: center; margin: 2rem 0;">
            <h2 style="color: #00ff41; font-family: 'Courier New', monospace; text-shadow: 0 0 15px rgba(0, 255, 65, 0.4);">
                🎯 AI INVESTMENT ANALYSIS
            </h2>
            <div style="height: 2px; background: linear-gradient(90deg, transparent, #00ff41, transparent); 
                        margin: 1rem auto; width: 40%;"></div>
        </div>
        """, unsafe_allow_html=True)
        
        recommendation = analyzer.generate_investment_recommendation(
            token_info, price_data, engagement_analysis
        )
        
        # Display recommendation with enhanced styling
        rec_class = {
            "🟢 STRONG BUY": "recommendation-strong-buy",
            "🟡 MODERATE BUY": "recommendation-moderate-buy", 
            "🟠 CAUTION": "recommendation-caution",
            "🔴 AVOID": "recommendation-avoid"
        }
        
        css_class = rec_class.get(recommendation["recommendation"], "recommendation-avoid")
        
        st.markdown(f"""
        <div class="{css_class}" style="text-align: center; margin: 2rem 0;">
            <h2 style="margin: 0; font-family: 'Courier New', monospace;">
                {recommendation['recommendation']}
            </h2>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem;">
                CONFIDENCE SCORE: {recommendation['score']}/100
            </p>
            <p style="margin: 0.5rem 0 0 0; font-size: 1rem;">
                RISK LEVEL: {recommendation['risk_level'].upper()}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show reasoning with enhanced styling
        st.markdown("""
        <div style="margin: 2rem 0;">
            <h3 style="color: #00ff41; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(0, 255, 65, 0.4);">
                📋 ANALYSIS BREAKDOWN
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        for reason in recommendation["reasons"]:
            st.markdown(f"""
            <div class="terminal-text" style="margin: 0.5rem 0; padding: 0.5rem 1rem;">
                <p style="margin: 0; color: #00ff41;">• {reason}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Disclaimer
        st.warning("""
        ⚠️ **DISCLAIMER**: This analysis is for educational purposes only and should not be considered financial advice. 
        Cryptocurrency investments are highly risky and volatile. Always do your own research and never invest more than you can afford to lose.
        """)
    
    elif analyze_button:
        st.error("Please enter a valid Solana contract address")
    
    # Enhanced info section
    with st.sidebar:
        st.markdown("""
        <div style="margin: 2rem 0;">
            <div style="height: 1px; background: #30363d; margin: 1rem 0;"></div>
            <h3 style="color: #00ff41; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(0, 255, 65, 0.4);">
                ⚙️ SYSTEM OPERATIONS
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="terminal-text">
            <p><strong>1. TOKEN SCAN:</strong> Solscan API data retrieval</p>
            <p><strong>2. MARKET INTEL:</strong> DEX aggregator price feeds</p>
            <p><strong>3. SOCIAL RECON:</strong> X.com mention analysis</p>
            <p><strong>4. INFLUENCE MAP:</strong> Notable account detection</p>
            <p><strong>5. RISK CALC:</strong> Multi-factor assessment</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="margin: 2rem 0;">
            <h3 style="color: #00ff41; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(0, 255, 65, 0.4);">
                🔑 API STATUS
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Check if Exa API is configured
        try:
            exa_key = st.secrets.get("EXA_API_KEY", None)
            if exa_key and exa_key != "your_exa_api_key_here":
                st.markdown("""
                <div class="terminal-text" style="border-color: #2ea043;">
                    <p style="color: #2ea043;">✅ EXA API: ACTIVE</p>
                    <p style="color: #00ff41;">🔍 SOCIAL ANALYSIS: ENABLED</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="terminal-text" style="border-color: #f87171;">
                    <p style="color: #f87171;">❌ EXA API: INACTIVE</p>
                    <p style="color: #fcd34d;">⚠️ LIMITED FUNCTIONALITY</p>
                </div>
                """, unsafe_allow_html=True)
        except:
            st.markdown("""
            <div class="terminal-text" style="border-color: #f87171;">
                <p style="color: #f87171;">❌ EXA API: OFFLINE</p>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()