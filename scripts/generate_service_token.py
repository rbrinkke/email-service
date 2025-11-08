#!/usr/bin/env python3
"""
Service Token Generator
Generate cryptographically secure tokens for service-to-service authentication

Usage:
    # Generate single token (development)
    python scripts/generate_service_token.py

    # Generate token for specific environment
    python scripts/generate_service_token.py --env production

    # Generate token for specific service
    python scripts/generate_service_token.py --service main-app --env live

    # Generate multiple tokens at once
    python scripts/generate_service_token.py --batch 5

    # Export format for .env file
    python scripts/generate_service_token.py --service main-app --format env

Security:
    - Uses secrets module (cryptographically secure random)
    - 160 bits of entropy (40 hex chars)
    - Resistant to brute force attacks
    - URL-safe characters only
"""

import argparse
import secrets
import sys
from typing import List


class ServiceTokenGenerator:
    """Generate and validate service authentication tokens"""

    # Standard token format: st_<env>_<40_hex_chars>
    # Total: ~50 characters
    # Entropy: 160 bits (40 hex chars * 4 bits per hex)

    VALID_ENVIRONMENTS = ['dev', 'development', 'test', 'staging', 'stage', 'prod', 'production', 'live']
    DEFAULT_ENV = 'dev'
    TOKEN_LENGTH = 40  # hex chars (= 20 bytes = 160 bits)

    def __init__(self, environment: str = None):
        """
        Initialize token generator

        Args:
            environment: Target environment (dev, staging, production, etc.)
        """
        self.environment = self._normalize_environment(environment or self.DEFAULT_ENV)

    def _normalize_environment(self, env: str) -> str:
        """
        Normalize environment name to standard format

        Args:
            env: Environment name

        Returns:
            Normalized environment name

        Examples:
            development -> dev
            production -> live
            staging -> staging
        """
        env = env.lower().strip()

        if env not in self.VALID_ENVIRONMENTS:
            print(f"⚠️  Warning: Unknown environment '{env}', using 'dev'")
            return 'dev'

        # Normalize to short forms
        mapping = {
            'development': 'dev',
            'test': 'dev',
            'production': 'live',
            'prod': 'live',
            'stage': 'staging',
        }

        return mapping.get(env, env)

    def generate(self) -> str:
        """
        Generate a cryptographically secure service token

        Returns:
            Service token in format: st_<env>_<40_hex_chars>

        Example:
            st_dev_a1b2c3d4e5f6789012345678901234567890abcd
        """
        # Generate random bytes and convert to hex
        random_hex = secrets.token_hex(self.TOKEN_LENGTH // 2)  # 20 bytes = 40 hex chars

        # Construct token with prefix and environment
        token = f"st_{self.environment}_{random_hex}"

        return token

    def generate_batch(self, count: int) -> List[str]:
        """
        Generate multiple tokens at once

        Args:
            count: Number of tokens to generate

        Returns:
            List of tokens
        """
        return [self.generate() for _ in range(count)]

    @staticmethod
    def validate_format(token: str) -> tuple[bool, str]:
        """
        Validate token format

        Args:
            token: Token to validate

        Returns:
            (is_valid, error_message)
        """
        if not token:
            return False, "Token is empty"

        if not token.startswith('st_'):
            return False, "Token must start with 'st_'"

        parts = token.split('_')
        if len(parts) != 3:
            return False, f"Token must have 3 parts (st_<env>_<random>), got {len(parts)}"

        prefix, env, random_part = parts

        if prefix != 'st':
            return False, f"Invalid prefix '{prefix}', expected 'st'"

        if not random_part:
            return False, "Missing random part"

        if len(random_part) != 40:
            return False, f"Random part must be 40 hex chars, got {len(random_part)}"

        # Check if random part is valid hex
        try:
            int(random_part, 16)
        except ValueError:
            return False, "Random part must be hexadecimal"

        return True, ""

    def print_token_info(self, token: str):
        """
        Print detailed information about a token

        Args:
            token: Token to analyze
        """
        is_valid, error = self.validate_format(token)

        print(f"\n{'='*70}")
        print(f"  SERVICE TOKEN GENERATED")
        print(f"{'='*70}\n")

        print(f"Token:       {token}")
        print(f"Length:      {len(token)} characters")
        print(f"Environment: {self.environment}")
        print(f"Format:      st_<env>_<40_hex_chars>")
        print(f"Entropy:     160 bits (cryptographically secure)")
        print(f"Valid:       {'✓ Yes' if is_valid else '✗ No'}")

        if not is_valid:
            print(f"Error:       {error}")

        print(f"\n{'='*70}")
        print(f"  HOW TO USE")
        print(f"{'='*70}\n")

        print(f"1. Add to .env file:")
        print(f"   SERVICE_TOKEN_<NAME>={token}")
        print(f"")
        print(f"   Example:")
        print(f"   SERVICE_TOKEN_MAIN_APP={token}")
        print(f"")
        print(f"2. Or set as environment variable:")
        print(f"   export SERVICE_TOKEN_MAIN_APP={token}")
        print(f"")
        print(f"3. Use in API requests:")
        print(f"   curl -H 'X-Service-Token: {token}' http://localhost:8010/send")
        print(f"")
        print(f"{'='*70}")
        print(f"  SECURITY NOTES")
        print(f"{'='*70}\n")

        print(f"⚠️  NEVER commit this token to git")
        print(f"⚠️  Use different tokens for dev/staging/production")
        print(f"⚠️  Rotate tokens every 90 days")
        print(f"⚠️  Keep tokens in .env files (which should be .gitignored)")
        print(f"")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate service authentication tokens",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate single dev token
  %(prog)s

  # Generate production token
  %(prog)s --env production

  # Generate token for specific service
  %(prog)s --service main-app --env live

  # Generate 5 tokens at once
  %(prog)s --batch 5

  # Export format for .env file
  %(prog)s --service main-app --format env

  # Just print the token (no formatting)
  %(prog)s --format raw
        """
    )

    parser.add_argument(
        '--env', '--environment',
        default='dev',
        help='Target environment (dev, staging, production) (default: dev)'
    )

    parser.add_argument(
        '--service',
        help='Service name (for .env format output)'
    )

    parser.add_argument(
        '--batch',
        type=int,
        help='Generate multiple tokens at once'
    )

    parser.add_argument(
        '--format',
        choices=['info', 'env', 'raw'],
        default='info',
        help='Output format (default: info)'
    )

    parser.add_argument(
        '--validate',
        help='Validate an existing token instead of generating'
    )

    args = parser.parse_args()

    generator = ServiceTokenGenerator(environment=args.env)

    # Validate mode
    if args.validate:
        is_valid, error = generator.validate_format(args.validate)
        if is_valid:
            print(f"✓ Token is valid: {args.validate}")
            sys.exit(0)
        else:
            print(f"✗ Token is INVALID: {error}")
            sys.exit(1)

    # Batch generation mode
    if args.batch:
        tokens = generator.generate_batch(args.batch)
        print(f"\nGenerated {args.batch} tokens:\n")
        for i, token in enumerate(tokens, 1):
            if args.format == 'env':
                service_name = args.service or f"SERVICE_{i}"
                print(f"SERVICE_TOKEN_{service_name.upper().replace('-', '_')}={token}")
            elif args.format == 'raw':
                print(token)
            else:
                print(f"{i}. {token}")
        print()
        return

    # Single token generation
    token = generator.generate()

    if args.format == 'raw':
        # Just print the token (for piping)
        print(token)

    elif args.format == 'env':
        # .env file format
        service_name = args.service or "YOUR_SERVICE"
        env_var_name = f"SERVICE_TOKEN_{service_name.upper().replace('-', '_')}"
        print(f"\n# Add this to your .env file:")
        print(f"{env_var_name}={token}")
        print()

    else:
        # Full info format (default)
        generator.print_token_info(token)


if __name__ == '__main__':
    main()
