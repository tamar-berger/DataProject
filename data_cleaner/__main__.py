"""
Main entry point for data_cleaner module.

Allows running the CLI via: python -m data_cleaner
"""

from .cli import main

if __name__ == '__main__':
    exit(main())