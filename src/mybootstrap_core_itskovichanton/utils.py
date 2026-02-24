import argparse
import asyncio
import base64
import dataclasses
import decimal
import functools
import hashlib
import hmac
import inspect
import os
import random
import re
import socket
import string
import subprocess
import sys
import threading
import time
import traceback
import urllib
import uuid
import zlib
from collections import abc
from collections.abc import MutableMapping
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum, EnumType
from inspect import isclass
from typing import Any, Callable, List, Set, Tuple, TypeVar, Dict, Optional
from urllib.error import URLError
from urllib.parse import urlparse, urlencode, urlunparse

import psutil
import requests
import schedule
from benedict import benedict
from dacite import from_dict
from dataclasses_json import LetterCase, dataclass_json
from dateutil.relativedelta import relativedelta
from xsdata.models.datatype import XmlDate, XmlDateTime, XmlTime

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


def generate_uid(version: int = 1) -> str:
    if version == 4:
        return str(uuid.uuid4())
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
    if isinstance(obj, Dict):
        return obj
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


def is_standard_value_object(obj):
    return isinstance(obj,
                      (Enum, str, int, float, date, datetime, Decimal, timedelta, XmlDate, XmlTime,
                       XmlDateTime)) or isclass(obj)


def to_dict_deep(obj, route=(),
                 is_value_object: Callable[[tuple, str], bool] = None,
                 key_mapper: Callable[[tuple, str], str] = lambda _, x: x,
                 value_mapper: Callable[[tuple, Any], Any] = lambda _, x: x):
    if obj is None:
        return None
    if isinstance(obj, Enum):
        return value_mapper(route, obj.value)
    if (is_value_object and is_value_object(route, obj)) or callable(obj):
        return value_mapper(route, obj)
    if not isinstance(obj, dict) and ((not obj) or is_standard_value_object(obj)):
        return value_mapper(route, obj)
    if isinstance(obj, (List, Set, Tuple)):
        return [to_dict_deep(x, route, is_value_object, key_mapper, value_mapper) for x in list(obj)]
    r = None
    if isinstance(obj, CaseInsensitiveDict):
        obj = dict(obj)
    try:
        for attr, value in to_dict(obj).items():
            if value is None or attr.startswith("_"):
                continue
            new_route = (*route, attr)
            attr = key_mapper(new_route, attr)
            if (is_value_object and is_value_object(route, value)) or callable(value) or is_standard_value_object(
                    value):
                value = value_mapper(route, value)
                if not r:
                    r = {}
                r.setdefault(attr, value)
            elif isinstance(value, (List, Set, Tuple)):
                value = [to_dict_deep(x, new_route, is_value_object, key_mapper, value_mapper) for x in value]
                if not r:
                    r = {}
                r.setdefault(attr, value)
            else:
                try:
                    value = to_dict_deep(value, new_route, is_value_object, key_mapper, value_mapper)
                    if not r:
                        r = {}
                    r.setdefault(attr, value)
                except BaseException as e1:
                    print("attr: ", attr, "\terror: ", e1)
                    ...
        return r
    except BaseException as e:
        print("out of for\t")
        print("error: ", e)
        return value_mapper(route, obj)


def convert_windows1251_to_utf8(text):
    # Таблица маппинга русских символов Windows-1251 на UTF-8
    mapping = {
        1040: 'А', 1041: 'Б', 1042: 'В', 1043: 'Г',
        1044: 'Д', 1045: 'Е', 1028: 'Ё', 1046: 'Ж',
        1047: 'З', 1048: 'И', 1049: 'Й', 1050: 'К',
        1051: 'Л', 1052: 'М', 1053: 'Н', 1054: 'О',
        1055: 'П', 1056: 'Р', 1057: 'С', 1058: 'Т',
        1059: 'У', 1060: 'Ф', 1061: 'Х', 1062: 'Ц',
        1063: 'Ч', 1064: 'Ш', 1065: 'Щ', 1066: 'Ъ',
        1067: 'Ы', 1068: 'Ь', 1069: 'Э', 1070: 'Ю',
        1071: 'Я', 1072: 'а', 1073: 'б', 1074: 'в',
        1075: 'г', 1076: 'д', 1077: 'е', 1100: 'ё',
        1078: 'ж', 1079: 'з', 1080: 'и', 1081: 'й',
        1082: 'к', 1083: 'л', 1084: 'м', 1085: 'н',
        1086: 'о', 1087: 'п', 1088: 'р', 1089: 'с',
        1090: 'т', 1091: 'у', 1092: 'ф', 1093: 'х',
        1094: 'ц', 1095: 'ч', 1096: 'ш', 1097: 'щ',
        1098: 'ъ', 1099: 'ы', 1100: 'ь', 1101: 'э',
        1102: 'ю', 1103: 'я',
    }

    utf8_text = ''

    for char in text:
        char_code = ord(char)
        if char_code in mapping:
            utf8_text += mapping[char_code]
        else:
            utf8_text += char  # Оставляем символ без изменений, если он не в маппинге

    return utf8_text


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
    if cl == object:
        return f"OBJECT<{random_str(random.randint(0, 20))}>"

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
                try:
                    func(*args, **kwargs)
                except BaseException as ex:
                    if "takes" not in str(ex):
                        raise ex
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
    return catch(_func=_func, exception=exception, silent=False)


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


