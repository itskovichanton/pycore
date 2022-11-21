import asyncio

from app import Application
from di import injector


async def main() -> None:
    app = injector.inject(Application)
    await app.async_run()
    # app.run()


if __name__ == '__main__':
    # main()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
