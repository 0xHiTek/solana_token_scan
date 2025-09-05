#!/usr/bin/env python3
"""
Standalone test script for Solana Token Analyzer
Tests the X.com analysis functions without Streamlit
"""

import requests
import json
import re
from datetime import datetime
import time
from typing import Dict, List, Optional
import os

# Mock Streamlit functions for testing
class MockST:
    @staticmethod
    def info(msg): print(f"INFO: {msg}")
    @staticmethod 
    def success(msg): print(f"SUCCESS: {msg}")
    @staticmethod
    def warning(msg): print(f"WARNING: {msg}")
    @staticmethod
    def error(msg): print(f"ERROR: {msg}")
    
    class secrets:
        @staticmethod
        def get(key, default=None):
            # Check for API key in environment first
            if key == "EXA_API_KEY":
                return os.environ.get("EXA_API_KEY", default)
            return default

# Mock the streamlit module
import sys
class MockStreamlit:
    def __getattr__(self, name):
        if name == 'secrets':
            return MockST.secrets
        return getattr(MockST, name, lambda *args, **kwargs: None)

sys.modules['streamlit'] = MockStreamlit()

try:
    from exa_py import Exa
    HAS_EXA = True
except ImportError:
    print("WARNING: exa-py not installed. Install with: pip install exa-py")
    HAS_EXA = False