singleton_cache = {}
cache_timestamps = {}


def clear_singleton_cache(key_prefix):
    clear_dict_with_key_prefix(singleton_cache, key_prefix)


def calc_hash(k):
    try:
        return hash(k)
    except:
        return str(id(k))


def clear_dict_with_key_prefix(d: dict, key_prefix=None):
    if not key_prefix:
        d.clear()
        return

    key_prefix_hash = calc_hash(key_prefix)
    keys_to_remove = [k for k in d if k[0] == key_prefix_hash]
    for k in keys_to_remove:
        del d[k]


@omittable_parentheses()
def singleton(ttl=None):
    def decorator(func):

        is_async = inspect.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            nonlocal ttl
            key = args

            if kwargs:
                key += (frozenset(kwargs.items()),)

            key = tuple(calc_hash(k) for k in key + (get_method_name(func),))

            if key in cache_timestamps:
                if ttl is not None and 0 < ttl < (time.time() - cache_timestamps[key]):
                    del singleton_cache[key]
                    del cache_timestamps[key]

            if key not in singleton_cache:
                singleton_cache[key] = await func(*args, **kwargs)
                cache_timestamps[key] = time.time()

            return singleton_cache[key]

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            nonlocal ttl
            key = args

            if kwargs:
                key += (frozenset(kwargs.items()),)

            key = tuple(calc_hash(k) for k in key + (get_method_name(func),))

            if key in cache_timestamps:
                if ttl is not None and 0 < ttl < (time.time() - cache_timestamps[key]):
                    del singleton_cache[key]
                    del cache_timestamps[key]

            if key not in singleton_cache:
                singleton_cache[key] = func(*args, **kwargs)
                cache_timestamps[key] = time.time()

            return singleton_cache[key]

        return async_wrapper if is_async else sync_wrapper

    return decorator


class SingletonCache:
    def __init__(self):
        self._lazy_singletons = {}

    def get_singleton_decorator(self, ttl):
        if ttl not in self._lazy_singletons:
            self._lazy_singletons[ttl] = singleton(ttl=ttl)
        return self._lazy_singletons[ttl]


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


def get_current_thread_id():
    current_thread = threading.current_thread()
    return current_thread.ident


def to_base64(s, encoding='utf-8') -> str:
    return base64.b64encode(s.encode(encoding)).decode("ascii")


def get_by_route(m: dict, *args):
    for s in args:
        m = m.get(s)
        if m is None:
            return
    return m


def get_method_name(m):
    if hasattr(m, "__self__") and m.__self__ is not None:
        cls = m.__self__.__class__.__name__
    else:
        cls = m.__qualname__.split(".")[0]
    return f"{cls}.{m.__name__}"


@dataclasses.dataclass
class UrlCheckResult:
    host: str | None
    port: int | None
    response_time_ms: float = None
    status: str | None = None
    error: str | None = None


def check_url_availability_with_socket(host, port, timeout=3) -> UrlCheckResult:
    start = time.time()
    status = "available"
    error = None

    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except Exception as e:
        status = "unavailable"
        error = str(e)
    finally:
        response_time = round((time.time() - start) * 1000, 2)

    return UrlCheckResult(
        host=host,
        port=port,
        status=status,
        error=error,
        response_time_ms=response_time
    )


def check_url_availability_by_url(url: str, timeout: int = 3) -> UrlCheckResult:
    if url.startswith("http"):
        return check_url_availability_by_url_with_http_request(url, timeout)

    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port
    return check_url_availability_with_socket(host, port, timeout)


def check_url_availability_by_url_with_http_request(url: str, timeout: int = 3) -> UrlCheckResult:
    response = None
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port
    r = UrlCheckResult(host=host, port=port, status="available")
    try:
        response = requests.head(url, timeout=timeout)
        response.raise_for_status()
        return r
    except BaseException as ex:
        msg = str(ex)
        if response:
            msg += f", response: {trim_string(response.text, limit=300)}"
        r.error = msg
        r.status = "unavailable"
        return r


