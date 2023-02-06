import argparse
import functools
import os
from collections import abc
from collections.abc import MutableMapping
from inspect import isclass

from benedict import benedict
from dacite import from_dict


def get_attr(obj, path: str | list[str]):
    if type(path) == str:
        path = path.split(".")
    for attr in path:
        if len(attr) == 0:
            continue
        if not hasattr(obj, attr):
            return None
        obj = getattr(obj, attr)
    return obj


def trim_string(s: str, limit: int, ellips='…') -> str:
    if not s:
        return ""
    s = s.strip()
    if len(s) > limit:
        return s[:limit - 1].strip() + ellips
    return s


def omittable_parentheses(maybe_decorator=None, /, allow_partial=False):
    """A decorator for decorators that allows them to be used without parentheses"""

    def decorator(func):
        @functools.wraps(decorator)
        def wrapper(*args, **kwargs):
            if len(args) == 1 and callable(args[0]):
                if allow_partial:
                    return func(**kwargs)(args[0])
                elif not kwargs:
                    return func()(args[0])
            return func(*args, **kwargs)

        return wrapper

    if maybe_decorator is None:
        return decorator
    else:
        return decorator(maybe_decorator)


def infer(b: benedict, keypath: str, default=None, result=None, none_result_violated=True):
    value = b[keypath] if keypath in b else default
    if value is None and none_result_violated:
        raise ValueError(f"Value for key={keypath} has not been provided")
    if value is None and result is None:
        return None

    if type(value) in (dict, benedict) and isclass(result):
        return from_dict(data_class=result, data=value)

    return value


def infer_from_tuple(b: benedict, args):
    if type(args) is tuple:
        if len(args) == 3:
            return infer(b, args[0], default=args[2], result=args[1], none_result_violated=False)
        if len(args) == 2:
            return infer(b, args[0], result=args[1])
        if len(args) == 1:
            return infer(b, args[0])
    if type(args) is str:
        return infer(b, args)
    return None


def create_benedict(a: dict) -> benedict:
    r = benedict()
    b = flatten_dict(a)
    for k, v in b.items():
        if "." in k:
            keys = k.split(".")
            if len(keys) == 1:
                k = keys[0]
        r[k] = v
    return r


def append_benedict(r: benedict, b: benedict):
    b = flatten_dict(b)
    for k, v in b.items():
        if "." in k:
            keys = k.split(".")
            if len(keys) == 1:
                k = keys[0]
        r[k] = v
    return r


class StoreInDict(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        d = getattr(namespace, self.dest)
        for opt in values:
            k, v = opt.split("=", 1)
            k = k.lstrip("-")
            if k in d:
                d[k].append(v)
            else:
                d[k] = v
        setattr(namespace, self.dest, d)


def nested_dict_iter(nested):
    for key, value in nested.items():
        if isinstance(value, abc.Mapping):
            yield from nested_dict_iter(value)
        else:
            yield key, value


def flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '.') -> MutableMapping:
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def is_windows():
    return os.name == 'nt'
