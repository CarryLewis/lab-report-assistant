"""macOS application entry point; no project data is included in the bundle."""
from app_runtime import main

if __name__ == '__main__':
    raise SystemExit(main())
