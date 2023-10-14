from typing import Callable, Dict, Any, Optional

from hivemind_core.database import ClientDatabase
from hivemind_core.protocol import HiveMindListenerProtocol, HiveMindClientConnection, HiveMindNodeType, \
    HiveMindListenerInternalProtocol
from hivemind_core.service import HiveMindService, MessageBusEventHandler
from json_database import JsonStorageXDG
from ovos_bus_client.session import Session
from ovos_utils.log import LOG
from ovos_utils.messagebus import FakeBus
from poorman_handshake import HandShake, PasswordHandShake

from multimind.minicroft import MiniCroft

DEFAULT_SKILLS = ["skill-ovos-hello-world.openvoiceos",
                  "skill-ovos-fallback-unknown.openvoiceos"]
PREMIUM_SKILLS = []


def on_ready():
    LOG.info('HiveMind bus service ready!')


def on_alive():
    LOG.info('HiveMind bus service alive')


def on_started():
    LOG.info('HiveMind bus service started!')


def on_error(e='Unknown'):
    LOG.info('HiveMind bus failed to start ({})'.format(repr(e)))


def on_stopping():
    LOG.info('HiveMind bus is shutting down...')


class MultiMindInternalProtocol(HiveMindListenerInternalProtocol):

    def register_bus_handlers(self):
        pass  # bus is per client now, done on_open

    @property
    def clients(self) -> Dict[str, HiveMindClientConnection]:
        return MultiMindProtocol.clients


class MultiMindProtocol(HiveMindListenerProtocol):
    internal_protocol: Optional[MultiMindInternalProtocol] = None

    def handle_new_client(self, client: HiveMindClientConnection):
        super().handle_new_client(client)
        self.register_client_handlers(client)

    def handle_client_disconnected(self, client: HiveMindClientConnection):
        super().handle_client_disconnected(client)
        client_keys = [c.key for _, c in MultiMindProtocol.clients.items()]
        if client.key not in client_keys:
            LOG.info(f"Stopping brain for key: {client.key}")
            client.fakecroft.stop()

    def register_client_handlers(self, client: HiveMindClientConnection):
        LOG.debug(f"registering MultiMind mycroft bus handlers for client: {client.name}")
        client.bus.on("message", self.internal_protocol.handle_internal_mycroft)  # catch all

    def get_bus(self, client: HiveMindClientConnection):
        # allow subclasses to use dedicated bus per client
        return client.bus


class MultiMindBusEventHandler(MessageBusEventHandler):

    def open(self):
        auth = self.request.uri.split("/?authorization=")[-1]
        name, key = self.decode_auth(auth)
        LOG.info(f"authorizing client: {name}")

        # in regular handshake an asymmetric key pair is used
        handshake = HandShake(HiveMindService.identity.private_key)
        self.client = HiveMindClientConnection(key=key, name=name,
                                               ip=self.request.remote_ip, socket=self, sess=Session(),
                                               handshake=handshake, loop=self.protocol.loop)

        with ClientDatabase() as users:
            user = users.get_client_by_api_key(key)
            if not user:
                LOG.error("Client provided an invalid api key")
                self.protocol.handle_invalid_key_connected(self.client)
                self.close()
                return

            self.client.crypto_key = user.crypto_key
            self.client.blacklist = user.blacklist.get("messages", [])
            self.client.allowed_types = user.allowed_types
            if user.password:
                # pre-shared password to derive aes_key
                self.client.pswd_handshake = PasswordHandShake(user.password)

            self.client.node_type = HiveMindNodeType.NODE  # TODO . placeholder

            if not self.client.crypto_key and \
                    not self.protocol.handshake_enabled \
                    and self.protocol.require_crypto:
                LOG.error("No pre-shared crypto key for client and handshake disabled, "
                          "but configured to require crypto!")
                # clients requiring handshake support might fail here
                self.protocol.handle_invalid_protocol_version(self.client)
                self.close()
                return

        db = JsonStorageXDG("multimind", subfolder="hivemind")
        if key not in db:
            LOG.debug(f"assigning default skills to {key}")
            db[key] = DEFAULT_SKILLS
            db.store()

        LOG.info(f"Assigning brain for client: {name}")
        LOG.info(f"available skills: {db[key]}")

        if key not in MultiMind.brains:
            LOG.info(f"Creating new brain for access key: {key}")
            MultiMind.brains[key] = MiniCroft(db[key], bus=FakeBus())
            MultiMind.brains[key].start()

        self.client.bus = MultiMind.brains[key].bus
        self.client.fakecroft = MultiMind.brains[key]

        self.protocol.handle_new_client(self.client)


class MultiMind(HiveMindService):
    brains: dict = {}

    def __init__(self,
                 alive_hook: Callable = on_alive,
                 started_hook: Callable = on_started,
                 ready_hook: Callable = on_ready,
                 error_hook: Callable = on_error,
                 stopping_hook: Callable = on_stopping,
                 websocket_config: Optional[Dict[str, Any]] = None):
        # these kwargs from HiveMindService define the MultiMind protocol
        bus = FakeBus()
        protocol = MultiMindProtocol
        ws_handler = MultiMindBusEventHandler
        super().__init__(alive_hook, started_hook, ready_hook, error_hook, stopping_hook,
                         websocket_config, protocol, bus, ws_handler)
