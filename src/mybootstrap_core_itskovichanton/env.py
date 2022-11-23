import argparse
import copy
import os
import sys

from benedict import benedict

from src.mybootstrap_core_itskovichanton.utils import StoreInDict, append_benedict, create_benedict


def get_env_props() -> benedict:
    r = create_benedict(copy.deepcopy(os.environ.__dict__.get("_data")))
    p = argparse.ArgumentParser(prefix_chars=' ')
    p.add_argument("options", nargs="*", action=StoreInDict, default=dict())
    args = p.parse_args(sys.argv[1:])
    append_benedict(r, create_benedict(args.__dict__["options"]))
    return r
