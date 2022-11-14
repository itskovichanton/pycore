from app import Application


class TestCoreApplication(Application):
    def run(self):
        print("ELLO!!")
        print(self.config_service.app_name())


print("Hello")
