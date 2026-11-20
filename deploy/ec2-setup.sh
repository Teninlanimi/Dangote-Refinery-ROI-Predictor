#!/usr/bin/env bash
# One-time setup for a fresh Amazon Linux 2023 EC2 instance.
# Run as ec2-user:   bash deploy/ec2-setup.sh   then log out and back in.
set -euo pipefail

echo ">> Installing Docker and git"
sudo dnf install -y docker git cronie
sudo systemctl enable --now docker crond
sudo usermod -aG docker "$USER"

echo ">> Installing the Docker Compose plugin"
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo ">> Adding 1 GB of swap (a t3.micro has only 1 GB of RAM)"
if [ ! -f /swapfile ]; then
  sudo dd if=/dev/zero of=/swapfile bs=1M count=1024 status=none
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  echo "/swapfile swap swap defaults 0 0" | sudo tee -a /etc/fstab >/dev/null
fi

echo ">> Done. Log out and SSH back in so the docker group applies, then:"
echo "   cd Dangote-Refinery-ROI-Predictor && cp .env.example .env && nano .env"
echo "   docker compose up -d --build"
