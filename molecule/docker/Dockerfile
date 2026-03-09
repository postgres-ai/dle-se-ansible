FROM geerlingguy/docker-ubuntu2204-ansible:latest

RUN add-apt-repository -y universe \
  && apt-get update \
  && apt-get install -y apt-transport-https ca-certificates curl software-properties-common gnupg gpg-agent dirmngr python3-debian --no-install-recommends \
  && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/docker-archive.gpg \
  && echo "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
  && apt-get update && apt-get install -y docker-ce=5:27.3.1-1~ubuntu.22.04~jammy docker-ce-cli=5:27.3.1-1~ubuntu.22.04~jammy containerd.io \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

VOLUME /var/lib/docker
ENTRYPOINT ["/entrypoint.sh"]
