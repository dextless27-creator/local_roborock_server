from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest

from roborock_local_server.ha_addon import write_config_from_home_assistant_options


def _write_options(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_write_config_from_home_assistant_options_provided_tls(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"
    token_path = tmp_path / "cloudflare_token"

    _write_options(
        options_path,
        {
            "stack_fqdn": "https://api-roborock.example.com",
            "https_port": 8443,
            "mqtt_tls_port": 9443,
            "region": "us",
            "tls_mode": "provided",
            "cert_file": "/ssl/fullchain.pem",
            "key_file": "/ssl/privkey.pem",
            "admin_password": "super-secret-password",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "123456",
        },
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
        cloudflare_token_path=token_path,
    )

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed["network"]["stack_fqdn"] == "api-roborock.example.com"
    assert parsed["network"]["https_port"] == 8443
    assert parsed["network"]["mqtt_tls_port"] == 9443
    assert parsed["network"]["advertised_https_port"] == 8443
    assert parsed["network"]["advertised_mqtt_tls_port"] == 9443
    assert parsed["broker"]["mode"] == "embedded"
    assert parsed["broker"]["host"] == "127.0.0.1"
    assert parsed["broker"]["port"] == 18830
    assert parsed["broker"]["enable_topic_bridge"] is True
    assert parsed["tls"]["mode"] == "provided"
    assert parsed["tls"]["cert_file"] == "/ssl/fullchain.pem"
    assert parsed["tls"]["key_file"] == "/ssl/privkey.pem"
    assert parsed["admin"]["protocol_auth_enabled"] is True
    assert parsed["admin"]["new_connections_enabled"] is True
    assert parsed["admin"]["protocol_login_email"] == "user@example.com"
    assert len(str(parsed["admin"]["session_secret"])) >= 24
    assert str(parsed["admin"]["password_hash"]).startswith("pbkdf2_sha256$")
    assert str(parsed["admin"]["protocol_login_pin_hash"]).startswith("pbkdf2_sha256$")
    assert token_path.exists() is False


def test_write_config_from_home_assistant_options_reverse_proxy_settings(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "https_port": 555,
            "mqtt_tls_port": 8881,
            "advertised_https_port": 443,
            "advertised_mqtt_tls_port": 8883,
            "tls_mode": "provided",
            "cert_file": "/ssl/fullchain.pem",
            "key_file": "/ssl/privkey.pem",
            "admin_password": "super-secret-password",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "123456",
        },
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
    )

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed["network"]["https_port"] == 555
    assert parsed["network"]["mqtt_tls_port"] == 8881
    assert parsed["network"]["advertised_https_port"] == 443
    assert parsed["network"]["advertised_mqtt_tls_port"] == 8883


def test_write_config_from_home_assistant_options_provided_tls_requires_paths_when_blank(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "tls_mode": "provided",
            "cert_file": "",
            "key_file": "",
            "admin_password": "super-secret-password",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "123456",
        },
    )

    with pytest.raises(ValueError, match="cert_file is required"):
        write_config_from_home_assistant_options(
            options_path=options_path,
            config_path=config_path,
        )


def test_write_config_from_home_assistant_options_ignores_legacy_protocol_auth_toggle(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "cert_file": "/ssl/fullchain.pem",
            "key_file": "/ssl/privkey.pem",
            "admin_password": "secret",
            "protocol_auth_enabled": False,
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
    )

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed["admin"]["protocol_auth_enabled"] is True
    assert parsed["admin"]["new_connections_enabled"] is True


def test_write_config_from_home_assistant_options_reuses_existing_session_secret(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "cert_file": "/ssl/fullchain.pem",
            "key_file": "/ssl/privkey.pem",
            "admin_password": "secret",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
    )
    first_secret = tomllib.loads(config_path.read_text(encoding="utf-8"))["admin"]["session_secret"]

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
    )
    second_secret = tomllib.loads(config_path.read_text(encoding="utf-8"))["admin"]["session_secret"]

    assert len(str(first_secret)) >= 24
    assert second_secret == first_secret


def test_write_config_from_home_assistant_options_ignores_legacy_broker_flags(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "use_external_broker": True,
            "broker_host": "mqtt.internal",
            "broker_port": 1883,
            "enable_topic_bridge": False,
            "cert_file": "/ssl/fullchain.pem",
            "key_file": "/ssl/privkey.pem",
            "admin_password": "secret",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
    )

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed["broker"]["mode"] == "embedded"
    assert parsed["broker"]["host"] == "127.0.0.1"
    assert parsed["broker"]["port"] == 18830
    assert parsed["broker"]["enable_topic_bridge"] is True


