#!/bin/bash

#sudo -E http_proxy="$http_proxy" dnf install -y podman podman-docker --allowerasing

#vi /etc/containers/containers.conf
#```
#[containers]
## Let containers use the proxy if the host has the env vars set
#http_proxy = true

#[engine]
#env = ["HTTP_PROXY=http://hksarg:8080", "HTTPS_PROXY=http://hksarg:8080", "NO_PROXY=localhost,127.0.0.1"]
#```
#sudo systemctl enable --now podman.socket
#sudo systemctl restart podman.socket
#podman pull hello-world
#podman compose up -d

podman ps -a

# Rebuild with the new changes and start fresh
podman-compose build

# Stop and remove existing containers
podman-compose down

# Rebuild with the new changes and start fresh
podman-compose up -d

sleep 30

# Check the logs to verify everything is working
podman-compose logs

#podman-compose run smspanel bash
