import os.path


def root_dir() -> str:
    """Utility function to identify the location of source root without hardcoding and attempting to identify elsewhere in the code"""
    return os.path.dirname(os.path.dirname(__file__))
