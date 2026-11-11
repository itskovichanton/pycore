"""Потокобезопасная ссылка (аналог Java AtomicReference)."""
import threading


class AtomicReference:
    """Хранит одно значение; ``compare_and_set`` меняет его только если совпал expected."""
    def __init__(self, initial_value=None):
        self._value = initial_value
        self._lock = threading.Lock()

    def get(self):
        """Текущее значение."""
        with self._lock:
            return self._value

    def set(self, new_value):
        """Записать значение."""
        with self._lock:
            self._value = new_value

    def compare_and_set(self, expected_value, new_value):
        """CAS: True, если было expected и стало new_value."""
        with self._lock:
            if self._value == expected_value:
                self._value = new_value
                return True
            return False