class TestSolanaTokenAnalyzer:
    def __init__(self):
        self.exa_client = None
        if HAS_EXA:
            self.setup_exa_client()
    
    def setup_exa_client(self):
        """Initialize Exa client for social media searches"""
        try:
            # Try to get API key from environment
            exa_api_key = os.environ.get("EXA_API_KEY")
            if not exa_api_key:
                # Try to read from secrets file
                try:
                    with open('.streamlit/secrets.toml', 'r') as f:
                        content = f.read()
                        import re
                        match = re.search(r'EXA_API_KEY\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            exa_api_key = match.group(1)
                except:
                    pass
            
            if exa_api_key:
                self.exa_client = Exa(api_key=exa_api_key)
                print("✅ Exa client initialized successfully")
            else:
                print("⚠️ Exa API key not found. Social media analysis will be limited.")
        except Exception as e:
            print(f"❌ Error setting up Exa client: {e}")
    
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
                    print("⚠️ API rate limit reached, trying alternative...")
                    continue
            except requests.exceptions.Timeout:
                print("⚠️ API timeout, trying alternative...")
                continue
            except Exception as e:
                print(f"⚠️ API error: {str(e)[:100]}...")
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
            print("⚠️ Price API timeout")
        except Exception as e:
            print(f"⚠️ Price fetch error: {str(e)[:50]}...")
        
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
        """Search X.com for mentions of the token using comprehensive search approach"""
        if not self.exa_client:
            return {"success": False, "error": "Exa client not initialized"}
        
        try:
            # Create comprehensive search queries to catch all mentions
            queries = []
            
            # 1. Full contract address search
            queries.append(contract_address)
            
            # 2. Shortened contract address variations (common on social media)
            queries.append(contract_address[:12])  # First 12 characters
            queries.append(contract_address[:8])   # First 8 characters
            
            # 3. Contract with Solana context
            queries.append(f"{contract_address} solana")
            queries.append(f"{contract_address} pump")
            
            # 4. If we have token info, search for those too
            if token_symbol and token_symbol not in ["Unknown", "UNKNOWN"]:
                queries.append(f"{token_symbol} {contract_address[:8]}")
                queries.append(f"${token_symbol} solana")
                queries.append(f"${token_symbol} pump.fun")
            
            if token_name and token_name not in ["Unknown", "Unknown Token"] and len(token_name.split()) <= 3:
                queries.append(f'"{token_name}" {contract_address[:8]}')
                queries.append(f'"{token_name}" solana')
            
            all_results = []
            
            print(f"🔍 Starting search with {len(queries)} queries...")
            
            for query in queries:
                try:
                    print(f"🔍 Searching: {query[:50]}...")
                    
                    # Use broader search parameters
                    results = self.exa_client.search(
                        query=query,
                        num_results=10,  # More results per query
                        include_domains=["x.com", "twitter.com"],
                        start_published_date="2023-01-01"  # Broader date range
                    )
                    
                    if results.results:
                        print(f"✅ Found {len(results.results)} results for: {query[:30]}...")
                        all_results.extend(results.results)
                    else:
                        print(f"⚠️ No results for: {query[:30]}...")
                        
                    time.sleep(0.5)  # Rate limiting
                
                except Exception as e:
                    print(f"❌ Search failed for '{query[:30]}...': {str(e)[:100]}")
                    continue
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_results = []
            for result in all_results:
                url = getattr(result, 'url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
            
            # Enhanced relevance scoring
            def calculate_relevance(result):
                title = getattr(result, 'title', '') or ""
                text = getattr(result, 'text', '') or ""
                content = (title + " " + text).lower()
                
                score = 0
                
                # Exact contract match gets highest score
                if contract_address.lower() in content:
                    score += 100
                
                # Partial contract matches
                for length in [12, 8, 6]:
                    if contract_address[:length].lower() in content:
                        score += 50 - (12 - length) * 5
                
                # Token symbol matches
                if token_symbol and token_symbol.lower() in content:
                    score += 20
                
                # Token name matches
                if token_name and token_name.lower() in content:
                    score += 15
                
                # Crypto context keywords
                crypto_keywords = ['pump', 'moon', 'solana', 'dex', 'trade', 'buy', 'sell', 'token', 'coin', 'crypto', 'gem']
                for keyword in crypto_keywords:
                    if keyword in content:
                        score += 2
                
                return score
            
            # Sort by relevance score
            unique_results.sort(key=calculate_relevance, reverse=True)
            
            # Take top results with some score threshold
            relevant_results = [r for r in unique_results if calculate_relevance(r) > 0]
            
            print(f"🎯 Found {len(unique_results)} total results, {len(relevant_results)} relevant")
            
            return {
                "success": True,
                "total_mentions": len(relevant_results),
                "results": relevant_results[:10]  # Show more results
            }
            
        except Exception as e:
            print(f"❌ Search system error: {str(e)}")
            return {"success": False, "error": str(e)}

def test_analysis():
    print("=" * 60)
    print("🚀 TESTING SOLANA TOKEN ANALYZER")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = TestSolanaTokenAnalyzer()
    
    # Test with the provided contract address
    test_contract = "GBUxQFRXQjSPjkxymAUKPfbUbSpRY8Ui7az1HCxtpump"
    
    print(f"\n📍 Testing contract: {test_contract}")
    
    # Test validation
    print("\n1. 🔍 Testing contract validation...")
    is_valid = analyzer.validate_solana_contract(test_contract)
    print(f"   Contract valid: {is_valid}")
    
    if not is_valid:
        print("❌ Invalid contract address format")
        return
    
    # Test token info fetch
    print("\n2. 📊 Testing token info fetch...")
    token_info = analyzer.get_token_info_from_solscan(test_contract)
    print(f"   Token info result:")
    for key, value in token_info.items():
        print(f"     {key}: {value}")
    
    # Test price data fetch  
    print("\n3. 💰 Testing price data fetch...")
    price_data = analyzer.get_token_price_data(test_contract)
    print(f"   Price data result:")
    for key, value in price_data.items():
        print(f"     {key}: {value}")
    
    # Test social media search (if Exa client is available)
    print("\n4. 🐦 Testing social media search...")
    if analyzer.exa_client:
        social_results = analyzer.search_x_mentions(
            test_contract,
            token_info.get("name", ""),
            token_info.get("symbol", "")
        )
        print(f"   Social results:")
        print(f"     Success: {social_results.get('success', False)}")
        print(f"     Total mentions: {social_results.get('total_mentions', 0)}")
        
        if social_results.get('success') and social_results.get('results'):
            print(f"     Sample results:")
            for i, result in enumerate(social_results['results'][:3]):  # Show first 3
                title = getattr(result, 'title', 'No title')
                url = getattr(result, 'url', 'No URL')
                text = getattr(result, 'text', 'No text')[:100]
                print(f"       {i+1}. {title}")
                print(f"          URL: {url}")
                print(f"          Text: {text}...")
                print()
        
    else:
        print("   ⚠️ Exa client not available - skipping social media tests")
        print("   To enable: pip install exa-py and set EXA_API_KEY environment variable")
    
    print("\n" + "=" * 60)
    print("✅ ANALYSIS TEST COMPLETED!")
    print("=" * 60)

if __name__ == "__main__":
    test_analysis()