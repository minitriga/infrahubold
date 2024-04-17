from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Awaitable, Callable, List, MutableMapping, Optional, Type, TypeVar

import nats
import ujson
from infrahub_sdk import UUIDT
from opentelemetry import context, propagate, trace
from opentelemetry.instrumentation.utils import is_instrumentation_enabled

from infrahub import config
from infrahub.components import ComponentType
from infrahub.log import clear_log_context, get_log_data
from infrahub.message_bus import InfrahubMessage, Meta, messages
from infrahub.message_bus.operations import execute_message
from infrahub.services.adapters.message_bus import InfrahubMessageBus
from infrahub.worker import WORKER_IDENTITY

if TYPE_CHECKING:
    from infrahub.config import BrokerSettings
    from infrahub.message_bus.types import MessageTTL
    from infrahub.services import InfrahubServices

MessageFunction = Callable[[InfrahubMessage], Awaitable[None]]
ResponseClass = TypeVar("ResponseClass")


async def _add_request_id(message: InfrahubMessage) -> None:
    log_data = get_log_data()
    message.meta.request_id = log_data.get("request_id", "")


class NATSMessageBus(InfrahubMessageBus):
    def __init__(self, settings: Optional[BrokerSettings] = None) -> None:
        self.settings = settings or config.SETTINGS.broker

        self.service: InfrahubServices
        self.connection: nats.NATS
        self.jetstream: nats.js.JetStreamContext
        self.callback_queue: nats.js.api.StreamInfo
        self.events_queue: nats.js.api.StreamInfo
        self.message_enrichers: List[MessageFunction] = []

        self.loop = asyncio.get_running_loop()
        self.futures: MutableMapping[str, asyncio.Future] = {}

    async def initialize(self, service: InfrahubServices) -> None:
        self.service = service
        self.connection = await nats.connect(
            f"nats://{self.settings.address}:{self.settings.service_port}",
            user=self.settings.username,
            password=self.settings.password,
        )

        self.jetstream = self.connection.jetstream()

        ####
        if self.service.component_type == ComponentType.API_SERVER:
            await self._initialize_api_server()
        elif self.service.component_type == ComponentType.GIT_AGENT:
            await self._initialize_git_worker()

    async def shutdown(self) -> None:
        await self.connection.drain()

    async def on_callback(self, message: nats.aio.msg.Msg) -> None:
        if is_instrumentation_enabled():
            ctx = propagate.extract(message.headers)
            token = context.attach(ctx)

        try:
            with trace.get_tracer(__name__).start_as_current_span("on_callback") as span:
                span.set_attribute("routing_key", message.subject)

                if message.headers and "correlation_id" in message.headers:
                    future: asyncio.Future = self.futures.pop(message.headers["correlation_id"])

                    if future:
                        future.set_result(message)
                        return

                clear_log_context()
                if message.subject in messages.MESSAGE_MAP:
                    await execute_message(routing_key=message.subject, message_body=message.data, service=self.service)
                else:
                    self.service.log.error("Invalid message received", message=f"{message!r}")
        finally:
            if is_instrumentation_enabled():
                context.detach(token)

    async def on_message(self, message: nats.aio.msg.Msg) -> None:
        if is_instrumentation_enabled():
            ctx = propagate.extract(message.headers)
            token = context.attach(ctx)

        try:
            with trace.get_tracer(__name__).start_as_current_span("on_message") as span:
                span.set_attribute("routing_key", message.subject)

                clear_log_context()
                if message.subject in messages.MESSAGE_MAP:
                    delay = await execute_message(
                        routing_key=message.subject, message_body=message.data, service=self.service
                    )
                    if delay:
                        return await message.nak(delay / 1000)
                else:
                    self.service.log.error("Invalid message received", message=f"{message!r}")

                return await message.ack()
        finally:
            if is_instrumentation_enabled():
                context.detach(token)

    async def _subscribe_events(self, events: List[str], identity: str) -> None:
        for subject in events:
            await self.jetstream.subscribe(
                subject=subject,
                stream=f"{self.settings.namespace}-events",
                config=nats.js.api.ConsumerConfig(ack_policy=nats.js.api.AckPolicy.NONE, description=identity),
                cb=self.on_callback,
            )

    async def _setup_callback(self, identity: str) -> None:
        self.callback_queue = await self.jetstream.add_stream(
            name=f"{self.settings.namespace}-callback-{WORKER_IDENTITY}",
            retention=nats.js.api.RetentionPolicy.LIMITS,
        )

        await self.jetstream.subscribe(
            subject="*",
            stream=f"{self.settings.namespace}-callback-{WORKER_IDENTITY}",
            cb=self.on_callback,
            config=nats.js.api.ConsumerConfig(ack_policy=nats.js.api.AckPolicy.NONE, description=identity),
        )

    async def _initialize_api_server(self) -> None:
        self.events_queue = await self.jetstream.add_stream(
            name=f"{self.settings.namespace}-events",
            subjects=["refresh.registry.*"],
            retention=nats.js.api.RetentionPolicy.INTEREST,
        )

        worker_bindings = [
            "check.*.*",
            "event.*.*",
            "finalize.*.*",
            "git.*.*",
            "refresh.webhook.*",
            "request.*.*",
            "send.*.*",
            "schema.*.*",
            "transform.*.*",
            "trigger.*.*",
        ]

        await self.jetstream.add_stream(
            name=f"{self.settings.namespace}-rpcs",
            subjects=worker_bindings,
            retention=nats.js.api.RetentionPolicy.WORK_QUEUE,
        )

        await self._subscribe_events(["refresh.registry.*"], f"api-worker-{WORKER_IDENTITY}")

        await self._setup_callback(f"api-worker-{WORKER_IDENTITY}")

        self.message_enrichers.append(_add_request_id)

    async def _initialize_git_worker(self) -> None:
        await self._subscribe_events(["refresh.registry.*"], f"git-worker-{WORKER_IDENTITY}")

        worker_bindings = [
            "check.*.*",
            "event.*.*",
            "finalize.*.*",
            "git.*.*",
            "refresh.webhook.*",
            "request.*.*",
            "send.*.*",
            "schema.*.*",
            "transform.*.*",
            "trigger.*.*",
        ]

        consumer_config = nats.js.api.ConsumerConfig(
            ack_policy=nats.js.api.AckPolicy.EXPLICIT,
            max_deliver=self.settings.maximum_message_retries,
            # Does not work as expected, must switch to pull-based consumer...
            # max_ack_pending=self.settings.maximum_concurrent_messages,
            # flow_control=True,
            # idle_heartbeat=5.0,  # default value
            filter_subjects=worker_bindings,
            durable_name="git-workers",
            deliver_group="git-workers",
            deliver_subject=self.connection.new_inbox(),
        )

        try:
            await self.jetstream.add_consumer(stream=f"{self.settings.namespace}-rpcs", config=consumer_config)
        except nats.js.errors.BadRequestError as exc:
            if exc.err_code != 10013:  # consumer name already in use
                raise

        for subject in worker_bindings:
            await self.jetstream.subscribe(
                subject=subject,
                queue="git-workers",
                stream=f"{self.settings.namespace}-rpcs",
                config=consumer_config,
                cb=self.on_message,
                manual_ack=True,
            )

        await self._setup_callback(f"git-worker-{WORKER_IDENTITY}")

    async def publish(self, message: InfrahubMessage, routing_key: str, delay: Optional[MessageTTL] = None) -> None:
        with trace.get_tracer(__name__).start_as_current_span("publish_message") as span:
            span.set_attribute("routing_key", routing_key)

            if delay:
                # Delayed messages are directly handled in the callback using Nack
                return

            for enricher in self.message_enrichers:
                await enricher(message)
            message.assign_priority(priority=messages.message_priority(routing_key=routing_key))

            headers = {}
            if message.meta.correlation_id:
                headers["correlation_id"] = message.meta.correlation_id
            if message.meta.reply_to:
                headers["reply_to"] = message.meta.reply_to
            if message.meta.expiration:
                headers["expiration"] = str(message.meta.expiration)

            if message.meta.headers:
                # Filter None and non-string values
                for k, v in message.meta.headers.items():
                    if v:
                        headers[k] = str(v)

            if is_instrumentation_enabled():
                propagate.inject(headers)

            await self.jetstream.publish(
                subject=routing_key,
                payload=message.body,
                headers=headers,  # None value throws exception
            )

    async def reply(self, message: InfrahubMessage, routing_key: str) -> None:
        headers = {}
        if message.meta.correlation_id:
            headers["correlation_id"] = message.meta.correlation_id
        if message.meta.reply_to:
            headers["reply_to"] = message.meta.reply_to
        if message.meta.expiration:
            headers["expiration"] = str(message.meta.expiration)
        if message.meta.headers:
            # Filter None and non-string values
            for k, v in message.meta.headers.items():
                if v:
                    headers[k] = str(v)

        await self.jetstream.publish(
            subject=routing_key,
            payload=message.body,
            headers=headers,
        )

    async def rpc(self, message: InfrahubMessage, response_class: Type[ResponseClass]) -> ResponseClass:
        correlation_id = str(UUIDT())

        future = self.loop.create_future()
        self.futures[correlation_id] = future

        log_data = get_log_data()
        request_id = log_data.get("request_id", "")
        message.meta = Meta(
            request_id=request_id, correlation_id=correlation_id, reply_to=self.callback_queue.config.name
        )

        await self.service.send(message=message)

        response: nats.aio.msg.Msg = await future
        data = ujson.loads(response.data)
        return response_class(**data)
