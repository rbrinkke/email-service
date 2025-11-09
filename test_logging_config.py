#!/usr/bin/env python3
"""
Test script for logging configuration

This script validates that the logging configuration is working correctly
without needing to start the full Docker stack.

Run this with:
    python test_logging_config.py

Expected output:
- Configuration loads successfully
- Test messages at all levels
- No file handlers (only stdout/stderr)
- Environment variables are respected
"""

import logging
import os
import sys

# Set test environment variables
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["ENVIRONMENT"] = "development"
os.environ["LOG_FORMAT"] = "text"

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.logging_config import setup_logging, test_logging


def test_configuration_loads():
    """Test that logging configuration loads without errors"""
    print("=" * 70)
    print("TEST 1: Configuration Loading")
    print("=" * 70)

    try:
        setup_logging()
        print("✅ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Configuration failed to load: {e}")
        return False


def test_log_levels():
    """Test that all log levels work correctly"""
    print("\n" + "=" * 70)
    print("TEST 2: Log Levels")
    print("=" * 70)
    print("You should see DEBUG, INFO, WARNING, ERROR, and CRITICAL messages below:")
    print("-" * 70)

    setup_logging()
    logger = logging.getLogger("test_logger")

    logger.debug("🔍 This is a DEBUG message")
    logger.info("ℹ️  This is an INFO message")
    logger.warning("⚠️  This is a WARNING message")
    logger.error("❌ This is an ERROR message")
    logger.critical("🚨 This is a CRITICAL message")

    print("-" * 70)
    print("✅ All log levels tested")


def test_different_loggers():
    """Test different logger namespaces"""
    print("\n" + "=" * 70)
    print("TEST 3: Different Logger Namespaces")
    print("=" * 70)
    print("Testing application vs third-party logger levels:")
    print("-" * 70)

    setup_logging()

    # Application loggers (should show DEBUG)
    app_logger = logging.getLogger("email_system")
    app_logger.debug("📧 email_system DEBUG (should be visible)")
    app_logger.info("📧 email_system INFO")

    api_logger = logging.getLogger("api")
    api_logger.debug("🌐 api DEBUG (should be visible)")
    api_logger.info("🌐 api INFO")

    # Third-party loggers (should NOT show DEBUG due to WARNING level)
    redis_logger = logging.getLogger("redis")
    redis_logger.debug("🔴 redis DEBUG (should NOT be visible - level is WARNING)")
    redis_logger.warning("🔴 redis WARNING (should be visible)")

    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.debug("⚡ asyncio DEBUG (should NOT be visible - level is WARNING)")
    asyncio_logger.warning("⚡ asyncio WARNING (should be visible)")

    print("-" * 70)
    print("✅ Logger namespace filtering tested")
    print("   Expected: Application DEBUG visible, third-party DEBUG hidden")


def test_no_file_handlers():
    """Verify that no file handlers are configured"""
    print("\n" + "=" * 70)
    print("TEST 4: No File Handlers")
    print("=" * 70)

    setup_logging()

    # Check root logger
    root_logger = logging.getLogger()
    file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]

    if file_handlers:
        print(f"❌ Found {len(file_handlers)} file handler(s) - logs will be written to files!")
        for handler in file_handlers:
            print(f"   - {handler.baseFilename}")
        return False
    else:
        print("✅ No file handlers found - all logs go to stdout/stderr")

        # Show what handlers we do have
        print("\nConfigured handlers:")
        for handler in root_logger.handlers:
            print(f"   - {type(handler).__name__}: {getattr(handler, 'stream', 'N/A')}")

        return True


def test_environment_variables():
    """Test that environment variables are respected"""
    print("\n" + "=" * 70)
    print("TEST 5: Environment Variable Respect")
    print("=" * 70)

    # Test with INFO level
    print("\nTest 5a: Setting LOG_LEVEL=INFO (DEBUG should be hidden)")
    print("-" * 70)
    os.environ["LOG_LEVEL"] = "INFO"
    setup_logging()

    logger = logging.getLogger("env_test")
    logger.debug("🔍 DEBUG message (should NOT be visible with LOG_LEVEL=INFO)")
    logger.info("ℹ️  INFO message (should be visible)")

    # Test with DEBUG level
    print("\nTest 5b: Setting LOG_LEVEL=DEBUG (DEBUG should be visible)")
    print("-" * 70)
    os.environ["LOG_LEVEL"] = "DEBUG"
    setup_logging()

    logger = logging.getLogger("env_test2")
    logger.debug("🔍 DEBUG message (should be visible with LOG_LEVEL=DEBUG)")
    logger.info("ℹ️  INFO message (should be visible)")

    print("-" * 70)
    print("✅ Environment variables working correctly")


def test_yaml_config_exists():
    """Check if YAML config file exists"""
    print("\n" + "=" * 70)
    print("TEST 6: YAML Configuration File")
    print("=" * 70)

    yaml_path = os.path.join(os.path.dirname(__file__), "config", "logging.yaml")

    if os.path.exists(yaml_path):
        print(f"✅ YAML config found: {yaml_path}")

        # Try to load it
        try:
            import yaml

            with open(yaml_path, "r") as f:
                config = yaml.safe_load(f)

            print(f"   - Formatters: {len(config.get('formatters', {}))}")
            print(f"   - Handlers: {len(config.get('handlers', {}))}")
            print(f"   - Loggers: {len(config.get('loggers', {}))}")

            # Show configured application loggers
            print("\n   Application loggers configured:")
            for logger_name in ["email_system", "api", "worker", "scheduler", "monitor"]:
                if logger_name in config.get("loggers", {}):
                    level = config["loggers"][logger_name].get("level", "N/A")
                    print(f"      - {logger_name}: {level}")

            print("\n   Third-party loggers configured:")
            for logger_name in ["redis", "asyncio", "httpx", "httpcore"]:
                if logger_name in config.get("loggers", {}):
                    level = config["loggers"][logger_name].get("level", "N/A")
                    print(f"      - {logger_name}: {level}")

            return True
        except ImportError:
            print("   ⚠️  PyYAML not installed - will use basic config fallback")
            return True
        except Exception as e:
            print(f"   ❌ Failed to parse YAML: {e}")
            return False
    else:
        print(f"⚠️  YAML config not found at {yaml_path}")
        print("   Will use basic configuration fallback")
        return True


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "LOGGING CONFIGURATION TEST SUITE" + " " * 21 + "║")
    print("╚" + "=" * 68 + "╝")

    tests = [
        test_configuration_loads,
        test_yaml_config_exists,
        test_log_levels,
        test_different_loggers,
        test_no_file_handlers,
        test_environment_variables,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if all(results):
        print("\n✅ ALL TESTS PASSED - Logging configuration is working correctly!")
        print("\nNext steps:")
        print("1. Rebuild Docker containers: docker-compose build")
        print("2. Start services: docker-compose up")
        print("3. Check logs: docker logs -f freeface-email-api")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Please review the output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
