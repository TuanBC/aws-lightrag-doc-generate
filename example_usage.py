"""
Example usage of the Ethereum Wallet Credit Scoring API
"""

import asyncio
import os
from dotenv import load_dotenv

# Import services directly for testing
from services.etherscan_service import EtherscanService
from services.credit_scoring_service import CreditScoringService


async def test_wallet_scoring(wallet_address: str):
    """
    Test the credit scoring for a wallet address.
    
    Args:
        wallet_address: Ethereum wallet address to analyze
    """
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("ETHERSCAN_API_KEY")
    
    if not api_key:
        print("Error: ETHERSCAN_API_KEY not found in environment variables")
        print("Please copy .env.example to .env and add your API key")
        return
    
    print(f"Analyzing wallet: {wallet_address}")
    print("-" * 60)
    
    # Initialize services
    etherscan_service = EtherscanService(api_key=api_key)
    credit_scoring_service = CreditScoringService()
    
    try:
        # Step 1: Fetch transactions
        print("\n1. Fetching transaction history from Etherscan...")
        transactions = await etherscan_service.fetch_transactions(wallet_address.lower())
        print(f"   Found {len(transactions)} transactions")
        
        if not transactions:
            print("   No transaction history found for this wallet")
            return
        
        # Step 2: Extract features
        print("\n2. Extracting credit features...")
        features = credit_scoring_service.extract_features(transactions, wallet_address.lower())
        print(f"   Extracted {len(features)} features")
        
        # Display some key features
        print("\n   Key Features:")
        key_features = [
            'account_age_days',
            'total_transactions',
            'total_eth_sent',
            'total_eth_received',
            'unique_counterparties',
            'contract_interactions',
            'failed_tx_ratio',
            'days_since_last_tx'
        ]
        for key in key_features:
            if key in features:
                value = features[key]
                if isinstance(value, float):
                    print(f"   - {key}: {value:.4f}")
                else:
                    print(f"   - {key}: {value}")
        
        # Step 3: Fetch card info (optional)
        print("\n3. Fetching additional card information...")
        try:
            card_info = await etherscan_service.fetch_card_info(wallet_address.lower())
            if card_info:
                print(f"   Retrieved {len(card_info)} card attributes")
                print(f"   Card info keys: {list(card_info.keys())[:5]}...")
            else:
                print("   No card information available")
        except Exception as e:
            print(f"   Warning: Could not fetch card info: {e}")
            card_info = None
        
        # Step 4: Calculate credit score
        print("\n4. Calculating credit score...")
        credit_score = credit_scoring_service.calculate_credit_score(features, card_info)
        
        print("\n" + "=" * 60)
        print(f"FINAL CREDIT SCORE: {credit_score:.2f} / 1000")
        print("=" * 60)
        
        # Score interpretation
        if credit_score >= 800:
            rating = "Excellent"
        elif credit_score >= 650:
            rating = "Good"
        elif credit_score >= 500:
            rating = "Fair"
        elif credit_score >= 350:
            rating = "Poor"
        else:
            rating = "Very Poor"
        
        print(f"Credit Rating: {rating}")
        print()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function to test the API"""
    # Example wallet addresses (you can replace with any valid Ethereum address)
    test_wallets = [
        "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",  # Vitalik Buterin
        # Add more wallet addresses to test
    ]
    
    for wallet in test_wallets:
        await test_wallet_scoring(wallet)
        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    print("Ethereum Wallet Credit Scoring - Test Script")
    print("=" * 60)
    asyncio.run(main())
