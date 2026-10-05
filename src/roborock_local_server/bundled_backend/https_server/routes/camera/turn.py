from __future__ import annotations

import logging
from typing import Any

from shared.camera import is_turn_provisioning_path
from shared.context import ServerContext
from shared.http_helpers import wrap_response

_LOGGER = logging.getLogger(__name__)


def match(path: str) -> bool:
    return is_turn_provisioning_path(path)


def build(
    ctx: ServerContext,
    _query_params: dict[str, list[str]],
    _body_params: dict[str, list[str]],
    clean_path: str,
) -> dict[str, Any]:
    turn_server = ctx.turn_server
    if turn_server is None or not turn_server.configured:
        logger = ctx.loggers.get("api") or _LOGGER
        logger.warning(
            "TURN provisioning request %s but [camera] turn_url is not configured; camera live view will fail",
            clean_path,
        )
        return wrap_response({})
    return wrap_response(turn_server.http_payload())
