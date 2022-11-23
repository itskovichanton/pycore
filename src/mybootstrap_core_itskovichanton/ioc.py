import functools
from dataclasses import dataclass
from typing import Type, Optional, Any

from benedict import benedict
from opyoid import Injector, SingletonScope, Module
from opyoid.scopes import Scope

from src.mybootstrap_core_itskovichanton.utils import infer_from_tuple, omittable_parentheses

settings: benedict
profile: str
config_service: None


@dataclass
class _beanPrefs:
    scope: Type[Scope] = SingletonScope,
    named: Optional[str] = None
    no_polymorph: bool = False
    to_class: Any = None


beans: dict[Any, list[_beanPrefs]] = {}


def _create_bean_init(method, **kwargs):
    @functools.wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        r = method(self, *method_args, **method_kwargs)
        for k, v in kwargs.items():
            v = infer_from_tuple(settings, v)
            kwargs[k] = v
            setattr(self, k, v)

        if hasattr(self, 'init') and callable(self.init):
            self.init(**kwargs)
        return r

    return _impl


@omittable_parentheses(allow_partial=True)
def bean(scope: Type[Scope] = None, named: Optional[str] = None, no_polymorph: bool = False, **kwargs):
    def discover(cl):
        print(f"Bean discovered: {cl}")
        if cl and hasattr(cl, "__bases__"):
            cl = dataclass(cl)
            prefs = _beanPrefs(to_class=cl, scope=scope, named=named, no_polymorph=no_polymorph)
            for base in cl.__bases__:
                beans.setdefault(base, []).append(prefs)
            cl.__init__ = _create_bean_init(cl.__init__, **kwargs)
        return cl

    return discover


class BaseModule(Module):

    def configure(self) -> None:
        self.bind(Injector, to_instance=Injector([self]))
        for target_type, beanList in beans.items():
            for prefs in beanList:
                if prefs.no_polymorph:
                    target_type = prefs.to_class
                print(f"binding {target_type} --> {prefs.to_class}")
                self.bind(target_type, to_class=prefs.to_class, named=prefs.named)
                print("bound")