def test_write_config_from_home_assistant_options_cloudflare(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"
    token_path = tmp_path / "run" / "secrets" / "cloudflare_token"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "tls_mode": "cloudflare_acme",
            "tls_base_domain": "example.com",
            "tls_email": "acme@example.com",
            "acme_server": "zerossl",
            "cloudflare_token": "cloudflare-token-123",
            "admin_password": "secret",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
        cloudflare_token_path=token_path,
    )

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed["tls"]["mode"] == "cloudflare_acme"
    assert parsed["tls"]["base_domain"] == "example.com"
    assert parsed["tls"]["email"] == "acme@example.com"
    assert parsed["tls"]["acme_server"] == "zerossl"
    assert parsed["tls"]["cloudflare_token_file"] == str(token_path)
    assert token_path.read_text(encoding="utf-8") == "cloudflare-token-123"


def test_write_config_from_home_assistant_options_infers_cloudflare_acme_from_token(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"
    token_path = tmp_path / "run" / "secrets" / "cloudflare_token"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "tls_mode": "provided",
            "tls_base_domain": "example.com",
            "tls_email": "acme@example.com",
            "acme_server": "zerossl",
            "cloudflare_token": "cloudflare-token-123",
            "cert_file": "",
            "key_file": "",
            "admin_password": "secret",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
        cloudflare_token_path=token_path,
    )

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed["tls"]["mode"] == "cloudflare_acme"
    assert parsed["tls"]["base_domain"] == "example.com"
    assert parsed["tls"]["email"] == "acme@example.com"
    assert parsed["tls"]["acme_server"] == "zerossl"
    assert parsed["tls"]["cloudflare_token_file"] == str(token_path)
    assert "cert_file" not in parsed["tls"]
    assert "key_file" not in parsed["tls"]
    assert token_path.read_text(encoding="utf-8") == "cloudflare-token-123"


