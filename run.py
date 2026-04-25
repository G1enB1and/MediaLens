import sys
import os
from native.mediamanagerx_app.main import main

if __name__ == '__main__':
    os.environ.setdefault("MEDIALENS_USE_INSTALLED_AI_PATHS", "1")
    sys.exit(main())
