import asyncio
import os
os.putenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
from app import TestCoreApp
from src.mybootstrap_core_itskovichanton.di import injector


def main() -> None:

    app = injector().inject(TestCoreApp)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run()
    # try:
    #     asyncio.run(app.run())
    # except KeyboardInterrupt:
    #     pass


if __name__ == '__main__':
    main()

