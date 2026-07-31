import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Dict, Any, Optional

from jose import jwt
from src.mybootstrap_ioc_itskovichanton.ioc import bean


class JWT(Protocol):
    def generate(self, expiration: datetime, claims: dict) -> str:
        ...

    def decode_jwt(self, token: str, verify_exp: bool = True) -> Dict[str, Any]:
        ...


@dataclass
class _Config:
    secret: str = "secret"
    alg = "HS256"


@bean(cfg=("jwt-generator", _Config, _Config()))
class JWTImpl(JWT):

    def generate(self, expiration: datetime, claims: dict) -> str:
        claims["exp"] = expiration
        return jwt.encode(claims, self.cfg.secret, self.cfg.alg)

    def decode_jwt(self, token: str, verify_exp: bool = True) -> Dict[str, Any]:
        """
        Декодирует JWT токен с проверкой срока действия.

        Args:
            token: JWT токен
            secret_key: Секретный ключ
            verify_exp: Проверять ли срок действия

        Returns:
            Dict[str, Any]: Payload токена

        Raises:
            jwt.ExpiredSignatureError: Если токен просрочен
            jwt.InvalidTokenError: Если токен невалиден
        """
        try:
            # Пытаемся декодировать с проверкой
            payload = jwt.decode(
                token,
                self.cfg.secret,
                algorithms=["HS256", "RS256", "ES256"],
                options={"verify_exp": verify_exp}
            )
            return payload

        except jwt.ExpiredSignatureError:
            # Если токен просрочен, но мы хотим увидеть данные (например, для логирования)
            if not verify_exp:
                # Декодируем без проверки срока
                unverified = jwt.decode(
                    token,
                    self.cfg.secret,
                    algorithms=["HS256", "RS256", "ES256"],
                    options={"verify_exp": False}
                )
                return unverified
            raise


def decode_without_verification(token: str) -> Dict[str, Any]:
    try:
        # Разделяем токен на части
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        # Декодируем payload (вторая часть)
        payload_b64 = parts[1]
        # Добавляем padding если нужно
        payload_b64 += '=' * (4 - len(payload_b64) % 4)

        payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')

        return json.loads(payload_json)

    except Exception as e:
        raise ValueError(f"Failed to decode token without verification: {e}")


def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Извлекает дату истечения токена из payload.
    """
    try:
        payload = decode_without_verification(token)
        exp = payload.get('exp')
        if exp:
            return datetime.fromtimestamp(exp)
        return None
    except:
        return None


def is_token_expired(token: str) -> bool:
    """
    Проверяет, истек ли срок действия токена.

    Args:
        token: JWT токен
    
    Returns:
        bool: True если токен просрочен
    """
    exp = get_token_expiration(token)
    if exp is None:
        return False

    now = datetime.now()
    return now > exp.replace(tzinfo=None)
