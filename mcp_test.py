#!/usr/bin/env python3
"""
Test the Solana Token Analyzer using MCP servers for web search
This will help identify issues with the X.com analysis functions
"""

import requests
import json
import re
from datetime import datetime
import time
from typing import Dict, List, Optional

def validate_solana_contract(contract_address: str) -> bool:
    """Validate if the contract address is a valid Solana address"""
    if not contract_address:
        return False
    
    # Basic Solana address validation (base58, 32-44 characters)
    if len(contract_address) < 32 or len(contract_address) > 44:
        return False
    
    # Check if it contains only valid base58 characters
    valid_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return all(c in valid_chars for c in contract_address)

def get_token_info_from_solscan(contract_address: str) -> Dict:
    """Fetch token information from multiple sources"""
    print(f"Fetching token info for: {contract_address}")
    
    # Try multiple endpoints
    endpoints = [
        f"https://api.solscan.io/token/meta?token={contract_address}",
        f"https://public-api.solscan.io/token/meta?tokenAddress={contract_address}"
    ]
    
    for url in endpoints:
        try:
            print(f"  Trying: {url}")
            response = requests.get(url, timeout=15)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "name": data.get("name", data.get("symbol", "Unknown Token")),
                    "symbol": data.get("symbol", "UNKNOWN"),
                    "decimals": data.get("decimals", 9),
                    "supply": data.get("supply", data.get("totalSupply", "Unknown")),
                    "success": True
                }
                print(f"  SUCCESS: {result}")
                return result
            elif response.status_code == 429:
                print("  WARNING: API rate limit reached, trying alternative...")
                continue
        except requests.exceptions.Timeout:
            print("  WARNING: API timeout, trying alternative...")
            continue
        except Exception as e:
            print(f"  ERROR: API error: {str(e)[:100]}...")
            continue
    
    # Fallback: Return basic info if all APIs fail
    result = {
        "name": f"Token {contract_address[:8]}...",
        "symbol": "UNKNOWN",
        "decimals": 9,
        "supply": "Unknown",
        "success": False,
        "fallback": True
    }
    print(f"  FALLBACK: {result}")
    return result

def get_token_price_data(contract_address: str) -> Dict:
    """Fetch token price and market data from multiple sources"""
    print(f"Fetching price data for: {contract_address}")
    
    # Try DexScreener first
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address}"
        print(f"  Trying: {url}")
        response = requests.get(url, timeout=15)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("pairs") and len(data["pairs"]) > 0:
                pair = data["pairs"][0]
                result = {
                    "price_usd": pair.get("priceUsd", "0"),
                    "market_cap": pair.get("fdv", "Unknown"),
                    "liquidity": pair.get("liquidity", {}).get("usd", "Unknown"),
                    "volume_24h": pair.get("volume", {}).get("h24", "Unknown"),
                    "price_change_24h": pair.get("priceChange", {}).get("h24", "Unknown"),
                    "dex": pair.get("dexId", "Unknown"),
                    "success": True
                }
                print(f"  SUCCESS: {result}")
                return result
            else:
                # Token exists but no trading pairs found
                result = {
                    "price_usd": "0",
                    "market_cap": "No trading data",
                    "liquidity": "No liquidity",
                    "volume_24h": "0",
                    "price_change_24h": "0",
                    "dex": "None",
                    "success": False,
                    "fallback": True
                }
                print(f"  NO PAIRS: {result}")
                return result
    except requests.exceptions.Timeout:
        print("  ERROR: Price API timeout")
    except Exception as e:
        print(f"  ERROR: Price fetch error: {str(e)[:50]}...")
    
    # Fallback response
    result = {
        "price_usd": "Unknown",
        "market_cap": "Unknown",
        "liquidity": "Unknown", 
        "volume_24h": "Unknown",
        "price_change_24h": "Unknown",
        "dex": "Unknown",
        "success": False,
        "fallback": True
    }
    print(f"  FALLBACK: {result}")
    return result

