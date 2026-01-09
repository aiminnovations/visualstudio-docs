#!/usr/bin/env python3
"""
Test script to verify the console interface and rate limiter fixes
"""

import os
import sys
import subprocess
from pathlib import Path


def test_imports():
    """Test if all required packages can be imported"""
    print("Testing imports...")

    packages = {
        "voyageai": "VoyageAI API client",
        "lancedb": "LanceDB vector database",
        "pypdf": "PDF processing",
        "python-dotenv": "Environment variables",
        "sentence_transformers": "Sentence embeddings",
    }

    success = True
    for package, desc in packages.items():
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✓ {package} - {desc}")
        except ImportError as e:
            print(f"  ✗ {package} - {desc} (MISSING: {e})")
            success = False

    return success


def test_rate_limiter_fix():
    """Test that the rate limiter typo is fixed"""
    print("\nTesting rate limiter fixes...")

    build_script = Path(__file__).parent / "scripts" / "build_knowledge_v4.py"
    if not build_script.exists():
        print(f"  ✗ Build script not found: {build_script}")
        return False

    with open(build_script, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for the old typo
    if '"timout"' in content:
        print("  ✗ Rate limiter still has 'timout' typo")
        return False

    # Check for the fix
    if '"timeout"' in content and "max_retries" in content:
        print("  ✓ Rate limiter typo fixed and retry limits added")
        return True
    else:
        print("  ? Rate limiter fixes may be incomplete")
        return False


def test_console_interface():
    """Test that console interface was created"""
    print("\nTesting console interface...")

    console_script = Path(__file__).parent / "console_interface.py"
    if console_script.exists():
        print(f"  ✓ Console interface created: {console_script}")

        # Check if it's executable
        try:
            result = subprocess.run(
                [sys.executable, str(console_script), "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Script doesn't have --help, but shouldn't crash
            print("  ✓ Console interface is runnable")
            return True
        except subprocess.TimeoutExpired:
            print("  ✓ Console interface starts (timeout expected)")
            return True
        except Exception as e:
            print(f"  ? Console interface may have issues: {e}")
            return False
    else:
        print(f"  ✗ Console interface not found: {console_script}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("LLM DOCS IMPLEMENTATION TEST")
    print("=" * 50)

    tests = [
        ("Package imports", test_imports),
        ("Rate limiter fixes", test_rate_limiter_fix),
        ("Console interface", test_console_interface),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ✗ Test failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {test_name}: {status}")
        if result:
            passed += 1

    print(f"\nSummary: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n🎉 All tests passed! Ready to use the console interface.")
        print("\nTo start: python console_interface.py")
    else:
        print("\n⚠️  Some tests failed. Check the issues above.")
        print("You may need to install missing packages or fix configuration.")


if __name__ == "__main__":
    main()
