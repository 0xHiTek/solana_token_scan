#!/usr/bin/env python3
"""
Test script to verify the token analysis functions work correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import SolanaTokenAnalyzer

def test_analysis():
    print("Testing Solana Token Analyzer...")
    
    # Initialize analyzer
    analyzer = SolanaTokenAnalyzer()
    
    # Test contract address
    test_contract = "6zsNXPkpGHaf8p71wThVTxr5fhtG8yKHw2TrkiKqpump"
    
    print(f"Testing contract: {test_contract}")
    
    # Test token info fetch
    print("\n1. Testing token info fetch...")
    token_info = analyzer.get_token_info_from_solscan(test_contract)
    print(f"Token info result: {token_info}")
    
    # Test price data fetch  
    print("\n2. Testing price data fetch...")
    price_data = analyzer.get_token_price_data(test_contract)
    print(f"Price data result: {price_data}")
    
    # Test social media search (if Exa client is available)
    print("\n3. Testing social media search...")
    if analyzer.exa_client:
        social_results = analyzer.search_x_mentions(
            test_contract,
            token_info.get("name", ""),
            token_info.get("symbol", "")
        )
        print(f"Social results: Found {social_results.get('total_mentions', 0)} mentions")
        
        # Test analysis engine
        print("\n4. Testing engagement analysis...")
        search_data = social_results.get("results", [])
        engagement_analysis = analyzer.analyze_social_engagement(
            search_data,
            test_contract,
            token_info.get("symbol", "")
        )
        
        print(f"Engagement analysis:")
        print(f"   - Total mentions: {engagement_analysis.get('total_mentions', 0)}")
        print(f"   - Relevant mentions: {engagement_analysis.get('relevant_mentions', 0)}")
        print(f"   - Filtered mentions: {engagement_analysis.get('filtered_mentions', 0)}")
        print(f"   - Engagement score: {engagement_analysis.get('engagement_score', 0)}")
        print(f"   - Notable accounts: {len(engagement_analysis.get('notable_accounts', []))}")
        
        # Test investment recommendation
        print("\n5. Testing investment recommendation...")
        recommendation = analyzer.generate_investment_recommendation(
            token_info, price_data, engagement_analysis
        )
        print(f"Recommendation: {recommendation.get('recommendation', 'Unknown')}")
        print(f"   - Score: {recommendation.get('score', 0)}/100")
        print(f"   - Risk level: {recommendation.get('risk_level', 'Unknown')}")
        
    else:
        print("WARNING: Exa client not available - skipping social media tests")
    
    print("\nAnalysis test completed!")

if __name__ == "__main__":
    test_analysis()