from app import TestCoreApp
from di import injector


def main() -> None:
    app = injector.inject(TestCoreApp)
    # await app._run()
    app.run()


if __name__ == '__main__':
    main()
# loop = io.new_event_loop()
# io.set_event_loop(loop)
# try:
#     io.run(main())
# except KeyboardInterrupt:
#     pass
