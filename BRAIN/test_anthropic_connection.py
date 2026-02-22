#!/usr/bin/env python3
"""
Simple test to verify Anthropic API connectivity and find working model IDs.
"""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

def test_api_connection():
    """Test basic API connectivity and try different model IDs."""
    print("=" * 60)
    print("ANTHROPIC API CONNECTION TEST")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ ANTHROPIC_API_KEY not found in environment")
        print("  Make sure .env file exists with: ANTHROPIC_API_KEY=your_key_here")
        return

    print(f"\n✓ API key found (starts with: {api_key[:10]}...)")

    # Initialize client
    try:
        client = Anthropic(api_key=api_key)
        print("✓ Anthropic client initialized")
    except Exception as e:
        print(f"\n✗ Failed to initialize client: {e}")
        return

    # Try different model IDs
    models_to_try = [
        # Claude 4.5/4.6 models (newest as of Jan 2025)
        "claude-opus-4-6",
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",

        # Claude 3.5 models
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-haiku-20241022",

        # Generic aliases
        "claude-3-5-sonnet-latest",
        "claude-3-opus-latest",
    ]

    print(f"\n{'=' * 60}")
    print("TESTING MODEL IDs")
    print("=" * 60)

    working_models = []

    for model_id in models_to_try:
        print(f"\nTrying: {model_id}")
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=50,
                messages=[{"role": "user", "content": "Say 'test successful' and nothing else."}]
            )

            result = response.content[0].text
            print(f"  ✓ SUCCESS - Response: {result}")
            working_models.append(model_id)

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not_found" in error_msg:
                print(f"  ✗ Model not found (404)")
            elif "401" in error_msg or "authentication" in error_msg.lower():
                print(f"  ✗ Authentication failed")
            elif "429" in error_msg or "rate_limit" in error_msg.lower():
                print(f"  ✗ Rate limit exceeded")
            else:
                print(f"  ✗ Error: {error_msg[:100]}")

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print("=" * 60)

    if working_models:
        print(f"\n✓ Found {len(working_models)} working model(s):")
        for model in working_models:
            print(f"  - {model}")

        print(f"\nRecommendation: Use '{working_models[0]}' in llm_parser.py")
        print("\nTo update llm_parser.py:")
        print(f"  model: str = \"{working_models[0]}\"")

    else:
        print("\n✗ No working models found!")
        print("\nPossible issues:")
        print("  1. API key is invalid or expired")
        print("  2. API key doesn't have access to these models")
        print("  3. Account has billing issues")
        print("\nCheck your account at: https://console.anthropic.com/settings/keys")
        print("Check billing at: https://console.anthropic.com/settings/billing")

if __name__ == "__main__":
    test_api_connection()
