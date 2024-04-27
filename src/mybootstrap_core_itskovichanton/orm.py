import inspect
import typing
from dataclasses import dataclass
from typing import Type, List, Set, Any, Tuple

from peewee import *
from peewee import ModelSelect


@dataclass
class _Mapping:
    to: Type
    attrs: dict[str, str]
    model_class_db_fields: Any = None

    def init(self):
        if self.model_class_db_fields is None:
            self.model_class_db_fields = inspect.getmembers(self.to, lambda a: not (inspect.isroutine(a)))
            self.model_class_db_fields = {a[0]: a[1] for a in self.model_class_db_fields if
                                          not (a[0].startswith('__') and a[0].endswith('__'))}


_MAPPING: dict[Type, _Mapping] = {}


def entity(real_entity, attr_mapping: dict[str, str] = None):
    def decorator(cls):
        _MAPPING[real_entity] = _Mapping(to=cls, attrs=attr_mapping)
        _MAPPING[cls] = _Mapping(to=real_entity, attrs=attr_mapping)
        return cls

    return decorator


def to_model(a):
    model_class_mapping = _MAPPING.get(type(a))
    if model_class_mapping:
        model_class_mapping.init()
        r = model_class_mapping.to()
        for filter_field in vars(a):
            filter_model_field = filter_field
            if model_class_mapping.attrs and filter_field in model_class_mapping.attrs:
                filter_model_field = model_class_mapping.attrs.get(filter_field)
            setattr(r, filter_field, getattr(a, filter_model_field, None))
    else:
        r = a
    return r


def infer_where(filter, model_class_field_db_field: Field = None):
    where = []

    if filter is not None:
        model_class_mapping = _MAPPING.get(type(filter))
        if model_class_mapping:
            model_class_mapping.init()
            for filter_field in vars(filter):
                filter_field_value = getattr(filter, filter_field)
                if filter_field_value is not None:
                    if model_class_mapping.attrs and filter_field in model_class_mapping.attrs:
                        filter_field = model_class_mapping.attrs.get(filter_field)
                    model_class_field_db_field = model_class_mapping.model_class_db_fields.get(filter_field)
                    where += infer_where(filter_field_value, model_class_field_db_field)
        else:
            if model_class_field_db_field:
                where += [model_class_field_db_field == filter]
    if not where:
        where = [1 == 1]
    return where


def convert_to_real_entity(a):
    if a is None:
        return

    if isinstance(a, List):
        return [convert_to_real_entity(x) for x in a]
    elif isinstance(a, Set):
        return {convert_to_real_entity(x) for x in a}
    elif isinstance(a, typing.Tuple):
        return (convert_to_real_entity(x) for x in a)

    to_class = _MAPPING.get(type(a))
    if to_class is None:
        return a

    r = to_class.to()
    attrs = dict(vars(a))
    try:
        data = dict(a.__data__)
        data.update({k: v for k, v in attrs.items() if not k.startswith("_")})
        for p in inspect.getmembers(type(a), lambda x:not(inspect.isroutine(x))):
            if not p[0].startswith("_"):
                getattr(a, p[0], None)
        data.update(vars(a).get("__rel__") or {})
        for a_field, a_value in data.items():
            setattr(r, a_field, convert_to_real_entity(a_value))
    except:
        a_fields = attrs

    return r


def to_real_entity(func, to_dict_with_key=None):
    def wrapper(*args, **kwargs):
        r = func(*args, **kwargs)
        if not r:
            return
        if isinstance(r, Model):
            return convert_to_real_entity(r)
        if isinstance(r, ModelSelect):
            r = [x for x in r]
        if isinstance(r, List):
            r = [convert_to_real_entity(x) for x in r]
        elif isinstance(r, Set):
            r = {convert_to_real_entity(x) for x in r}
        elif isinstance(r, typing.Tuple):
            r = (convert_to_real_entity(x) for x in r)
        else:
            return convert_to_real_entity(r)

        if to_dict_with_key:
            r = {getattr(x, to_dict_with_key): x for x in r}

        return r

    return wrapper
