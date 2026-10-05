import json
import logging
from pathlib import Path

import pytest
from roborock.protocol import create_mqtt_decoder, create_mqtt_encoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

from roborock_local_server.backend import MqttTlsProxy, ServerContext, default_endpoint_rules, resolve_route
from roborock_local_server.bundled_backend.shared.camera import TurnServerSettings, is_turn_provisioning_path
from roborock_local_server.config import load_config
from roborock_local_server.server import ReleaseSupervisor

LOCAL_KEY = "abcdefghijklmnop"
APP_TOPIC = "rr/m/i/rriot-u/mqtt-user/duid-1"
TURN = TurnServerSettings(url="turn:192.168.1.10:3478", user="roborock", password="secret")

_BASE_CONFIG = """
[network]
stack_fqdn = "api-roborock.example.com"

[tls]
mode = "provided"
cert_file = "certs/fullchain.pem"
key_file = "certs/privkey.pem"

[admin]
password_hash = "pbkdf2_sha256$600000$abc$def"
session_secret = "abcdefghijklmnopqrstuvwxyz123456"
protocol_login_email = "user@example.com"
protocol_login_pin_hash = "pbkdf2_sha256$600000$ghi$jkl"
"""


def _write_config(tmp_path: Path, extra: str = "") -> Path:
    config_file = tmp_path / "config.toml"
    config_file.write_text(_BASE_CONFIG + extra, encoding="utf-8")
    return config_file


def _make_context(tmp_path: Path, turn_server: TurnServerSettings | None) -> ServerContext:
    return ServerContext(
        api_host="api.example.com",
        mqtt_host="mqtt.example.com",
        wood_host="wood.example.com",
        region="us",
        protocol_login_email="user@example.com",
        localkey="key123",
        duid="duid-1",
        mqtt_usr="usr",
        mqtt_passwd="pwd",
        mqtt_clientid="cid",
        https_port=443,
        mqtt_tls_port=8883,
        http_jsonl=tmp_path / "http.jsonl",
        mqtt_jsonl=tmp_path / "mqtt.jsonl",
        loggers={},
        turn_server=turn_server,
    )


def _make_proxy(tmp_path: Path, published: list, **kwargs) -> MqttTlsProxy:
    return MqttTlsProxy(
        cert_file=None,
        key_file=None,
        listen_host="127.0.0.1",
        listen_port=8883,
        backend_host="127.0.0.1",
        backend_port=18830,
        localkey=LOCAL_KEY,
        logger=logging.getLogger("test.camera"),
        decoded_jsonl=tmp_path / "decoded.jsonl",
        publish_to_broker=lambda host, port, topic, payload: published.append((host, port, topic, payload)),
        **kwargs,
    )


def _app_rpc_publish_packet(method: str, request_id: int) -> bytes:
    request = json.dumps({"id": request_id, "method": method, "params": []})
    payload = json.dumps({"t": 1700000000, "dps": {"101": request}}).encode()
    encoded = create_mqtt_encoder(LOCAL_KEY)(
        RoborockMessage(protocol=RoborockMessageProtocol.RPC_REQUEST, payload=payload)
    )
    topic = APP_TOPIC.encode()
    remaining = len(topic).to_bytes(2, "big") + topic + encoded
    remaining_len = bytearray()
    length = len(remaining)
    while True:
        byte_val = length % 128
        length //= 128
        remaining_len.append(byte_val | (0x80 if length else 0))
        if not length:
            break
    return bytes([0x30]) + bytes(remaining_len) + remaining


def test_load_config_camera_defaults_to_unconfigured(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path))

    assert config.camera.turn_url == ""
    assert config.camera.answer_turn_requests is True


def test_load_config_reads_camera_section(tmp_path: Path) -> None:
    config = load_config(
        _write_config(
            tmp_path,
            '\n[camera]\nturn_url = "turn:192.168.1.10:3478"\nturn_user = "roborock"\n'
            'turn_password = "secret"\nanswer_turn_requests = false\n',
        )
    )

    assert config.camera.turn_url == "turn:192.168.1.10:3478"
    assert config.camera.turn_user == "roborock"
    assert config.camera.turn_password == "secret"
    assert config.camera.answer_turn_requests is False


