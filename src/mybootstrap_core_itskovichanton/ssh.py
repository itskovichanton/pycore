import os
import tempfile
from dataclasses import dataclass
from typing import Optional, List

import paramiko


@dataclass
class DownloadFileArgs:
    remote_path: str
    local_path: str = None
    success: bool = False


@dataclass
class SSHConfig:
    login: str
    password: str
    host: str
    port: str
    cwd: str = None
    download_file_args: DownloadFileArgs = None


class SSHClient:
    def __init__(self, config: SSHConfig, working_directory: str = None):
        """
        Инициализация SSH клиента с конфигурацией

        Args:
            config: Конфигурация подключения
            working_directory: Рабочая директория на удаленном сервере (опционально)
        """
        self.config = config
        self.working_directory = working_directory
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None

    def __enter__(self):
        """Контекстный менеджер для автоматического подключения"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер для автоматического отключения"""
        self.disconnect()

    def connect(self) -> None:
        """Установка SSH соединения"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.client.connect(
                hostname=self.config.host,
                port=int(self.config.port),
                username=self.config.login,
                password=self.config.password,
                timeout=10
            )

            # Открываем SFTP сессию для файловых операций
            self.sftp = self.client.open_sftp()

            # Переходим в рабочую директорию, если указана
            if self.working_directory:
                self._change_to_working_directory()

            print(f"Успешное подключение к {self.config.host}:{self.config.port}")

        except Exception as e:
            raise ConnectionError(f"Ошибка подключения SSH: {e}")

    def _change_to_working_directory(self) -> bool:
        """
        Переход в рабочую директорию на удаленном сервере

        Returns:
            True если удалось перейти, False в противном случае
        """
        if not self.client:
            return False

        try:
            # Проверяем существование директории
            try:
                self.sftp.stat(self.working_directory)
            except FileNotFoundError:
                print(f"Предупреждение: Директория {self.working_directory} не существует на сервере")
                return False

            # Переходим в директорию
            result = self.execute_command(f"cd {self.working_directory} && pwd")
            if result['success']:
                print(f"Рабочая директория установлена: {result['stdout'].strip()}")
                return True
            return False

        except Exception as e:
            print(f"Ошибка при переходе в рабочую директорию: {e}")
            return False

    def set_working_directory(self, directory: str) -> bool:
        """
        Установка новой рабочей директории

        Args:
            directory: Путь к новой рабочей директории

        Returns:
            True если удалось установить, False в противном случае
        """
        self.working_directory = directory

        if self.client:
            return self._change_to_working_directory()
        return True  # Директория будет установлена при следующем connect()

    def get_current_working_directory(self) -> Optional[str]:
        """
        Получение текущей рабочей директории на удаленном сервере

        Returns:
            Текущая рабочая директория или None в случае ошибки
        """
        if not self.client:
            return None

        result = self.execute_command("pwd")
        if result['success']:
            return result['stdout'].strip()
        return None

    def _prepare_command_with_working_dir(self, command: str) -> str:
        """
        Подготовка команды с учетом рабочей директории

        Args:
            command: Исходная команда

        Returns:
            Команда с переходом в рабочую директорию (если она установлена)
        """
        if self.working_directory:
            return f"cd {self.working_directory} && {command}"
        return command

    def _prepare_remote_path(self, remote_path: str) -> str:
        """
        Подготовка удаленного пути с учетом рабочей директории

        Args:
            remote_path: Исходный путь

        Returns:
            Абсолютный путь или путь относительно рабочей директории
        """
        if os.path.isabs(remote_path):
            return remote_path
        elif self.working_directory:
            return os.path.join(self.working_directory, remote_path)
        else:
            return remote_path

    def disconnect(self) -> None:
        """Закрытие SSH соединения"""
        if self.sftp:
            self.sftp.close()
            self.sftp = None

        if self.client:
            self.client.close()
            self.client = None

        print("SSH соединение закрыто")

    def execute_command(self, command: str, timeout: int = 30, use_working_dir: bool = True) -> dict:
        """
        Выполнение команды на удаленном сервере

        Args:
            command: Команда для выполнения
            timeout: Таймаут выполнения в секундах
            use_working_dir: Использовать ли рабочую директорию

        Returns:
            Словарь с результатами выполнения:
            {
                'exit_code': код возврата,
                'stdout': стандартный вывод,
                'stderr': вывод ошибок,
                'success': флаг успешности
            }
        """
        if not self.client:
            raise ConnectionError("Нет активного SSH подключения")

        try:
            # Подготавливаем команду с учетом рабочей директории
            prepared_command = command
            if use_working_dir and self.working_directory:
                prepared_command = self._prepare_command_with_working_dir(command)

            stdin, stdout, stderr = self.client.exec_command(prepared_command, timeout=timeout)

            # Чтение результатов
            exit_code = stdout.channel.recv_exit_status()
            stdout_str = stdout.read().decode('utf-8').strip()
            stderr_str = stderr.read().decode('utf-8').strip()

            return {
                'exit_code': exit_code,
                'stdout': stdout_str,
                'stderr': stderr_str,
                'success': exit_code == 0
            }

        except Exception as e:
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }

    def execute_bash_script(self, script_content: str, timeout: int = 60, use_working_dir: bool = True) -> dict:
        """
        Выполнение bash-скрипта на удаленном сервере

        Args:
            script_content: Содержимое bash-скрипта
            timeout: Таймаут выполнения в секундах
            use_working_dir: Использовать ли рабочую директорию

        Returns:
            Словарь с результатами выполнения скрипта
        """
        if not self.client:
            raise ConnectionError("Нет активного SSH подключения")

        try:
            # Создаем временный файл для скрипта
            script_file = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False)
            script_file.write(script_content)
            script_file.close()

            # Загружаем скрипт на сервер
            remote_script_path = f"/tmp/script_{os.getpid()}_{os.path.basename(script_file.name)}"

            try:
                self.upload_file(script_file.name, remote_script_path)

                # Делаем скрипт исполняемым
                self.execute_command(f"chmod +x {remote_script_path}", use_working_dir=False)

                # Выполняем скрипт с учетом рабочей директории
                prepared_command = f"bash {remote_script_path}"
                if use_working_dir and self.working_directory:
                    prepared_command = self._prepare_command_with_working_dir(prepared_command)

                result = self.execute_command(prepared_command, timeout=timeout, use_working_dir=False)

                # Удаляем временный файл скрипта с сервера
                self.execute_command(f"rm -f {remote_script_path}", use_working_dir=False)

                return result

            finally:
                # Удаляем локальный временный файл
                os.unlink(script_file.name)

        except Exception as e:
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }

    def download_file(self, remote_path: str, local_path: str, use_working_dir: bool = True) -> bool:
        """
        Скачивание файла с удаленного сервера

        Args:
            remote_path: Путь к файлу на удаленном сервере
            local_path: Путь для сохранения файла локально
            use_working_dir: Использовать ли рабочую директорию для remote_path

        Returns:
            True если файл успешно скачан, False в противном случае
        """
        if not self.sftp:
            raise ConnectionError("Нет активной SFTP сессии")

        try:
            # Подготавливаем удаленный путь с учетом рабочей директории
            prepared_remote_path = remote_path
            if use_working_dir and not os.path.isabs(remote_path) and self.working_directory:
                prepared_remote_path = self._prepare_remote_path(remote_path)

            # Создаем директорию для локального файла, если ее нет
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)

            self.sftp.get(prepared_remote_path, local_path)
            print(f"Файл скачан: {prepared_remote_path} -> {local_path}")
            return True

        except Exception as e:
            print(f"Ошибка при скачивании файла {remote_path}: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str, use_working_dir: bool = True) -> bool:
        """
        Загрузка файла на удаленный сервер

        Args:
            local_path: Путь к локальному файлу
            remote_path: Путь для сохранения файла на удаленном сервере
            use_working_dir: Использовать ли рабочую директорию для remote_path

        Returns:
            True если файл успешно загружен, False в противном случае
        """
        if not self.sftp:
            raise ConnectionError("Нет активной SFTP сессии")

        try:
            # Подготавливаем удаленный путь с учетом рабочей директории
            prepared_remote_path = remote_path
            if use_working_dir and not os.path.isabs(remote_path) and self.working_directory:
                prepared_remote_path = self._prepare_remote_path(remote_path)

            # Проверяем существование локального файла
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Локальный файл не найден: {local_path}")

            # Создаем директорию на удаленном сервере, если ее нет
            remote_dir = os.path.dirname(prepared_remote_path)
            if remote_dir:
                self._ensure_remote_directory(remote_dir)

            self.sftp.put(local_path, prepared_remote_path)
            print(f"Файл загружен: {local_path} -> {prepared_remote_path}")
            return True

        except Exception as e:
            print(f"Ошибка при загрузке файла {local_path}: {e}")
            return False

    def _ensure_remote_directory(self, remote_dir: str) -> None:
        """
        Создание директории на удаленном сервере, если ее нет

        Args:
            remote_dir: Путь к директории на удаленном сервере
        """
        if not self.sftp:
            return

        try:
            self.sftp.stat(remote_dir)
        except FileNotFoundError:
            # Рекурсивно создаем родительские директории
            parent_dir = os.path.dirname(remote_dir)
            if parent_dir:
                self._ensure_remote_directory(parent_dir)

            self.sftp.mkdir(remote_dir)

    def execute_multiple_commands(self, commands: List[str], use_working_dir: bool = True) -> List[dict]:
        """
        Выполнение нескольких команд за одно подключение

        Args:
            commands: Список команд для выполнения
            use_working_dir: Использовать ли рабочую директорию

        Returns:
            Список результатов выполнения для каждой команды
        """
        results = []
        for command in commands:
            print(f"Выполнение команды: {command}")
            result = self.execute_command(command, use_working_dir=use_working_dir)
            results.append(result)

            if not result['success']:
                print(f"Команда завершилась с ошибкой: {result['stderr']}")

        return results

    def batch_file_operations(self, downloads: List[tuple] = None, uploads: List[tuple] = None,
                              use_working_dir: bool = True) -> dict:
        """
        Выполнение нескольких файловых операций за одно подключение

        Args:
            downloads: Список кортежей (remote_path, local_path) для скачивания
            uploads: Список кортежей (local_path, remote_path) для загрузки
            use_working_dir: Использовать ли рабочую директорию для удаленных путей

        Returns:
            Словарь с результатами операций
        """
        results = {
            'downloads': {},
            'uploads': {}
        }

        if downloads:
            for remote_path, local_path in downloads:
                success = self.download_file(remote_path, local_path, use_working_dir=use_working_dir)
                results['downloads'][remote_path] = {
                    'local_path': local_path,
                    'success': success
                }

        if uploads:
            for local_path, remote_path in uploads:
                success = self.upload_file(local_path, remote_path, use_working_dir=use_working_dir)
                results['uploads'][local_path] = {
                    'remote_path': remote_path,
                    'success': success
                }

        return results

    def list_directory(self, remote_path: str = None, use_working_dir: bool = True) -> List[str]:
        """
        Список файлов в директории на удаленном сервере

        Args:
            remote_path: Путь к директории (None для текущей рабочей директории)
            use_working_dir: Использовать ли рабочую директорию

        Returns:
            Список файлов и директорий
        """
        if not self.sftp:
            raise ConnectionError("Нет активной SFTP сессии")

        try:
            # Определяем путь для листинга
            if remote_path is None:
                target_path = self.working_directory if use_working_dir and self.working_directory else "."
            else:
                target_path = remote_path
                if use_working_dir and not os.path.isabs(remote_path) and self.working_directory:
                    target_path = self._prepare_remote_path(remote_path)

            return self.sftp.listdir(target_path)

        except Exception as e:
            print(f"Ошибка при получении списка файлов в {remote_path}: {e}")
            return []


# Пример использования
if __name__ == "__main__":
    # Создаем конфигурацию
    config = SSHConfig(
        login="username",
        password="password",
        host="192.168.1.100",
        port="22"
    )

    # 1. Использование с рабочей директорией
    print("=== Пример с рабочей директорией ===")
    with SSHClient(config, working_directory="/home/user/project") as ssh:
        # Команды выполняются в рабочей директории
        result = ssh.execute_command("pwd")
        print(f"Текущая директория: {result['stdout']}")

        # Скачивание файла относительно рабочей директории
        ssh.download_file("config.txt", "./local_config.txt")

        # Загрузка файла в рабочую директорию
        ssh.upload_file("./local_file.txt", "uploaded_file.txt")

        # Смена рабочей директории во время сессии
        ssh.set_working_directory("/tmp")
        result = ssh.execute_command("pwd")
        print(f"Новая рабочая директория: {result['stdout']}")

    print("\n=== Пример выполнения bash-скрипта ===")

    # 2. Выполнение bash-скрипта
    with SSHClient(config) as ssh:
        # Простой скрипт
        simple_script = """#!/bin/bash