def test_mcp_web_search(contract_address: str, token_name: str = "", token_symbol: str = ""):
    """Test web search using MCP servers to find X.com mentions"""
    print(f"\nTesting MCP web search for contract: {contract_address}")
    
    # Create comprehensive search queries
    queries = []
    
    # 1. Full contract address search
    queries.append(f"site:x.com {contract_address}")
    queries.append(f"site:twitter.com {contract_address}")
    
    # 2. Shortened contract address variations (common on social media)
    queries.append(f"site:x.com {contract_address[:12]}")
    queries.append(f"site:x.com {contract_address[:8]}")
    
    # 3. Contract with Solana context
    queries.append(f"site:x.com {contract_address} solana")
    queries.append(f"site:x.com {contract_address} pump")
    queries.append(f"site:x.com {contract_address} token")
    
    # 4. If we have token info, search for those too
    if token_symbol and token_symbol not in ["Unknown", "UNKNOWN"]:
        queries.append(f"site:x.com {token_symbol} {contract_address[:8]}")
        queries.append(f"site:x.com ${token_symbol} solana")
        queries.append(f"site:x.com ${token_symbol} pump.fun")
    
    if token_name and token_name not in ["Unknown", "Unknown Token"] and len(token_name.split()) <= 3:
        queries.append(f'site:x.com "{token_name}" {contract_address[:8]}')
        queries.append(f'site:x.com "{token_name}" solana')
    
    print(f"Will test {len(queries)} search queries:")
    for i, query in enumerate(queries, 1):
        print(f"  {i}. {query}")
    
    # Note: In a real implementation, we would use the MCP servers here
    # For now, we'll simulate the expected results
    
    return {
        "queries_tested": len(queries),
        "queries": queries,
        "note": "This would use MCP servers in the real implementation"
    }

def analyze_current_issues():
    """Analyze the current issues with the X.com analysis"""
    print("\nANALYZING CURRENT ISSUES:")
    print("=" * 50)
    
    issues = [
        "1. Limited search strategy - only basic contract searches",
        "2. Poor relevance filtering - includes non-relevant results", 
        "3. Weak engagement scoring - doesn't properly weight factors",
        "4. Missing crypto-specific search patterns",
        "5. No verification of actual token mentions in content",
        "6. Insufficient search query variations",
        "7. Poor handling of pump.fun tokens specifically",
        "8. Limited social media platform coverage",
        "9. Weak notable account detection patterns",
        "10. No sentiment analysis of found content"
    ]
    
    for issue in issues:
        print(f"  - {issue}")
    
    print("\nRECOMMENDED FIXES:")
    print("=" * 50)
    
    fixes = [
        "1. Implement multi-platform search (X.com, Reddit, Telegram)",
        "2. Add crypto-specific search patterns and keywords",
        "3. Improve relevance scoring with content analysis",
        "4. Add sentiment analysis of found content",
        "5. Better notable account detection patterns",
        "6. Implement proper content verification",
        "7. Add pump.fun specific search strategies",
        "8. Use MCP servers for more comprehensive searches",
        "9. Add engagement metrics from post interactions",
        "10. Implement time-based relevance weighting"
    ]
    
    for fix in fixes:
        print(f"  + {fix}")

def main():
    print("SOLANA TOKEN ANALYZER - MCP TEST")
    print("=" * 50)
    
    # Test with the provided contract address
    test_contract = "GBUxQFRXQjSPjkxymAUKPfbUbSpRY8Ui7az1HCxtpump"
    
    print(f"\nTesting contract: {test_contract}")
    
    # Test validation
    print("\n1. Testing contract validation...")
    is_valid = validate_solana_contract(test_contract)
    print(f"   Contract valid: {is_valid}")
    
    if not is_valid:
        print("ERROR: Invalid contract address format")
        return
    
    # Test token info fetch
    print("\n2. Testing token info fetch...")
    token_info = get_token_info_from_solscan(test_contract)
    
    # Test price data fetch  
    print("\n3. Testing price data fetch...")
    price_data = get_token_price_data(test_contract)
    
    # Test web search strategy
    print("\n4. Testing web search strategy...")
    search_test = test_mcp_web_search(
        test_contract,
        token_info.get("name", ""),
        token_info.get("symbol", "")
    )
    
    # Analyze issues
    print("\n5. Analyzing current system issues...")
    analyze_current_issues()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED!")
    print("=" * 50)

if __name__ == "__main__":
    main()