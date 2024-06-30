import argparse
import asyncio
import base64
import subprocess
import os
import dataclasses
import decimal
import functools
import hashlib
import hmac
import os
import random
import re
import string
import sys
import time
import traceback
import urllib
import uuid
from collections import abc
from collections.abc import MutableMapping
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum, EnumType
from inspect import isclass
from typing import Any, Callable, List, Set, Tuple, TypeVar, Dict
from urllib.error import URLError
from urllib.parse import urlparse, urlencode, urlunparse

import psutil
import schedule
from benedict import benedict
from dacite import from_dict
from dataclasses_json import LetterCase, dataclass_json
from dateutil.relativedelta import relativedelta

from src.mybootstrap_core_itskovichanton.structures import CaseInsensitiveDict


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
            try:
                k, v = opt.split("=", 1)
                k = k.lstrip("-")
                if k in d:
                    d[k].append(v)
                else:
                    d[k] = v
            except:
                ...
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


def synchronized(lock):
    def wrapper(f):
        def inner(*args, **kwargs):
            with lock:
                return f(*args, **kwargs)

        return inner

    return wrapper


def remove_self_closed_xml_tags(s):
    return re.sub("<[^>]+?/>", "", s)


def generate_tag() -> str:
    return str(uuid.uuid1().int)


def generate_uid() -> str:
    return str(uuid.uuid1())


def md5(a: str):
    return hashlib.md5(a.encode('utf-8')).hexdigest()


def replace_attrs(obj, filter_type,
                  mapper: Callable[[Any, str, Any], Any],
                  collection_mapper: Callable[[Any], Any] = lambda x: x,
                  is_collection: Callable[[Any], bool] = lambda x: True):
    if obj is None or isinstance(obj, Enum):
        return obj
    # print(type(obj), ": ")
    if isinstance(obj, filter_type):
        return mapper(obj, "self", obj)
    if isinstance(obj, object):
        try:
            for attr, value in obj.__dict__.copy().items():
                if value is None or attr.startswith("_"):
                    continue
                # print("\t", attr)
                if isinstance(value, (List, Set, Tuple)) and is_collection(value):
                    value = [replace_attrs(x, filter_type, mapper, collection_mapper, is_collection) for x in value]
                    try:
                        value = collection_mapper(value)
                    except BaseException as e1:
                        ...
                        # print("attr: ", attr, "\terror: ", e1)
                    setattr(obj, attr, value)
                else:
                    try:
                        value = replace_attrs(value, filter_type, mapper, collection_mapper, is_collection)
                        setattr(obj, attr, value)
                    except BaseException as e1:
                        # print("attr: ", attr, "\terror: ", e1)
                        ...
            return obj
        except BaseException as e:
            # print("out of for\t")
            # print("error: ", e)
            return obj
    else:
        return obj


def list_to_map(obj):
    r = dict()
    for kv in obj:
        r.update(kv)
    return r


def to_dict(obj, remove_none_values: bool = False):
    try:
        obj_dict = dict(obj)
    except:
        obj_dict = {}
    r = obj.__dict__ if hasattr(obj, "__dict__") else obj_dict
    if not r and obj_dict:
        r = obj_dict
    if remove_none_values:
        r = {k: v for k, v in r.items() if v is not None}
    return r


