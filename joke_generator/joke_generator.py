#!/usr/bin/env python3
"""
Random Joke Generator using free external APIs
No authentication required!
"""

import requests
import json
import sys
from typing import Dict, Optional

# Available APIs
JOKE_APIS = {
    "official": "https://official-joke-api.appspot.com/jokes/random",
    "jokeapi": "https://v2.jokeapi.dev/joke/Any",
    "chucknorris": "https://api.chucknorris.io/jokes/random",
}

TIMEOUT = 5  # seconds


def fetch_joke_from_official() -> Optional[Dict]:
    """Fetch from Official Joke API"""
    try:
        response = requests.get(JOKE_APIS["official"], timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        return {
            "type": "official",
            "setup": data.get("setup", ""),
            "punchline": data.get("punchline", ""),
            "success": True,
        }
    except requests.RequestException as e:
        print(f"❌ Official Joke API failed: {e}")
        return None


def fetch_joke_from_jokeapi() -> Optional[Dict]:
    """Fetch from JokeAPI (supports multiple categories)"""
    try:
        response = requests.get(JOKE_APIS["jokeapi"], timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data.get("type") == "twopart":
            setup = data.get("setup", "")
            delivery = data.get("delivery", "")
            return {
                "type": "jokeapi",
                "setup": setup,
                "punchline": delivery,
                "category": data.get("category", "Unknown"),
                "success": True,
            }
        else:
            joke_text = data.get("joke", "")
            return {
                "type": "jokeapi",
                "setup": joke_text,
                "punchline": "",
                "category": data.get("category", "Unknown"),
                "success": True,
            }
    except requests.RequestException as e:
        print(f"❌ JokeAPI failed: {e}")
        return None


def fetch_joke_from_chucknorris() -> Optional[Dict]:
    """Fetch Chuck Norris facts/jokes"""
    try:
        response = requests.get(JOKE_APIS["chucknorris"], timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        return {
            "type": "chucknorris",
            "setup": data.get("value", ""),
            "punchline": "",
            "success": True,
        }
    except requests.RequestException as e:
        print(f"❌ Chuck Norris API failed: {e}")
        return None


def display_joke(joke: Dict) -> None:
    """Pretty print a joke"""
    if not joke or not joke.get("success"):
        print("⚠️  Failed to fetch joke")
        return
    
    api_type = joke.get("type", "unknown")
    setup = joke.get("setup", "")
    punchline = joke.get("punchline", "")
    
    print("\n" + "=" * 60)
    print(f"📝 {api_type.upper()} JOKE API")
    print("=" * 60)
    
    if joke.get("category"):
        print(f"Category: {joke['category']}")
    
    print(f"\n{setup}")
    
    if punchline:
        print(f"\n→ {punchline}")
    
    print("\n" + "=" * 60 + "\n")


def get_random_joke(source: str = "random") -> Dict:
    """
    Fetch a random joke from specified source
    
    Args:
        source: "official", "jokeapi", "chucknorris", or "random"
    
    Returns:
        Joke dict with keys: type, setup, punchline, success, [category]
    """
    
    if source == "random":
        # Try all APIs in random order
        import random
        sources = list(JOKE_APIS.keys())
        random.shuffle(sources)
        
        for api_source in sources:
            joke = get_random_joke(api_source)
            if joke and joke.get("success"):
                return joke
        
        # Fallback if all fail
        return {
            "type": "error",
            "setup": "Why did the API fail? Because it had connectivity issues!",
            "punchline": "Try again later!",
            "success": False,
        }
    
    elif source == "official":
        return fetch_joke_from_official() or {"success": False}
    
    elif source == "jokeapi":
        return fetch_joke_from_jokeapi() or {"success": False}
    
    elif source == "chucknorris":
        return fetch_joke_from_chucknorris() or {"success": False}
    
    else:
        print(f"❌ Unknown source: {source}")
        print(f"   Available: {', '.join(JOKE_APIS.keys())}, random")
        return {"success": False}


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Get random jokes from free APIs (no auth required!)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python joke_generator.py                    # Get random joke from any API
  python joke_generator.py --source official  # Use Official Joke API
  python joke_generator.py --source jokeapi   # Use JokeAPI
  python joke_generator.py --source chucknorris  # Get Chuck Norris facts
  python joke_generator.py --count 3          # Get 3 jokes
  python joke_generator.py --json             # Output as JSON
        """
    )
    
    parser.add_argument(
        "--source",
        choices=list(JOKE_APIS.keys()) + ["random"],
        default="random",
        help="API source to fetch from (default: random)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of jokes to fetch (default: 1)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    jokes = []
    for i in range(args.count):
        print(f"⏳ Fetching joke {i+1}/{args.count}...")
        joke = get_random_joke(args.source)
        jokes.append(joke)
        
        if not args.json:
            display_joke(joke)
    
    if args.json:
        print(json.dumps(jokes, indent=2))


if __name__ == "__main__":
    main()