def remove_last_path_fragments(url: str, n: int = 1) -> str:
    parsed = urlparse(url)

    parts = parsed.path.rstrip("/").split("/")

    if n > 0:
        parts = parts[:-n] if n < len(parts) else []

    new_path = "/" + "/".join(parts) if parts else ""

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        new_path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def map_if_type_or_collection(value, t, mapper):
    # Если одиночный объект типа T → вернуть список с одним преобразованным элементом
    if isinstance(value, t):
        return mapper(value)

    # Если это коллекция — пройтись по элементам
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            if isinstance(item, t):
                result.append(mapper(item))
            else:
                result.append(item)
        return result

    # Всё остальное — в список как есть
    return value


def threaded_async(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        def runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            coro = func(*args, **kwargs)
            loop.run_until_complete(coro)
            loop.run_forever()

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        return thread

    return wrapper


def to_sync(
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        wait: bool = False,
        timeout: Optional[float] = None,
        return_future: bool = False,
        detect_loop_from_self: bool = True  # Новая опция!
):
    """
    Универсальный декоратор для преобразования async функции в sync.

    Параметры:
        loop: конкретный event loop для запуска
        wait: ждать ли завершения (True) или вернуть Future (False)
        timeout: таймаут ожидания
        return_future: всегда возвращать Future, даже если есть работающий loop
        detect_loop_from_self: автоматически искать _event_loop в self (первом аргументе)
    """

    def decorator(async_func: Callable) -> Callable:
        @functools.wraps(async_func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # Определяем target loop
            target_loop = loop

            # Автоматическое определение loop из self объекта
            if detect_loop_from_self and target_loop is None and args:
                # Пытаемся найти self (первый аргумент может быть self для метода)
                potential_self = args[0]

                # Проверяем, что это объект, а не класс
                if hasattr(potential_self, '__class__'):
                    # Ищем event loop в разных возможных атрибутах
                    for attr_name in ['_event_loop', 'event_loop', 'loop', '_loop']:
                        if hasattr(potential_self, attr_name):
                            attr_value = getattr(potential_self, attr_name)
                            if isinstance(attr_value, asyncio.AbstractEventLoop):
                                target_loop = attr_value
                                break

            # Определяем контекст
            try:
                current_loop = asyncio.get_running_loop()
                in_async_context = True
            except RuntimeError:
                current_loop = None
                in_async_context = False

            # Выбор стратегии
            if in_async_context and not return_future:
                if wait:
                    if timeout:
                        return asyncio.wait_for(
                            async_func(*args, **kwargs),
                            timeout=timeout
                        )
                    # Для wait=True в async контексте нужен await
                    # Но мы в sync-обертке, поэтому запускаем синхронно
                    task = current_loop.create_task(async_func(*args, **kwargs))
                    if timeout:
                        return asyncio.wait_for(task, timeout=timeout)
                    return asyncio.run_coroutine_threadsafe(
                        async_func(*args, **kwargs),
                        current_loop
                    ).result()
                else:
                    task = current_loop.create_task(async_func(*args, **kwargs))
                    if timeout:
                        return asyncio.wait_for(task, timeout=timeout)
                    return task

            elif target_loop is not None:
                future = asyncio.run_coroutine_threadsafe(
                    async_func(*args, **kwargs),
                    target_loop
                )
                if wait:
                    return future.result(timeout=timeout)
                return future

            else:
                if timeout:
                    return asyncio.run(asyncio.wait_for(
                        async_func(*args, **kwargs),
                        timeout=timeout
                    ))
                return asyncio.run(async_func(*args, **kwargs))

        return sync_wrapper

    return decorator


def is_caused_by(e: BaseException, target: BaseException | type) -> bool:
    """Проверяет, было ли исключение e вызвано target,
    либо объектом target, либо потомками класса target."""

    # Если передан объект — определяем его класс
    target_type = target if isinstance(target, type) else type(target)

    current = e
    while current is not None:
        # Проверка: это сам объект или экземпляр потомка
        if current is target or isinstance(current, target_type):
            return True
        current = current.__cause__ or current.__context__

    return False


def get_url_path(url):
    return url.split("?")[0]


def compress_str(s: str):
    compressed = zlib.compress(s.encode('utf-8'), level=9)
    return base64.urlsafe_b64encode(compressed).decode('ascii')


def with_empty_method(cls):
    def empty(self):
        for f in dataclasses.fields(self):
            if getattr(self, f.name):
                return False
        return True

    setattr(cls, "empty", empty)
    return cls