def encode_json_value(_, obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj


def to_dict_deep(obj, route=(),
                 is_value_object: Callable[[tuple, str], bool] = None,
                 key_mapper: Callable[[tuple, str], str] = lambda _, x: x,
                 value_mapper: Callable[[tuple, Any], Any] = lambda _, x: x):
    if (is_value_object and is_value_object(route, obj)) or callable(obj):
        return value_mapper(route, obj)
    if not isinstance(obj, dict) and (
            (not obj) or isinstance(obj, (Enum, str, int, float, date, datetime, Decimal, timedelta)) or isclass(obj)):
        return value_mapper(route, obj)
    if isinstance(obj, (List, Set, Tuple)):
        return [to_dict_deep(x, route, is_value_object, key_mapper, value_mapper) for x in list(obj)]
    r = {}
    if isinstance(obj, CaseInsensitiveDict):
        obj = dict(obj)
    try:
        for attr, value in to_dict(obj).items():
            if value is None or attr.startswith("_"):
                continue
            new_route = (*route, attr)
            attr = key_mapper(new_route, attr)
            if isinstance(value, (List, Set, Tuple)):
                value = [to_dict_deep(x, new_route, is_value_object, key_mapper, value_mapper) for x in value]
                r.setdefault(attr, value)
            else:
                try:
                    value = to_dict_deep(value, new_route, is_value_object, key_mapper, value_mapper)
                    r.setdefault(attr, value)
                except BaseException as e1:
                    # print("attr: ", attr, "\terror: ", e1)
                    ...
        return r
    except BaseException as e:
        # print("out of for\t")
        # print("error: ", e)
        return value_mapper(route, obj)


# https://stackoverflow.com/questions/7555335/how-to-convert-a-string-from-cp-1251-to-utf-8
def win1251_to_utf8(s: str):
    return s.encode("cp1251").decode('cp1251').encode('utf8')


def utf8_to_win1251(s: str):
    return s.encode("utf8").decode('utf8').encode('cp1251')


def trim_string(s: str, limit: int, ellipsis='…') -> str:
    s = s.strip()
    if len(s) > limit:
        return s[:limit - 1].strip() + ellipsis
    return s


def convert_to_int(s, default=0):
    if not s:
        return default
    try:
        i = int(s)
    except ValueError as e:
        i = default
    return i


def random_str(length: int):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# конструирует объект типа cl - со всеми рандомными полями
def fill_random(cl, pkg=None, generators: dict[type, Callable[[], Any]] = None):
    if not pkg:
        pkg = cl.__module__

    if hasattr(cl, "__forward_arg__"):
        cl = cl.__forward_arg__

    if type(cl) == str:
        root = sys.modules[pkg]
        for part in cl.split("."):
            if hasattr(root, part):
                root = getattr(root, part)
        cl = root

    if generators:
        generator = generators.get(cl)
        if generator:
            return generator()

    if cl == str:
        return random_str(random.randint(0, 30))
    if cl == bool:
        return random.randint(0, 10) < 5
    if cl in (float, int, decimal.Decimal):
        return random.randint(1, int(10e+4))
    if type(cl) == EnumType:
        values = [e.value for e in cl]
        return values[random.randint(0, len(values) - 1)]

    o = cl()
    print(cl)

    if hasattr(cl, "__dataclass_fields__"):
        for k, v in cl.__dataclass_fields__.items():
            vtype = v.type
            vtype_vars = vars(vtype)
            vtype_name = vtype_vars.get("_name")
            if not vtype_name:
                setattr(o, k, fill_random(vtype, pkg, generators))
                continue
            vtype_args = vtype_vars.get("__args__")
            unwrapped_type = vtype_args[0]
            if vtype_name.upper() == "LIST":
                setattr(o, k, [fill_random(unwrapped_type, pkg, generators) for _ in range(0, random.randint(5, 10))])
            else:
                setattr(o, k, fill_random(unwrapped_type, pkg, generators))

    return o


def concat_lists(l1, l2):
    if l1 is None and l2 is None:
        return None
    if l1 is None:
        l1 = []
    if l2 is None:
        l2 = []

    return l1 + l2


def get_basic_auth_header(username, password, add_basic: bool = True):
    r = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
    if add_basic:
        r = f"Basic {r}"
    return r


def find_by_key(d, k):
    for a, b in d.items():
        if a == k:
            return b
        if type(b) == dict:
            return find_by_key(b, k)


def to_dataclass(x, T):
    field_names = set(f.name for f in dataclasses.fields(T))
    r = T()
    for k, v in x.__dict__.items():
        setattr(r, k, v)
    return r


def last_day_of_month(date):
    return date.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)


def js(cl, letter_case=LetterCase.CAMEL):
    return dataclass_json(letter_case=letter_case)(dataclasses.dataclass(cl))


def add_params_to_url(url, params):
    url_parts = list(urlparse(url))
    query = url_parts[4]
    query = dict((k, v) for k, v in [p.split('=') for p in query.split('&')]) if query else {}
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlunparse(url_parts)


def unescape_str(s: str):
    return s.encode('raw_unicode_escape').decode('unicode_escape')


def async_decorator(sync_decorator):
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped_func(*args, **kwargs):
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, functools.partial(sync_decorator, func)
            )
            return result(*args, **kwargs)

        return wrapped_func

    return wrapper


