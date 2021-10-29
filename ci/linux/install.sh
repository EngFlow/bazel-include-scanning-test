#!/bin/bash

set -evx

# Print basic architecture info

uname -a
cat /etc/issue.net

# Determine architecture

case $(uname -m) in
'x86_64')
  ARCH=amd64
  XARCH=x64
  ;;
'aarch64')
  ARCH=arm64
  XARCH=arm64
  ;;
*)
  echo $(uname -m)
  exit 1
  ;;
esac

# Ubuntu LTS releases use slightly different version numbers than non-LTS
# releases. We don't want to be overly specific here, and match anything similar
# to "Ubuntu 16.04.7 LTS".
case $(cat /etc/issue.net) in
'Ubuntu 18.04'*)
  OS_LABEL=ubuntu1804
  ;;
'Ubuntu 20.04'*)
  OS_LABEL=ubuntu2004
  ;;
'Debian GNU/Linux 10')
  OS_LABEL=debian10
  ;;
*)
  echo $(cat /etc/issue.net)
  exit 1
  ;;
esac


# Unbreak Ubuntu 20.04
# For no apparent reason, the standard image comes *without* Python, which makes
# apt update fail after successfully pulling the package lists.

if [[ $OS_LABEL == "ubuntu2004" ]]; then
  apt download python3-minimal
  sudo apt install --reinstall ./python3-minimal_*.deb
fi


# Install dependencies.

sudo DEBIAN_FRONTEND=noninteractive apt update
sudo DEBIAN_FRONTEND=noninteractive apt upgrade -yq
sudo DEBIAN_FRONTEND=noninteractive apt install -yq \
  apt-transport-https \
  build-essential  \
  ca-certificates \
  curl \
  docker.io \
  git \
  python \
  python3 \
  python3-pip \
  unzip \
  zip


# Install OpenJDK

sudo DEBIAN_FRONTEND=noninteractive apt install -yq openjdk-11-jdk-headless


# Install amazon-ecr-credential-helper

if [[ $OS_LABEL == "ubuntu1804" ]]; then
  # There's no package of amazon-ecr-credential-helper for Ubuntu 16.04 / 18.04.
  sudo curl -L \
    -o /usr/local/bin/docker-credential-ecr-login \
    https://amazon-ecr-credential-helper-releases.s3.us-east-2.amazonaws.com/0.5.0/linux-amd64/docker-credential-ecr-login
  sudo chmod +x /usr/local/bin/docker-credential-ecr-login
else
  sudo DEBIAN_FRONTEND=noninteractive apt install -yq \
    amazon-ecr-credential-helper
fi


# Install Bazelisk as Bazel

sudo curl -L \
  -o /usr/local/bin/bazel \
  https://github.com/bazelbuild/bazelisk/releases/download/v1.10.1/bazelisk-linux-${ARCH}
sudo chmod +x /usr/local/bin/bazel


# Create CI user

sudo useradd -ms /bin/bash github-actions-runner
sudo adduser github-actions-runner docker


# Install GitHub Actions Runner

curl -L \
  -o /tmp/actions-runner.tar.gz \
  https://github.com/actions/runner/releases/download/v2.278.0/actions-runner-linux-${XARCH}-2.278.0.tar.gz
sudo mkdir /github-actions-runner
sudo chown -R github-actions-runner /github-actions-runner
sudo chmod -R 775 /github-actions-runner
cd /github-actions-runner
sudo tar xzf /tmp/actions-runner.tar.gz
rm /tmp/actions-runner.tar.gz


# Register GitHub Actions Runner and install systemd service

cd /github-actions-runner
sudo runuser \
  -u github-actions-runner \
  -- \
    ./config.sh \
    --name "${OS_LABEL}-${XARCH}-$2" \
    --url "https://github.com/EngFlow/include-scanning" \
    --token "$1" \
    --labels "${OS_LABEL}"
sudo ./svc.sh install github-actions-runner


# Allow "clone" for unprivileged users (used for sandboxing)

sudo mv /tmp/allow_unprivileged_userns_clone.conf /etc/sysctl.d/allow_unprivileged_userns_clone.conf
sudo chown root /etc/sysctl.d/allow_unprivileged_userns_clone.conf
sudo chmod 775 /etc/sysctl.d/allow_unprivileged_userns_clone.conf


# Add SSH CA certificate for user keys

sudo mv /tmp/ca.engflow.com.pub /etc/ssh/ca.engflow.com.pub
sudo chown root /etc/ssh/ca.engflow.com.pub
sudo chmod 600 /etc/ssh/ca.engflow.com.pub
echo "TrustedUserCAKeys /etc/ssh/ca.engflow.com.pub" | sudo tee -a /etc/ssh/sshd_config

