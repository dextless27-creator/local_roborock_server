FROM python:3.11-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    coturn \
    curl \
    git \
    mosquitto \
    openssl \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/acme.sh \
  && curl -fsSL https://github.com/acmesh-official/acme.sh/archive/refs/heads/master.tar.gz \
  | tar -xz --strip-components=1 -C /opt/acme.sh \
  && chmod +x /opt/acme.sh/acme.sh \
  && ln -sf /opt/acme.sh/acme.sh /usr/local/bin/acme.sh

# Supervisor builds this add-on from its own folder, so fetch the server source
# from the branch. BUILD_VERSION changes with the add-on version, which busts the cache.
ARG BUILD_VERSION
ARG SOURCE_REPO=https://github.com/dextless27-creator/local_roborock_server.git
ARG SOURCE_REF=feat/camera-turn-support
RUN echo "building ${BUILD_VERSION}" \
  && git clone --depth 1 --branch "${SOURCE_REF}" "${SOURCE_REPO}" /tmp/src \
  && pip install --no-cache-dir /tmp/src \
  && rm -rf /tmp/src

WORKDIR /app

CMD ["python", "-m", "roborock_local_server.container_entrypoint"]