def repeat(interval=0, count=-1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            n = 0
            while (count >= 0 and n < count) or (count < 0):
                func(*args, **kwargs)
                n += 1
                if interval > 0:
                    time.sleep(interval)

        return wrapper

    return decorator


def run_once(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            result = f(*args, **kwargs)
            wrapper.has_run = True
            return result

    wrapper.has_run = False
    return wrapper


def parse_http_params(params_string):
    params_dict = {}
    params_list = params_string.split('&')
    for param in params_list:
        key_value_pair = param.split('=')
        key = urllib.parse.unquote(key_value_pair[0])
        value = urllib.parse.unquote(key_value_pair[1])
        params_dict[key] = value
    return params_dict


def generate_unique_int():
    r = uuid.uuid1()
    unique_int = int(r.int >> 96)
    return unique_int


def is_base64(string: str) -> bool:
    try:
        encoded = string.encode('ascii')
        decoded = base64.b64decode(encoded)
        if encoded.strip()[-2:] == b'==':
            return True
        return False
    except:
        return False


def is_sequence(a):
    return isinstance(a, (list, tuple, str, dict, set))


def is_listable(a):
    return isinstance(a, (list, tuple))


def silent_catch(_func=None, *, exception=None):
    return catch(_func=_func, exception=exception, silent=True)


def catch(_func=None, *, exception=None, handler=None, silent=False):
    if not exception:
        exception = Exception
    if type(exception) == list:
        exception = tuple(exception)

    def decorator_catch(func):
        @functools.wraps(func)
        def wrapper_catch(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseException as e:
                if not silent:
                    if not handler:
                        traceback.print_exc()
                    else:
                        handler(e)

        return wrapper_catch

    if _func is None:
        return decorator_catch
    else:
        return decorator_catch(_func)


def singleton(func):
    singleton_cache = {}

    def calc_hash(k):
        try:
            return hash(k)
        except:
            return str(id(k))

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = args
        if kwargs:
            key += (frozenset(kwargs.items()),)
        key = tuple(calc_hash(k) for k in key)
        if key not in singleton_cache:
            singleton_cache[key] = func(*args, **kwargs)
        return singleton_cache[key]

    return wrapper


def scheduled(everyday_time):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            schedule.every().day.at(everyday_time).do(func, *args, **kwargs)
            while True:
                schedule.run_pending()
                time.sleep(1)

        return wrapper

    def decorator_class_method(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            schedule.every().day.at(everyday_time).do(func, self, *args, **kwargs)
            while True:
                schedule.run_pending()
                time.sleep(1)

        return wrapper

    def decorate(func):
        if hasattr(func, '__call__'):
            return decorator(func)
        else:
            return decorator_class_method(func)

    return decorate


def wrap_exception(wrapper: Callable[[BaseException], BaseException], suppress_if_wrapped_to_none=False):
    def decorator(func):
        def wrapper_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseException as e:
                wrapped = wrapper(e)
                if wrapped:
                    raise wrapped
                if not suppress_if_wrapped_to_none:
                    raise e

        return wrapper_func

    return decorator


A = TypeVar('A')
B = TypeVar('B')


def execute_parallel(ops: list[Tuple[Callable, List, Dict]], pool=None):
    ops = [op for op in ops if op]
    if not ops:
        return
    if not pool:
        pool = ThreadPoolExecutor()

    with pool as executor:
        for op in ops:
            if len(op) == 1:
                executor.submit(op[0])
            elif len(op) == 2:
                executor.submit(op[0], *op[1])
            elif len(op) == 2:
                executor.submit(op[0], *op[1], **op[2])


def calc_parallel(args, operation: Callable[[A], B], pool=None) -> dict[A, B]:
    result_dict = {}
    if not args:
        return result_dict

    def execute_operation(arg):
        result = operation(arg)
        result_dict[arg] = result

    if not pool:
        pool = ThreadPoolExecutor()
    with pool as executor:
        executor.map(execute_operation, args)

    return result_dict


_DEFAULT_POOL = ThreadPoolExecutor()


def threaded(executor=None):
    def decorator(f):
        @functools.wraps(f)
        def wrapper_threaded(*args, **kwargs):
            return (executor or _DEFAULT_POOL).submit(f, *args, **kwargs)

        return wrapper_threaded

    return decorator


def hashed(cls):
    def eq(self, other):
        if not isinstance(other, cls):
            return NotImplemented
        return all(getattr(self, field.name) == getattr(other, field.name) for field in dataclasses.fields(cls))

    def hash_(self):
        return hash(tuple(getattr(self, field.name) for field in dataclasses.fields(cls)))

    cls.__eq__ = eq
    cls.__hash__ = hash_
    return cls


def is_network_connection_failed(ex: BaseException) -> bool:
    return isinstance(ex, (ConnectionError, URLError, TimeoutError))


def get_systemd_service_name(process=None):
    if not process:
        try:
            # Попробуем использовать переменную окружения `INVOCATION_ID`
            invocation_id = os.getenv('INVOCATION_ID')
            if invocation_id:
                result = subprocess.run(
                    ['systemctl', 'show', '-p', 'Id', '--value', invocation_id],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                service_name = result.stdout.strip()
                if service_name:
                    return service_name

            # Переход к чтению из `/proc/self/cgroup` в случае отсутствия `INVOCATION_ID`
            with open('/proc/self/cgroup') as f:
                for line in f:
                    fields = line.strip().split(':')
                    if len(fields) == 3 and 'systemd' in fields[1]:
                        path = fields[2]
                        if '/system.slice' in path:
                            service_name = path.split('/')[-1]
                            return service_name
        except Exception as e:
            print(f"err: {e}")

        return None

    try:
        cmdline = process.cmdline()
        for arg in cmdline:
            if arg.startswith("--unit="):
                return arg.split("--unit=")[1]
    except psutil.Error:
        pass

    return None


def get_systemd_service_for_pid(pid=None):
    if not pid:
        pid = os.getpid()
    process = psutil.Process(pid)
    return get_systemd_service_name(process)


def create_hmac_sha256(data, key):
    hashed = hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256)
    return hashed.hexdigest()
