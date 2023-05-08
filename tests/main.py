import asyncio
from app import TestCoreApp
from src.mybootstrap_core_itskovichanton.di import injector


def main() -> None:
    app = injector().inject(TestCoreApp)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