@pytest.mark.parametrize(
    ("camera_section", "message"),
    [
        ('turn_url = "http://example.com"', "must start with turn:"),
        ('turn_url = "turn:192.168.1.10:3478"', "turn_user and camera.turn_password are required"),
    ],
)
def test_load_config_rejects_invalid_camera_section(tmp_path: Path, camera_section: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_config(_write_config(tmp_path, f"\n[camera]\n{camera_section}\n"))


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/v1/getTurnServer", True),
        ("/api/v1/turn/server", True),
        ("/rtc/turn_server", True),
        ("/api/v1/iceServers", True),
        ("/api/v1/returnDevice", False),
        ("/region", False),
    ],
)
def test_is_turn_provisioning_path(path: str, expected: bool) -> None:
    assert is_turn_provisioning_path(path) is expected


def test_turn_route_returns_configured_relay(tmp_path: Path) -> None:
    route_name, payload = resolve_route(
        rules=default_endpoint_rules(),
        context=_make_context(tmp_path, TURN),
        clean_path="/api/v1/getTurnServer",
        query_params={},
        body_params={},
    )

    assert route_name == "camera_turn"
    assert payload["code"] == 200
    assert payload["data"]["url"] == "turn:192.168.1.10:3478"
    assert payload["data"]["user"] == "roborock"
    assert payload["data"]["pwd"] == "secret"
    assert payload["data"]["iceServers"] == [
        {"urls": ["turn:192.168.1.10:3478"], "username": "roborock", "credential": "secret"}
    ]


def test_turn_route_answers_empty_when_unconfigured(tmp_path: Path) -> None:
    route_name, payload = resolve_route(
        rules=default_endpoint_rules(),
        context=_make_context(tmp_path, TurnServerSettings(url="")),
        clean_path="/api/v1/getTurnServer",
        query_params={},
        body_params={},
    )

    assert route_name == "camera_turn"
    assert payload["data"] == {}


def test_turn_provisioning_path_does_not_require_app_token() -> None:
    assert ReleaseSupervisor._required_protocol_auth("/api/v1/getTurnServer") is None
    assert ReleaseSupervisor._required_protocol_auth("/api/v1/getHomeDetail") == "token"


def test_proxy_answers_app_get_turn_server_with_configured_relay(tmp_path: Path) -> None:
    published: list = []
    proxy = _make_proxy(tmp_path, published, turn_server=TURN)

    proxy._trace_packet("1", "c2b", _app_rpc_publish_packet("get_turn_server", 4242))

    assert len(published) == 1
    host, port, topic, payload = published[0]
    assert (host, port, topic) == ("127.0.0.1", 18830, "rr/m/o/rriot-u/mqtt-user/duid-1")
    [message] = create_mqtt_decoder(LOCAL_KEY)(payload)
    assert message.protocol == RoborockMessageProtocol.RPC_RESPONSE
    rpc = json.loads(json.loads(message.payload)["dps"]["102"])
    assert rpc == {"id": 4242, "result": {"url": "turn:192.168.1.10:3478", "user": "roborock", "pwd": "secret"}}

    decoded = json.loads((tmp_path / "decoded.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    [decoded_message] = decoded["decoded_messages"]
    assert decoded_message["turn_server_answered"] is True
    assert decoded_message["handled"] == {"camera": True, "method": "get_turn_server"}


def test_proxy_leaves_get_turn_server_to_robot_when_disabled_or_unconfigured(tmp_path: Path) -> None:
    published: list = []
    for proxy in (
        _make_proxy(tmp_path, published, turn_server=TURN, answer_turn_requests=False),
        _make_proxy(tmp_path, published, turn_server=None),
    ):
        proxy._trace_packet("1", "c2b", _app_rpc_publish_packet("get_turn_server", 1))
    # Only app-to-broker requests are answered locally.
    _make_proxy(tmp_path, published, turn_server=TURN)._trace_packet(
        "1", "b2c", _app_rpc_publish_packet("get_turn_server", 2)
    )

    assert published == []


def test_proxy_does_not_answer_other_camera_methods(tmp_path: Path) -> None:
    published: list = []
    proxy = _make_proxy(tmp_path, published, turn_server=TURN)

    proxy._trace_packet("1", "c2b", _app_rpc_publish_packet("start_camera_preview", 7))

    assert published == []
    decoded = json.loads((tmp_path / "decoded.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert decoded["decoded_messages"][0]["handled"] == {"camera": True, "method": "start_camera_preview"}
