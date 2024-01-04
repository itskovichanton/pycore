import asyncio
from app import TestCoreApp
from src.mybootstrap_core_itskovichanton.di import injector
from app_generate import CodeGeneratorApp


def main() -> None:
    app = injector().inject(CodeGeneratorApp)
    app.run()


if __name__ == '__main__':
    main()

