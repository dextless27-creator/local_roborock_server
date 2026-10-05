# Roborock Local Server (Camera Test)

Test build of Roborock Local Server with camera live view support. It is built from the
`feat/camera-turn-support` branch and bundles a [coturn](https://github.com/coturn/coturn)
TURN relay. See `docs/camera.md` in the repository for how it works.

## Switching from the regular add-on

1. Copy your options from the regular add-on into this one.
2. Stop the regular Roborock Local Server add-on. Both use ports 555 and 8881.
3. Start this add-on. It has its own data folder, so onboard the vacuum again and
   re-authenticate the Roborock integration in Home Assistant.

To go back, stop this add-on and start the regular one again. Its data is untouched.

## Camera options

- `camera_turn_mode`: `bundled` runs the TURN relay inside this add-on, `external` uses
  your own TURN server, `off` disables camera support.
- `camera_turn_host`: an IP or hostname both your phone and the vacuum can reach, usually
  your Home Assistant LAN IP.
- `camera_turn_password`: a long random password used only for this relay.
- `camera_turn_external_ip`: your public IP, only needed to view the camera from outside
  your home network. Also forward UDP/TCP 3478 and UDP 49160-49200 to Home Assistant.
