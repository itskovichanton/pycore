import pickle

import pika
import json
import time
import logging
import threading
from typing import Generator, Optional, Dict, Any, Callable
from queue import Queue
from dataclasses import dataclass
from enum import Enum
import signal
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BatchEntry:
    entries: list[dict]
    meta: dict


class ConnectionState(Enum):
    """Состояния соединения"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class ConnectionConfig:
    """Конфигурация соединения"""
    host: str = 'localhost'
    port: int = 5672
    username: str = 'guest'
    password: str = 'guest'
    virtual_host: str = '/'
    heartbeat: int = 600
    blocked_connection_timeout: int = 300
    connection_attempts: int = 3
    retry_delay: int = 5
    prefetch_count: int = 10


def unmarshal_json(a):
    return json.loads(a)


def unmarshal_pickle(a):
    return pickle.loads(a)


class RabbitMQConsumer:
    """
    Надежный потребитель RabbitMQ с автоматическим реконнектом и стабильным стримингом.

    Особенности:
    - Автоматическое восстановление соединения при разрывах
    - Graceful shutdown при получении сигналов
    - Поддержка heartbeats для поддержания соединения
    - Потокобезопасный
    - Подробное логирование
    - Возможность настройки повторных попыток

    Пример использования:
        consumer = RabbitMQConsumer()
        for message in consumer.stream('my_queue'):
            print(f"Received: {message}")
            # Обработка сообщения
    """

    def __init__(
            self,
            host: str = 'localhost',
            port: int = 5672,
            username: str = 'guest',
            password: str = 'guest',
            virtual_host: str = '/',
            heartbeat: int = 600,
            prefetch_count: int = 10,
            reconnect_delay: int = 5,
            unmarshaller=unmarshal_json,
            max_reconnect_attempts: int = -1,  # -1 = бесконечно
    ):
        """
        Инициализация потребителя RabbitMQ

        Args:
            host: Хост RabbitMQ
            port: Порт RabbitMQ
            username: Имя пользователя
            password: Пароль
            virtual_host: Виртуальный хост
            heartbeat: Интервал heartbeat в секундах
            prefetch_count: Количество сообщений для предварительной выборки
            reconnect_delay: Задержка между попытками переподключения (секунды)
            max_reconnect_attempts: Максимальное количество попыток переподключения
        """
        self.config = ConnectionConfig(
            host=host,
            port=port,
            username=username,
            password=password,
            virtual_host=virtual_host,
            heartbeat=heartbeat,
            prefetch_count=prefetch_count
        )

        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self._unmarshaller = unmarshaller
        self._state = ConnectionState.DISCONNECTED
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._reconnect_attempts = 0

        # Для потока восстановления соединения
        self._reconnect_thread = None
        self._message_queue = Queue(maxsize=1000)

        # Текущее соединение и канал
        self._connection = None
        self._channel = None
        self._consumer_tag = None

        # Обработка сигналов для graceful shutdown
        self._setup_signal_handlers()

        logger.info(f"RabbitMQConsumer initialized for {host}:{port}")

    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.close()
        sys.exit(0)

    def _set_state(self, state: ConnectionState):
        """Безопасное изменение состояния"""
        with self._state_lock:
            old_state = self._state
            self._state = state
            logger.debug(f"State changed: {old_state.value} -> {state.value}")

    def _get_connection_params(self) -> pika.ConnectionParameters:
        """Создание параметров соединения"""
        credentials = pika.PlainCredentials(
            self.config.username,
            self.config.password
        )

        return pika.ConnectionParameters(
            host=self.config.host,
            port=self.config.port,
            virtual_host=self.config.virtual_host,
            credentials=credentials,
            heartbeat=self.config.heartbeat,
            blocked_connection_timeout=self.config.blocked_connection_timeout,
            connection_attempts=self.config.connection_attempts,
            retry_delay=self.config.retry_delay,
            socket_timeout=10
        )

    def _connect(self) -> bool:
        """
        Установка соединения с RabbitMQ

        Returns:
            bool: True если соединение успешно, False в противном случае
        """
        self._set_state(ConnectionState.CONNECTING)

        try:
            logger.info(f"Connecting to RabbitMQ at {self.config.host}:{self.config.port}...")

            params = self._get_connection_params()
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()

            # Настройка QoS
            self._channel.basic_qos(prefetch_count=self.config.prefetch_count)

            # Добавляем обработчики ошибок соединения
            self._connection.add_on_connection_blocked_callback(self._on_connection_blocked)
            self._connection.add_on_connection_unblocked_callback(self._on_connection_unblocked)

            self._set_state(ConnectionState.CONNECTED)
            self._reconnect_attempts = 0  # Сброс счетчика попыток

            logger.info("Successfully connected to RabbitMQ")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self._set_state(ConnectionState.DISCONNECTED)
            return False

    def _on_connection_blocked(self, method_frame):
        """Обработчик блокировки соединения"""
        logger.warning("Connection blocked: %s", method_frame.method.reason)

    def _on_connection_unblocked(self, method_frame):
        """Обработчик разблокировки соединения"""
        logger.info("Connection unblocked")

    def _on_connection_close(self, connection, reason):
        """Обработчик закрытия соединения"""
        logger.warning(f"Connection closed: {reason}")
        self._set_state(ConnectionState.DISCONNECTED)

        if not self._stop_event.is_set():
            self._start_reconnect()

    def _on_channel_close(self, channel, reason):
        """Обработчик закрытия канала"""
        logger.warning(f"Channel closed: {reason}")

        if not self._stop_event.is_set():
            self._reconnect()

    def _reconnect(self):
        """Переподключение к RabbitMQ"""
        if self._stop_event.is_set():
            return

        self._set_state(ConnectionState.RECONNECTING)

        # Проверяем лимит попыток переподключения
        if (self.max_reconnect_attempts > 0 and
                self._reconnect_attempts >= self.max_reconnect_attempts):
            logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) exceeded")
            self.close()
            return

        self._reconnect_attempts += 1
        delay = self.reconnect_delay

        # Exponential backoff
        if self._reconnect_attempts > 1:
            delay = min(delay * 1.5, 60)  # Максимум 60 секунд

        logger.info(f"Attempting to reconnect (attempt {self._reconnect_attempts}) in {delay}s...")

        # Закрываем старое соединение если оно есть
        self._cleanup_connection()

        # Ждем перед попыткой переподключения
        time.sleep(delay)

        # Пытаемся подключиться
        if self._connect():
            logger.info("Reconnection successful")
        else:
            # Рекурсивно пытаемся снова
            self._reconnect()

    def _start_reconnect(self):
        """Запуск потока переподключения"""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        self._reconnect_thread = threading.Thread(
            target=self._reconnect,
            name="RabbitMQ-Reconnect-Thread",
            daemon=True
        )
        self._reconnect_thread.start()

    def _cleanup_connection(self):
        """Очистка соединения и канала"""
        try:
            if self._channel and self._channel.is_open:
                self._channel.close()
        except:
            pass

        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
        except:
            pass

        self._channel = None
        self._connection = None
        self._consumer_tag = None

    def _consume_queue(self, queue_name: str, durable: bool = True):
        """
        Начать потребление из очереди

        Args:
            queue_name: Имя очереди
            durable: Создавать ли durable очередь
        """
        try:
            # Объявляем очередь
            self._channel.queue_declare(
                queue=queue_name,
                durable=durable,
                # arguments={
                #     'x-max-length': 10000,
                #     'x-message-ttl': 3600000,  # 1 час
                #     'x-overflow': 'reject-publish'
                # }
            )

            # Начинаем потребление
            self._consumer_tag = self._channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._on_message_received,
                auto_ack=False,
                exclusive=False,
                consumer_tag=None
            )

            logger.info(f"Started consuming from queue '{queue_name}'")

            # Начинаем обработку сообщений
            self._channel.start_consuming()

        except Exception as e:
            logger.error(f"Error while consuming from queue '{queue_name}': {e}")
            raise

    def _on_message_received(self, channel, method, properties, body):
        """
        Обработчик получения сообщения

        Args:
            channel: Канал
            method: Метод доставки
            properties: Свойства сообщения
            body: Тело сообщения
        """
        try:
            message = BatchEntry(
                entries=self._unmarshaller(body),
                meta={
                    'delivery_tag': method.delivery_tag,
                    'exchange': method.exchange,
                    'routing_key': method.routing_key,
                    'redelivered': method.redelivered,
                    'timestamp': time.time()
                },
            )

            # Кладем сообщение в очередь для yield
            self._message_queue.put(message)

            # Автоматически подтверждаем получение
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON message: {body[:100]}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def stream(
            self,
            queue_name: str,
            durable: bool = True,
            yield_timeout: float = 0.1
    ) -> Generator[BatchEntry, None, None]:
        """
        Бесконечный генератор сообщений из RabbitMQ

        Args:
            queue_name: Имя очереди
            durable: Создавать ли durable очередь
            yield_timeout: Таймаут ожидания сообщения для yield

        Yields:
            dict: Сообщение из очереди

        Raises:
            RuntimeError: Если потребитель остановлен

        Example:
            consumer = RabbitMQConsumer()
            for message in consumer.stream('my_queue'):
                print(f"Received: {message}")
        """
        if self._stop_event.is_set():
            raise RuntimeError("Consumer is stopped")

        logger.info(f"Starting stream from queue '{queue_name}'")

        # Пытаемся подключиться
        if not self._connect():
            raise ConnectionError("Failed to connect to RabbitMQ")

        # Запускаем потребление в отдельном потоке
        consume_thread = threading.Thread(
            target=self._consume_queue,
            args=(queue_name, durable),
            name=f"RabbitMQ-Consume-{queue_name}",
            daemon=True
        )
        consume_thread.start()

        # Даем время на запуск потребления
        time.sleep(0.5)

        try:
            # Бесконечный цикл yield сообщений
            while not self._stop_event.is_set():
                try:
                    # Получаем сообщение из очереди с таймаутом
                    message = self._message_queue.get(block=True, timeout=yield_timeout)
                    yield message

                except Exception as ex:
                    # Проверяем состояние соединения
                    with self._state_lock:
                        if self._state != ConnectionState.CONNECTED:
                            logger.warning(f"Connection state is {self._state.value}, waiting for recovery...")
                            time.sleep(1)
                            continue

                    # Если очередь пуста, просто продолжаем цикл
                    time.sleep(0.5)
                    continue

        except GeneratorExit:
            logger.info(f"Stream generator for queue '{queue_name}' was closed")
        except KeyboardInterrupt:
            logger.info("Stream interrupted by user")
        except Exception as e:
            logger.error(f"Error in stream: {e}")
            raise
        finally:
            # Останавливаем потребление
            self._stop_consuming()
            consume_thread.join(timeout=5)

    def _stop_consuming(self):
        """Остановка потребления сообщений"""
        try:
            if self._channel and self._channel.is_open and self._consumer_tag:
                self._channel.basic_cancel(self._consumer_tag)
                logger.info("Stopped consuming messages")
        except Exception as e:
            logger.error(f"Error stopping consumption: {e}")

    def close(self):
        """
        Graceful shutdown потребителя

        Закрывает все соединения и останавливает все потоки
        """
        if self._stop_event.is_set():
            return

        logger.info("Closing RabbitMQ consumer...")
        self._stop_event.set()
        self._set_state(ConnectionState.SHUTTING_DOWN)

        # Останавливаем потребление
        self._stop_consuming()

        # Очищаем соединения
        self._cleanup_connection()

        logger.info("RabbitMQ consumer closed")

    def __enter__(self):
        """Контекстный менеджер"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие при выходе из контекста"""
        self.close()

    @property
    def is_connected(self) -> bool:
        """Проверка подключения"""
        with self._state_lock:
            return self._state == ConnectionState.CONNECTED

    @property
    def state(self) -> ConnectionState:
        """Текущее состояние соединения"""
        with self._state_lock:
            return self._state