echo "Начало выполнения скрипта"
echo "Текущая директория: $(pwd)"
echo "Список файлов:"
ls -la
echo "Завершение скрипта"
"""

        result = ssh.execute_bash_script(simple_script)
        print(f"Скрипт выполнен: {result['success']}")
        print(f"Вывод скрипта:\n{result['stdout']}")

        # Более сложный скрипт с параметрами
        advanced_script = """#!/bin/bash
# Создаем несколько файлов
for i in {1..3}; do
    echo "Файл номер $i" > file_$i.txt
done

# Проверяем создание
echo "Созданные файлы:"
ls *.txt

# Создаем директорию
mkdir -p test_dir
echo "Директория test_dir создана"
"""

        result = ssh.execute_bash_script(advanced_script, timeout=30)
        print(f"\nПродвинутый скрипт выполнен: {result['success']}")

        if result['stderr']:
            print(f"Ошибки: {result['stderr']}")

    print("\n=== Комбинированный пример ===")

    # 3. Комбинированный пример
    with SSHClient(config, working_directory="/tmp") as ssh:
        # Выполняем несколько команд
        commands = [
            "whoami",
            "pwd",
            "echo 'Тестовая команда'",
            "mkdir -p test_folder"
        ]

        results = ssh.execute_multiple_commands(commands)
        for i, result in enumerate(results):
            print(f"Команда {i + 1}: {result['stdout']}")

        # Bash-скрипт, который создает файл в рабочей директории
        create_file_script = """#!/bin/bash
echo "Создаем тестовый файл в рабочей директории"
echo "Содержимое файла" > test_script_output.txt
echo "Файл создан:"
ls -la test_script_output.txt
cat test_script_output.txt
"""

        result = ssh.execute_bash_script(create_file_script)
        print(f"\nРезультат выполнения скрипта: {result['success']}")

        # Скачиваем созданный файл
        ssh.download_file("test_script_output.txt", "./downloaded_script_output.txt")

        # Пакетные операции
        batch_results = ssh.batch_file_operations(
            downloads=[
                ("test_script_output.txt", "./batch_download_1.txt"),
                ("/etc/hosts", "./batch_download_2.txt")
            ],
            uploads=[
                ("./local_file_1.txt", "uploaded_1.txt"),
                ("./local_file_2.txt", "uploaded_2.txt")
            ]
        )

        print(f"\nПакетные операции завершены")
