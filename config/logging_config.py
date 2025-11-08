"""
Centralized Logging Configuration for FreeFace Email Service

This module provides production-grade logging configuration that:
- Sends all logs to stdout/stderr (Docker-compatible)
- Respects LOG_LEVEL environment variable
- Prevents log duplication through proper propagation management
- Supports granular per-logger control via YAML configuration
- Provides separate handlers for errors (stderr) and info (stdout)

Usage:
    from config.logging_config import setup_logging

    # Initialize logging at application startup
    setup_logging()

    # Use logging as normal
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("This respects LOG_LEVEL environment variable")
"""

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Optional

import yaml


def get_log_level() -> str:
    """
    Get log level from environment variable with validation.

    Returns:
        str: Valid Python logging level name
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    if level not in valid_levels:
        print(
            f"WARNING: Invalid LOG_LEVEL '{level}'. Defaulting to INFO. "
            f"Valid levels: {', '.join(valid_levels)}",
            file=sys.stderr
        )
        return "INFO"

    return level


def get_environment() -> str:
    """
    Get current environment (development, staging, production).

    Returns:
        str: Environment name
    """
    return os.getenv("ENVIRONMENT", "development")


def load_yaml_config(config_path: Optional[Path] = None) -> dict:
    """
    Load logging configuration from YAML file.

    Args:
        config_path: Path to YAML config file. If None, uses default location.

    Returns:
        dict: Logging configuration dictionary
    """
    if config_path is None:
        # Default to logging.yaml in same directory as this file
        config_path = Path(__file__).parent / "logging.yaml"

    if not config_path.exists():
        print(
            f"WARNING: Logging config file not found at {config_path}. "
            "Using basic configuration.",
            file=sys.stderr
        )
        return get_basic_config()

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        print(
            f"ERROR: Failed to load logging config from {config_path}: {e}. "
            "Using basic configuration.",
            file=sys.stderr
        )
        return get_basic_config()


def get_basic_config() -> dict:
    """
    Get basic logging configuration as fallback.

    This is used when YAML config file is not available.
    All logs go to stdout/stderr, respecting LOG_LEVEL.

    Returns:
        dict: Basic logging configuration
    """
    log_level = get_log_level()

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - [%(name)s] - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'stdout': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'stream': 'ext://sys.stdout'
            },
            'stderr': {
                'class': 'logging.StreamHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'stream': 'ext://sys.stderr'
            }
        },
        'loggers': {
            # Uvicorn loggers - prevent duplication
            'uvicorn.error': {
                'level': log_level,
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'uvicorn.access': {
                'level': 'WARNING',  # We'll implement custom access logging
                'handlers': [],
                'propagate': False
            },
            # Application loggers
            'email_system': {
                'level': log_level,
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'api': {
                'level': log_level,
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'worker': {
                'level': log_level,
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'config': {
                'level': log_level,
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'services': {
                'level': log_level,
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'providers': {
                'level': log_level,
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'models': {
                'level': log_level,
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            # Third-party noise control
            'redis': {
                'level': 'WARNING',
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'asyncio': {
                'level': 'WARNING',
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'httpx': {
                'level': 'WARNING',
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            },
            'httpcore': {
                'level': 'WARNING',
                'handlers': ['stdout', 'stderr'],
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['stdout', 'stderr']
        }
    }


def apply_environment_overrides(config: dict) -> dict:
    """
    Apply environment variable overrides to logging config.

    This allows runtime control of log levels per logger via environment variables.
    Example: LOGGER_LEVEL_redis=DEBUG would set redis logger to DEBUG level.

    Args:
        config: Base logging configuration

    Returns:
        dict: Configuration with environment overrides applied
    """
    # Get global log level
    global_log_level = get_log_level()

    # Apply to root logger
    if 'root' in config:
        config['root']['level'] = global_log_level

    # Apply to all loggers that don't have explicit overrides
    if 'loggers' in config:
        for logger_name in config['loggers']:
            # Check for logger-specific override
            env_var = f"LOGGER_LEVEL_{logger_name.replace('.', '_').upper()}"
            override_level = os.getenv(env_var)

            if override_level:
                override_level = override_level.upper()
                if override_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                    config['loggers'][logger_name]['level'] = override_level
                    print(
                        f"Applied environment override: {logger_name} logger set to {override_level}",
                        file=sys.stderr
                    )
            else:
                # Apply global level to application loggers
                if logger_name in ['email_system', 'api', 'worker', 'config', 'services', 'providers', 'models', 'uvicorn.error']:
                    config['loggers'][logger_name]['level'] = global_log_level

    return config


def setup_logging(config_path: Optional[Path] = None) -> None:
    """
    Setup logging configuration for the application.

    This should be called once at application startup, before any loggers are created.

    Features:
    - Loads configuration from YAML file (with fallback to basic config)
    - Applies environment variable overrides
    - Configures all handlers to use stdout/stderr (Docker-compatible)
    - Prevents log duplication through proper propagation management

    Args:
        config_path: Optional path to YAML config file

    Example:
        # At the start of main.py, api.py, worker.py:
        from config.logging_config import setup_logging
        setup_logging()

        # Then use logging normally:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Application started")
    """
    # Get environment info for logging
    env = get_environment()
    log_level = get_log_level()

    # Load configuration
    if config_path and config_path.exists():
        config = load_yaml_config(config_path)
    else:
        # Try default location first
        default_config_path = Path(__file__).parent / "logging.yaml"
        if default_config_path.exists():
            config = load_yaml_config(default_config_path)
        else:
            config = get_basic_config()

    # Apply environment overrides
    config = apply_environment_overrides(config)

    # Apply configuration
    logging.config.dictConfig(config)

    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured - Environment: {env}, Level: {log_level}, "
        f"Config source: {'YAML' if config_path else 'Basic'}"
    )
    logger.debug("Debug logging is enabled")


# Convenience function for testing
def test_logging():
    """
    Test logging configuration by emitting test messages at all levels.

    This is useful for verifying that logging is working correctly.
    """
    setup_logging()

    logger = logging.getLogger(__name__)

    logger.debug("DEBUG: This is a debug message")
    logger.info("INFO: This is an info message")
    logger.warning("WARNING: This is a warning message")
    logger.error("ERROR: This is an error message")
    logger.critical("CRITICAL: This is a critical message")

    # Test different loggers
    for logger_name in ['email_system', 'api', 'worker', 'redis']:
        test_logger = logging.getLogger(logger_name)
        test_logger.info(f"Testing logger: {logger_name}")
        test_logger.debug(f"Debug message from: {logger_name}")


if __name__ == "__main__":
    # Allow testing this module directly
    print("Testing logging configuration...")
    test_logging()
