FROM ubuntu:jammy

USER root

# install packages
RUN apt-get clean && rm -rf /var/lib/apt/lists/partial \
    && apt-get update -o Acquire::CompressionTypes::Order::=gz \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
       ca-certificates gnupg git python3 python3-pip keychain

# clone dle-se-ansible repository
RUN git clone https://gitlab.com/postgres-ai/dle-se-ansible.git /dle-se-ansible

# install ansible (latest version)
RUN pip3 install ansible

# install requirements
RUN cd dle-se-ansible && \
    ansible-galaxy install -r requirements.yml

# clean
RUN apt-get autoremove -y --purge gnupg git \
    && apt-get clean -y autoclean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# set environment variable for Ansible collections paths
ENV ANSIBLE_COLLECTIONS_PATHS=/usr/lib/python3/dist-packages/ansible_collections
ENV USER=root

WORKDIR /dle-se-ansible
