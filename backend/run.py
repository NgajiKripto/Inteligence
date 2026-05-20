"""
MemeCoin Intelligence - Backend Entry Point
"""

import os
import sys

if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config


def main():
    """Main entry point"""
    errors = Config.validate()
    if errors:
        print("Configuration errors:")
        for err in errors:
            print(f"  - {err}")
        print("\nPlease check .env file configuration")
        sys.exit(1)
    
    app = create_app()
    
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = Config.DEBUG
    
    print(f"\n🚀 MemeCoin Intelligence running on http://{host}:{port}")
    print(f"   Debug mode: {debug}")
    print(f"   LLM Model: {Config.LLM_MODEL_NAME}")
    print(f"   Solana RPC: {Config.SOLANA_RPC_URL[:50]}...")
    print()
    
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    main()