def test_write_config_from_home_assistant_options_actalis_requires_eab(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "tls_mode": "cloudflare_acme",
            "tls_base_domain": "example.com",
            "tls_email": "acme@example.com",
            "acme_server": "actalis",
            "cloudflare_token": "cloudflare-token-123",
            "admin_password": "secret",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    with pytest.raises(ValueError, match="acme_eab_kid is required"):
        write_config_from_home_assistant_options(
            options_path=options_path,
            config_path=config_path,
        )


def test_write_config_from_home_assistant_options_actalis_writes_eab(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"
    token_path = tmp_path / "run" / "secrets" / "cloudflare_token"
    kid_path = tmp_path / "run" / "secrets" / "acme_eab_kid"
    hmac_path = tmp_path / "run" / "secrets" / "acme_eab_hmac_key"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "tls_mode": "cloudflare_acme",
            "tls_base_domain": "example.com",
            "tls_email": "acme@example.com",
            "acme_server": "actalis",
            "acme_eab_kid": "kid-123",
            "acme_eab_hmac_key": "hmac-456",
            "cloudflare_token": "cloudflare-token-123",
            "admin_password": "secret",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
        cloudflare_token_path=token_path,
        acme_eab_kid_path=kid_path,
        acme_eab_hmac_key_path=hmac_path,
    )

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed["tls"]["acme_server"] == "actalis"
    assert parsed["tls"]["acme_eab_kid"] == ""
    assert parsed["tls"]["acme_eab_hmac_key"] == ""
    assert parsed["tls"]["acme_eab_kid_file"] == str(kid_path)
    assert parsed["tls"]["acme_eab_hmac_key_file"] == str(hmac_path)
    assert kid_path.read_text(encoding="utf-8") == "kid-123"
    assert hmac_path.read_text(encoding="utf-8") == "hmac-456"


def test_write_config_from_home_assistant_options_rejects_invalid_acme_server(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "tls_mode": "provided",
            "acme_server": "bad-ca",
            "cert_file": "/ssl/fullchain.pem",
            "key_file": "/ssl/privkey.pem",
            "admin_password": "secret",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    with pytest.raises(ValueError, match="acme_server must be 'zerossl' or 'actalis'"):
        write_config_from_home_assistant_options(
            options_path=options_path,
            config_path=config_path,
        )


def test_write_config_from_home_assistant_options_rejects_external_tls(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "listener_mode": "external_tls",
            "https_port": 443,
            "mqtt_tls_port": 8883,
            "admin_password": "secret",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    with pytest.raises(ValueError, match="external_tls"):
        write_config_from_home_assistant_options(
            options_path=options_path,
            config_path=config_path,
        )


def test_write_config_from_home_assistant_options_requires_admin_password(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "cert_file": "/ssl/fullchain.pem",
            "key_file": "/ssl/privkey.pem",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "123456",
        },
    )

    with pytest.raises(ValueError, match="admin_password is required"):
        write_config_from_home_assistant_options(
            options_path=options_path,
            config_path=config_path,
        )


def test_write_config_from_home_assistant_options_requires_api_prefix(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"

    _write_options(
        options_path,
        {
            "stack_fqdn": "lashleyhomeassist.duckdns.org",
            "admin_password": "super-secret-password",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "123456",
        },
    )

    with pytest.raises(ValueError, match="stack_fqdn must start with api-"):
        write_config_from_home_assistant_options(
            options_path=options_path,
            config_path=config_path,
        )


def test_write_config_from_home_assistant_options_removes_stale_cloudflare_token_when_using_provided_tls(
    tmp_path: Path,
) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"
    token_path = tmp_path / "run" / "secrets" / "cloudflare_token"
    kid_path = tmp_path / "run" / "secrets" / "acme_eab_kid"
    hmac_path = tmp_path / "run" / "secrets" / "acme_eab_hmac_key"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text("stale-token", encoding="utf-8")
    kid_path.write_text("stale-kid", encoding="utf-8")
    hmac_path.write_text("stale-hmac", encoding="utf-8")

    _write_options(
        options_path,
        {
            "stack_fqdn": "api-roborock.example.com",
            "tls_mode": "provided",
            "cert_file": "/ssl/fullchain.pem",
            "key_file": "/ssl/privkey.pem",
            "admin_password": "secret",
            "protocol_login_email": "user@example.com",
            "protocol_login_pin": "654321",
        },
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
        cloudflare_token_path=token_path,
        acme_eab_kid_path=kid_path,
        acme_eab_hmac_key_path=hmac_path,
    )

    assert token_path.exists() is False
    assert kid_path.exists() is False
    assert hmac_path.exists() is False


def _camera_options(**camera: object) -> dict[str, object]:
    return {
        "stack_fqdn": "api-roborock.example.com",
        "tls_mode": "provided",
        "cert_file": "/ssl/fullchain.pem",
        "key_file": "/ssl/privkey.pem",
        "admin_password": "super-secret-password",
        "protocol_login_email": "user@example.com",
        "protocol_login_pin": "123456",
        **camera,
    }


def test_write_config_from_home_assistant_options_camera_off_by_default(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"
    turn_conf = tmp_path / "turnserver.conf"
    turn_conf.write_text("stale", encoding="utf-8")
    _write_options(options_path, _camera_options())

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
        cloudflare_token_path=tmp_path / "cloudflare_token",
        turnserver_conf_path=turn_conf,
    )

    assert "camera" not in tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert not turn_conf.exists()


def test_write_config_from_home_assistant_options_bundled_turn(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"
    turn_conf = tmp_path / "turnserver.conf"
    _write_options(
        options_path,
        _camera_options(
            camera_turn_mode="bundled",
            camera_turn_host="192.168.1.10",
            camera_turn_password="relay-secret",
            camera_turn_external_ip="203.0.113.7",
        ),
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
        cloudflare_token_path=tmp_path / "cloudflare_token",
        turnserver_conf_path=turn_conf,
    )

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed["camera"] == {
        "turn_url": "turn:192.168.1.10:3478",
        "turn_user": "roborock",
        "turn_password": "relay-secret",
    }
    conf_lines = turn_conf.read_text(encoding="utf-8").splitlines()
    assert "listening-port=3478" in conf_lines
    assert "user=roborock:relay-secret" in conf_lines
    assert "external-ip=203.0.113.7" in conf_lines


def test_write_config_from_home_assistant_options_external_turn_writes_no_coturn_config(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    config_path = tmp_path / "config.toml"
    turn_conf = tmp_path / "turnserver.conf"
    _write_options(
        options_path,
        _camera_options(
            camera_turn_mode="external",
            camera_turn_host="turn.example.com",
            camera_turn_port=5349,
            camera_turn_password="relay-secret",
        ),
    )

    write_config_from_home_assistant_options(
        options_path=options_path,
        config_path=config_path,
        cloudflare_token_path=tmp_path / "cloudflare_token",
        turnserver_conf_path=turn_conf,
    )

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert parsed["camera"]["turn_url"] == "turn:turn.example.com:5349"
    assert not turn_conf.exists()


def test_write_config_from_home_assistant_options_bundled_turn_requires_password(tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    _write_options(options_path, _camera_options(camera_turn_mode="bundled", camera_turn_host="192.168.1.10"))

    with pytest.raises(ValueError, match="camera_turn_password"):
        write_config_from_home_assistant_options(
            options_path=options_path,
            config_path=tmp_path / "config.toml",
            cloudflare_token_path=tmp_path / "cloudflare_token",
            turnserver_conf_path=tmp_path / "turnserver.conf",
        )
