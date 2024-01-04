from src.mybootstrap_ioc_itskovichanton.ioc import bean

from src.mybootstrap_core_itskovichanton.app import Application
from src.mybootstrap_core_itskovichanton.generate import CodeGenerator


@bean
class CodeGeneratorApp(Application):
    code_generator: CodeGenerator

    def run(self):
        self.code_generator.generate()
