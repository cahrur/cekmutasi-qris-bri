"""
Entry point for running the application as a module
Usage: python -m app
"""
import asyncio
from app.main import main

if __name__ == "__main__":
    asyncio.run(main())
