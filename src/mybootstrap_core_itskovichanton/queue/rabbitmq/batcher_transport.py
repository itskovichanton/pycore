import pickle

import aio_pika
import asyncio
import json
import random

import pika

from src.mybootstrap_core_itskovichanton.batcher import AbstractTransport, TransportRetry, TransportSlowDown, \
    TransportError


def marshal_json(a):
    return json.dumps(a).encode("utf‑8")


def marshal_pickle(a):
    return pickle.dumps(a)


class RabbitMQTransport(AbstractTransport):
    def __init__(
            self,
            url,
            exchange_name=None,
            queue_name=None,
            persistent=True,
            marshaller=marshal_json,
    ):
        self.url = url
        self.marshaller = marshaller
        self.exchange_name = exchange_name
        self.queue_name = queue_name
        self.persistent = persistent
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()

        if self.persistent:
            await self.channel.set_qos(prefetch_count=100)

        if self.exchange_name:
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
        else:
            self.exchange = None

        if self.queue_name:
            await self.channel.declare_queue(
                self.queue_name,
                durable=True,
            )

    async def send(self, batch):
        if self.connection is None:
            await self.connect()

        body = self.marshaller(batch)

        message = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT if self.persistent else aio_pika.DeliveryMode.NOT_PERSISTENT,
        )

        if self.exchange:
            await self.exchange.publish(message, routing_key=self.queue_name)
            return

        await self.channel.default_exchange.publish(
            message,
            routing_key=self.queue_name,
            # properties=pika.BasicProperties(
            #     delivery_mode=2,  # Make message persistent (optional)
            # )
        )
