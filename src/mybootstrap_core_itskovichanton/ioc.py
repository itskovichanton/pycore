import functools
from dataclasses import dataclass
from typing import Type, Optional, Any

from opyoid import Injector, SingletonScope, Module
from opyoid.scopes import Scope

from src.mybootstrap_core_itskovichanton.env import get_env_props
from src.mybootstrap_core_itskovichanton.utils import infer_from_tuple, omittable_parentheses


@dataclass
class Context:
    properties = get_env_props()
    profile = properties.get("profile", default="dev")


context = Context()


@dataclass
class _Bean:
    scope: Type[Scope] = SingletonScope,
    no_polymorph: bool = False
    to_class: Any = None
    profile: str = None
    # bound: bool = False


_beans: dict[Any, list[_Bean]] = {}


def _create_bean_init(method, prefs: _Bean, **kwargs):
    @functools.wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        r = method(self, *method_args, **method_kwargs)
        # from here we have a bean created
        print("BEAN_CREATED ", self, "hex=", hex(id(self)), ", bean=", prefs)
        setattr(self, "_context", context)
        for k, v in kwargs.items():
            v = infer_from_tuple(context.properties, v)
            kwargs[k] = v
            setattr(self, k, v)

        if hasattr(self, 'init') and callable(self.init):
            self.init(**kwargs)

        return r

    return _impl


@omittable_parentheses(allow_partial=True)
def bean(scope: Type[Scope] = None,
         named: Optional[str] = None,
         no_polymorph: bool = False,
         profile: str = None,
         **kwargs):
    def discover(cl):
        print(f"Bean discovered: {cl.__name__}")
        if cl and hasattr(cl, "__bases__"):
            cl = dataclass(cl)
            prefs = _Bean(to_class=cl, scope=scope, no_polymorph=no_polymorph, profile=profile)
            for base in cl.__bases__:
                _beans.setdefault(base, []).append(prefs)
            cl.__init__ = _create_bean_init(cl.__init__, prefs, **kwargs)
        return cl

    return discover


class BaseModule(Module):

    def configure(self) -> None:
        self.bind(Injector, to_instance=Injector([self]))
        for target_type, beanList in _beans.items():
            for prefs in beanList:
                if prefs.profile is None or prefs.profile == context.profile:
                    if prefs.no_polymorph:
                        target_type = prefs.to_class
                    print(f"binding {target_type.__name__} --> {prefs.to_class.__name__}")
                    self.bind(target_type, to_class=prefs.to_class)
                    prefs.bound = True
                    print("bound")
