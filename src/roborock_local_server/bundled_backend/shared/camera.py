"""Camera live-view (WebRTC) support shared by the HTTPS server and MQTT proxy.

The app streams the camera over WebRTC and signals through ordinary V1 RPC
commands. The robot hands out the TURN relay it got from the Roborock cloud via
``get_turn_server``; with the cloud replaced, the server supplies a TURN relay
configured in ``[camera]`` instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# V1 RPC methods used by camera live view and its WebRTC signaling.
CAMERA_RPC_METHODS = frozenset(
    {
        "get_camera_status",
        "set_camera_status",
        "get_homesec_connect_status",
        "check_homesec_password",
        "set_homesec_password",
        "reset_homesec_password",
        "start_camera_preview",
        "stop_camera_preview",
        "switch_video_quality",
        "get_turn_server",
        "send_sdp_to_robot",
        "get_device_sdp",
        "send_ice_to_robot",
        "get_device_ice",
        "start_voice_chat",
        "stop_voice_chat",
        "set_voice_chat_volume",
        "enable_homesec_voice",
        "app_rc_start",
        "app_rc_move",
        "app_rc_end",
    }
)


@dataclass(frozen=True)
class TurnServerSettings:
    url: str
    user: str = ""
    password: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def rpc_result(self) -> dict[str, str]:
        """Result for the ``get_turn_server`` RPC, as the robot returns it."""
        return {"url": self.url, "user": self.user, "pwd": self.password}

    def http_payload(self) -> dict[str, Any]:
        """Payload for the robot's TURN provisioning HTTP request.

        The cloud response shape is not documented, so this carries the RPC field
        names plus the common WebRTC ``iceServers`` spellings.
        """
        return {
            **self.rpc_result(),
            "username": self.user,
            "password": self.password,
            "credential": self.password,
            "urls": [self.url],
            "ttl": 86400,
            "iceServers": [{"urls": [self.url], "username": self.user, "credential": self.password}],
        }


def is_turn_provisioning_path(path: str) -> bool:
    """True for HTTP paths that look like a TURN/ICE server lookup."""
    lowered = str(path or "").lower().replace("return", "")
    return "turn" in lowered or "iceserver" in lowered or "ice_server" in lowered
