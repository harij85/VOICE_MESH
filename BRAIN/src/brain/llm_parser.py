"""
LLM-based command parser using Claude API.
Converts natural language to structured scene commands.
"""
import json
import os
from typing import Any, Dict, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMCommandParser:
    """Parses natural language commands using Claude."""

    SYSTEM_PROMPT = """You are a command parser for a 3D scene renderer. Parse natural language into structured scene commands.

Available primitives: rounded_box, rounded_slab, cylinder, sphere, capsule, torus
Available categories: generic, consumer_electronics, product_container, audio_device, controller
Available colors: red, blue, green, purple, pink, orange, white, black, electric blue, or hex codes
Available styles: futuristic_holo, wireframe, clay, glossy_studio, matte_studio

Return ONLY valid JSON matching this schema:
{
  "object": {"name": str, "category": str} (optional),
  "shape_hint": {
    "primitive": str,
    "features": list,
    "dimensions": {
      "width": float (0.05-5.0),
      "height": float (0.05-5.0),
      "depth": float (0.05-5.0),
      "radius": float (0.05-3.0),
      "thickness": float (0.01-1.0),
      "segments": int (8-128)
    } (optional)
  } (optional),
  "material": {"color": str, "roughness": float} (optional),
  "camera": {"orbit": bool, "distance": float} (optional),
  "presentation": {"style": str} (optional),
  "fx": {"outline": float, "bloom": float, "alpha": float} (optional)
}

Dimension Adjective Mapping:
- "tall" → increase height (e.g., height: 1.5-2.0)
- "short" → decrease height (e.g., height: 0.3-0.6)
- "wide" → increase width (e.g., width: 1.2-1.8)
- "narrow" / "thin" → decrease width (e.g., width: 0.2-0.4)
- "thick" → increase depth or thickness (e.g., depth: 0.5-0.8)
- "small" → decrease all dimensions (e.g., radius: 0.3, height: 0.5)
- "large" / "big" → increase all dimensions (e.g., radius: 1.0, height: 1.5)

Examples:
"show me a phone" → {"object": {"name": "phone", "category": "consumer_electronics"}, "shape_hint": {"primitive": "rounded_box", "features": [], "dimensions": {"width": 0.35, "height": 0.75, "depth": 0.08}}, "camera": {"orbit": true}}
"show me a tall cylinder" → {"object": {"name": "tall cylinder", "category": "generic"}, "shape_hint": {"primitive": "cylinder", "dimensions": {"radius": 0.3, "height": 2.0}}, "camera": {"orbit": true}}
"show me a small blue sphere" → {"object": {"name": "small sphere", "category": "generic"}, "shape_hint": {"primitive": "sphere", "dimensions": {"radius": 0.3}}, "material": {"color": "#4b7bff"}, "camera": {"orbit": true}}
"make it red" → {"material": {"color": "#ff2b2b"}}
"make it wider" → {"shape_hint": {"dimensions": {"width": 1.2}}}
"make it taller" → {"shape_hint": {"dimensions": {"height": 1.8}}}
"zoom in" → {"camera": {"distance": 1.6}}
"more bloom" → {"fx": {"bloom": 0.35}}

Only include fields that are mentioned in the command. Return {} for unknown commands."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-5-20250929"):
        """
        Initialize Claude API client.

        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key parameter."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        print(f"[llm] Initialized with model: {model}")

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language command into structured scene patch.

        Args:
            text: Natural language command

        Returns:
            dict: Scene patch to apply, or {} if command not understood
        """
        print(f"[llm] Parsing: '{text}'")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": text}],
            )

            # Extract JSON from response
            content = response.content[0].text.strip()
            print(f"[llm] Response: {content}")

            # Try to parse JSON
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.endswith("```"):
                content = content[:-3]  # Remove ```
            content = content.strip()

            patch = json.loads(content)
            print(f"[llm] Parsed patch: {patch}")

            return patch

        except json.JSONDecodeError as e:
            print(f"[llm] JSON parse error: {e}")
            print(f"[llm] Raw response: {content}")
            return {}
        except Exception as e:
            print(f"[llm] Error: {e}")
            return {}


def test_llm_parser():
    """Test function: Parse various natural language commands."""
    print("\n=== Step 3: LLM Command Parser Test ===")
    print("This will test parsing natural language with Claude API.\n")

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("✗ Test failed! ANTHROPIC_API_KEY not set.")
        print("\nSetup instructions:")
        print("  1. Get API key from https://console.anthropic.com/")
        print("  2. Create .env file in BRAIN directory:")
        print("     ANTHROPIC_API_KEY=your_api_key_here")
        print("  3. Run: pip install anthropic python-dotenv")
        return

    # Initialize parser
    try:
        parser = LLMCommandParser()
    except Exception as e:
        print(f"✗ Failed to initialize parser: {e}")
        return

    # Test commands
    test_commands = [
        "show me a phone prototype",
        "make it red",
        "show me a blue bottle",
        "zoom in closer",
        "make it more futuristic",
        "add more bloom and glow",
        "stop rotating",
        "fade out slowly",
    ]

    print("Testing command parsing:\n")
    passed = 0
    failed = 0

    for cmd in test_commands:
        print(f"Command: '{cmd}'")
        patch = parser.parse(cmd)

        if patch:
            print(f"  ✓ Parsed successfully")
            print(f"  → {json.dumps(patch, indent=2)}")
            passed += 1
        else:
            print(f"  ✗ Failed to parse or returned empty")
            failed += 1
        print()

    # Summary
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(test_commands)} commands parsed successfully")

    if passed == len(test_commands):
        print("\n✓ Test passed! All commands parsed correctly.")
        print("\nNext step: python -m brain.ws_client")
    else:
        print(f"\n⚠ {failed} commands failed to parse.")
        print("  This may be due to LLM variability. Review the outputs above.")


if __name__ == "__main__":
    test_llm_parser()
