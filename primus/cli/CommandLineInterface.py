"""
Entry point module for backward compatibility.
This module imports and re-exports the main CLI function from the correct location.
"""

from primus.cli.shared.CommandLineInterface import main

__all__ = ['main']