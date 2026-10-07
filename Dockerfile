FROM ubuntu:jammy

USER root

# install packages
RUN apt-get clean && rm -rf /var/lib/apt/lists/partial \
    && apt-get update -o Acquire::CompressionTypes::Order::=gz \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
       ca-certificates gnupg git python3 python3-pip keychain

# copy dle-se-ansible repository
ADD . /dle-se-ansible

# install ansible (latest version)
RUN pip3 install ansible \
    boto3 dopy google-auth hcloud

# install requirements
RUN cd dle-se-ansible && \
    ansible-galaxy install -r requirements.yml && \
    ansible-galaxy collection install hetzner.hcloud:7.1.0 -p /usr/lib/python3/dist-packages/ansible_collections

# hetzner.hcloud is pinned above, into ANSIBLE_COLLECTIONS_PATHS, which wins over the
# copy bundled with the ansible package: that one (3.1.1) reads server.datacenter, which
# the Hetzner API no longer returns, so every server create fails with
# "'NoneType' object has no attribute 'name'" (platform-all#876).

# clean
RUN apt-get autoremove -y --purge gnupg git \
    && apt-get clean -y autoclean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# set environment variable for Ansible collections paths
ENV ANSIBLE_COLLECTIONS_PATHS=/usr/lib/python3/dist-packages/ansible_collections
ENV USER=root

WORKDIR /dle-se-ansible
