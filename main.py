from opyoid import Injector

from app import Application
from di import CoreModule


def main() -> None:
    injector = Injector([CoreModule])
    app1 = injector.inject(Application)
    app1.run()


if __name__ == '__main__':
    main()
