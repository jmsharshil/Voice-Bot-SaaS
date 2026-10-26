import sys
import importlib

# Ensure audioop compatibility across Python 3.10 - 3.13
if "audioop" not in sys.modules:
    try:
        importlib.import_module("audioop")
    except ImportError:
        try:
            sys.modules["audioop"] = importlib.import_module("audioop_lts")
        except ImportError:
            pass
