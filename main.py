import asyncio

from opyoid import Injector

from app import Application
from di import CoreModule


async def main() -> None:

    injector = Injector([CoreModule])
    app = injector.inject(Application)

    await app.run()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
