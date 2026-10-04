"""
Console Worker Module Entrypoint

Allows running the console worker as a module:
    python -m primus.console.local_worker
"""

from primus.console.local_worker import main

if __name__ == "__main__":
    main()
