# Camera Live View

!!! warning "Experimental"
    Camera live view (remote view) support has not been confirmed on a real vacuum yet. If you test it, please report the result in [#18](https://github.com/Python-roborock/local_roborock_server/issues/18) with the logs listed under [Reporting results](#reporting-results).

## How it works

The app streams the vacuum camera over WebRTC. Setup messages (`start_camera_preview`, `send_sdp_to_robot`, `get_device_sdp`, `send_ice_to_robot`, `get_device_ice`) already go through this server's MQTT broker like any other command.

The missing piece is the TURN relay. WebRTC needs one when the phone and the vacuum cannot reach each other directly, for example when you view the camera away from home. With the official cloud, the vacuum gets TURN credentials from Roborock and hands them to the app through the `get_turn_server` command. With this server, nothing provides those credentials, so the preview fails right away.

This server now fills that gap in two ways:

- **MQTT:** when the app sends `get_turn_server`, the server answers it directly with the TURN relay from `[camera]`. The robot's own reply comes later and the app ignores it.
- **HTTPS:** requests from the vacuum to paths that look like a TURN lookup (for example containing `turn` or `iceServers`) get the same relay. These paths do not require an app token, the same as `/region` and `/time`.

## Setup

1. Run a TURN server. The bundled `compose.yaml` has an optional [coturn](https://github.com/coturn/coturn) service:

    ```bash
    ROBOROCK_TURN_PASSWORD='a-long-random-password' docker compose --profile camera up -d
    ```

    Any TURN server works. If you run your own, enable long-term credentials (`lt-cred-mech`).

2. Add the relay to `config.toml` and restart the server:

    ```toml
    [camera]
    turn_url = "turn:192.168.1.10:3478"   # IP or hostname both the phone and the vacuum can reach
    turn_user = "roborock"
    turn_password = "a-long-random-password"
    ```

3. Let the vacuum reach the TURN server. If the vacuum is on a firewalled IoT network, allow it to reach the TURN host on UDP/TCP `3478` and UDP `49160-49200`.

### Viewing from outside your home network

The phone must be able to reach the TURN server from the internet:

- Forward UDP/TCP `3478` and UDP `49160-49200` from your router to the TURN host.
- Set `--external-ip` in the coturn service to your public IP.
- Set `turn_url` to an address that works from outside your network, such as a dynamic DNS hostname.

On your home Wi-Fi, a LAN address is enough.

!!! note
    The TURN credentials are handed to anyone who can reach this server's HTTPS port, because the vacuum fetches them without logging in. Use a dedicated TURN user and password, not one you use anywhere else.

## Reporting results

The vacuum's exact TURN request has never been captured, so reports are very useful. After trying the live view, send:

- The lines containing `[camera]` from `data/runtime/mqtt_server.log`. They show each camera command and the robot's response or error, such as `-10012`.
- The entries from `data/runtime/decompiled_http.jsonl` written while you opened the camera, especially any with `"route": "camera_turn"` or `"route": "catchall"`.
- Your vacuum model, firmware version, and whether the phone was on the same network as the vacuum.

Remove secrets (tokens, passwords, keys) before posting logs publicly.

To turn off the local `get_turn_server` answer and let the robot reply itself, set `answer_turn_requests = false` under `[camera]`.
