from importlib import import_module
import os

# Allow access to submodules in the accompanying ``view`` package directory
__path__ = [os.path.join(os.path.dirname(__file__), "view")]

# Re-export the main view class
SelectorView = import_module(__name__ + ".orchestrator").SelectorView

__all__ = ["SelectorView"]
