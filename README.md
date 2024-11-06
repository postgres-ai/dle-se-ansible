## :rocket: `dle-se-ansible`: Automation of the DBLab Engine using Ansible.

This playbook deploys [DBLab Engine](https://gitlab.com/postgres-ai/database-lab) Standard Edition (DBLab SE) to any environment, cloud or on-prem.

The HowTo guide can be found here: [How to install DBLab Engine using the Postgres.ai Console](https://postgres.ai/docs/how-to-guides/administration/install-dle-from-postgres-ai).

## Requirements

- You will need the `Org key` and `Project name` from the [Postgres.ai platform](https://console.postgres.ai). These are provided by the platform upon registration. You can find more details [here](https://postgres.ai/docs/how-to-guides/administration/install-dle-from-postgres-ai).
  - Keep in mind that without specifying these values in the `platform_org_key` and `platform_project_name` variables, the Ansible Playbook will not be executed.
- For deployment on an existing server:
  - Debian 11, 12, or Ubuntu 22.04, 24.04
  - Root privileges or sudo access
  - Data storage disk (which is larger than the size of the database)
- For deployment in one of the supported clouds:
  - AWS: [Access key ID and secret](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html). Before performing automation, these values must be exported to the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` variables, respectively.
  - GCP: [Service account](https://developers.google.com/identity/protocols/oauth2/service-account#creatinganaccount). Before performing automation, the contents of the service account JSON file must be exported to the `GCP_SERVICE_ACCOUNT_CONTENTS` variable.
  - Digital Ocean: [Personal Access Token](https://docs.digitalocean.com/reference/api/create-personal-access-token/). Before performing automation, this token must be exported to the `DO_API_TOKEN` variable.
  - Hetzner Cloud: [API Token](https://docs.hetzner.com/cloud/api/getting-started/generating-api-token/). Before performing automation, this token must be exported to the `HCLOUD_API_TOKEN` variable.
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html) version 2.11.0 and higher, or a [Docker](https://docs.docker.com/engine/install/) on the computer from which the automation is performed.


## Variables

#### Cloud:

| Variable | Description | Default value |
|:---------|:------------|:-------------:|
| `provision` (optional) | Determines in which cloud to deploy the DBLab Engine server. Available values: `aws`, `gcp`, `azure`, `digitalocean`, `hetzner`, `none` (skip creating server resources). | `none` |
| `server_name` (required) | The name of server to be created. | "" |
| `server_type` (required) | The type of server to be created (the value depends on the selected cloud). | "" |
| `server_image` (required) | The system image for the server to be created (the value depends on the selected cloud). | "" |
| `server_location` (required) | The region in which the server will be created (the value depends on the selected cloud). | "" |
| `server_network` (optional) | If specified, the server will be added to this network (must be created in advance). By default, the server is added to the default network (the value depends on the selected cloud). | "" |
| `volume_size` (required) | The storage for `zpool_disk` (size in gigabytes). | "" |
| `volume_type` (optional) | The volume type (the value depends on the selected cloud). Not applicable for Hetzner, DigitalOcean. | `gp3` for AWS, `pd-ssd` for GCP |
| `ssh_key_name` (optional) | The name of the SSH key pre-uploaded to the cloud that will be added to the DBLab Engine server. If not specified, all ssh keys will be added (applicable for hetzner, digitalocean).  | "" |
| `ssh_key_content` (optional) | if specified, the contents of the public key will be added to the cloud (for GCP - will be added to the server). | "" |
| `state` (optional) | '`present`' to create or '`absent`' to delete server resources. | `present` |

Note: if 'ssh_key_name' is not specified, with each new execution of the playbook, a new temporary SSH key is created (_automatically filling in the values of variables 'ssh_key_name' and 'ssh_key_content'_). To access the server during deployment. At the end of the deployment, the temporary SSH key is deleted.

#### System:

| Variable | Description | Default value |
|:---------|:------------|:-------------:|
| `ssh_public_keys` (optional) | These SSH public keys will be added to the DBLab Engine server's to `~/.ssh/authorized_keys` file. Providing at least one public key is recommended to ensure access to the server after deployment. | "" |
| `username` (optional) | The system user, owner of configuration files. | `root` |
| `zpool_disk` (optional) | Disk for the ZFS pool (e.g.: /dev/sdb). If the specified disk is not empty, the playbook stops with an error (data deletion protection). If not specified, an attempt will be made to automatically detect an empty volume. | "" |
| `zpool_name` (optional) | The name of the ZFS pool. | `dblab_pool` |
| `zpool_mount_dir` (optional) | The path to mount the ZFS pool. | `/var/lib/dblab` |
| `zpool_options` (optional) | Options used when creating a ZFS pool. | `-O compression=on -O atime=off -O recordsize=128k -O logbias=throughput` |
| `zpool_datasets_number`(optional)  | The number of datasets that will be created for the ZFS pool. | `2` |
| `zpool_datasets_name`(optional)  | Base name for ZFS datasets. Suffixes (01, 02, etc.) are appended based on `zpool_datasets_number`. | `dataset` |

#### DBLab Engine:

| Variable | Description | Default value |
|:---------|:------------|:-------------:|
| `dblab_engine_version` (optional) | The DBLab Engine version. | `3.5.0` |
| `dblab_engine_ui_version` (optional) | The DBLab Engine UI version.| `{{ dblab_engine_version }}` |
| `dblab_engine_verification_token` (required) | The token that is used to work with DBLab Engine API. | `some-secret-token` |
| `dblab_engine_base_path`(optional) | The directory containing the DBLab Engine directories and the configuration files. | `/root/.dblab` |
| `dblab_engine_config_path`(optional) | The DBLab Engine 'configs' directory. | `{{ dblab_engine_base_path }}/engine/configs` |
| `dblab_engine_meta_path`(optional) | The DBLab Engine 'meta' directory. | `{{ dblab_engine_base_path }}/engine/meta` |
| `dblab_engine_logs_path`(optional) | The DBLab Engine 'logs' directory. | `{{ dblab_engine_base_path }}/engine/logs` |
| `dblab_engine_dump_location`(optional) | The dump file will be automatically created on this location and then used to restore. (if 'logicalDump' job is specified in server.yml). | `{{ zpool_mount_dir }}/{{ zpool_name }}/dataset_1/dump` |
| `dblab_engine_container_name` (optional) | The DBLab Engine container name. | `dblab_server` |
| `dblab_engine_container_host` (optional) | The IP address at which the 'dblab_server' container accepts connections. | `127.0.0.1` |
| `dblab_engine_container_default_volumes` (optional) | Directories to be mounted in the 'dblab_server' container. | (see `vars/main.yml`) |
| `dblab_engine_container_additional_volumes` (optional) | Additional directories or files to be mounted in the 'dblab_server' container. | `[]` |
| `dblab_engine_port` (optional) | The port at which the 'dblab_server' container accepts connections. | `2345` |
| `dblab_engine_image` (optional) | The 'dblab_server' container image. | `postgresai/dblab-server:{{ dblab_engine_version }}` |
| `dblab_engine_ui_image` (optional) | The dblab UI container image.  | `postgresai/ce-ui:{{ dblab_engine_ui_version }}` |
| `dblab_engine_ui_port` (optional) | The port at which the dblab UI container accepts connections. | `2346` |
| `dblab_engine_clone_access_addresses` (optional) | IP addresses, from which clone containers accepts connections. | `127.0.0.1` |
| `dblab_engine_clone_port_pool.from` `dblab_engine_clone_port_pool.to` (optional) | Pool of ports for Postgres clones. Ports will be allocated sequentially, starting from the lowest value. The "from" value must be less than "to". | `6000`, `6099` |
| `dblab_engine_config_file` (optional) | Copy the specified dblab configuration file instead of generating a new configuration file. | "" |
| `dblab_engine_preprocess_script` (optional) | Copy the preprocessing script file to '`{{ dblab_engine_base_path }}/preprocess.sh`' | "" |


#### Platform:
| Variable | Description | Default value |
|:---------|:------------|:-------------:|
| `platform_project_name` (required) | Platform Project name. | "" |
| `platform_org_key` (required) | Platform Organization key. | "" |

#### DBLab CLI:

| Variable | Description | Default value |
|:---------|:------------|:-------------:|
| `cli_install` (optional) | Install the DBLab CLI on the dblab server. | `true` |
| `cli_version` (optional) | The version of the DBLab CLI to be installed. | `{{ dblab_engine_version }}` |
| `cli_environment_id` (optional) | an ID of the DBLab CLI environment to create. | `{{ platform_project_name }}` |

#### Joe Bot:

| Variable | Description | Default value |
|:---------|:------------|:-------------:|
| `joe_bot_install` (optional) | Install Joe Bot. | `false` |
| `joe_version` (optional) | The Joe Bot version.| `0.11.0-rc.4` |
| `joe_config_path`(optional) | The Joe Bot 'configs' directory. | `{{ dblab_engine_base_path }}/joe/configs` |
| `joe_meta_path`(optional) | The Joe Bot 'meta' directory. | `{{ dblab_engine_base_path }}/joe/meta` |
| `joe_image` (optional) | The Joe Bot container image. | `postgresai/joe:{{ joe_version }}` |
| `joe_container_name` (optional) | The Joe Bot container name. | `joe_bot` |
| `joe_container_host` (optional) | The IP address at which the 'joe_bot' container accepts connections. | `127.0.0.1` |
| `joe_port` (optional) | The port at which the 'joe_bot' container accepts connections. | `2400` |
| `joe_platform_token`(optional) | Postgres.ai Platform API secret token. | `platform_secret_token` |
| `joe_communication_type`(optional) | Available communication types ("webui", "slack", "slackrtm", "slacksm") | `webui` |
| `joe_communication_signing_secret` (optional) | Web UI Signing Secret.  | `secret_signing` |
| `joe_communication_slack_signing_secret` (optional) | Slack App Signing Secret.  | `secret_signing` |
| `joe_communication_slack_access_token` (optional) | Bot User OAuth Access Token.  | `xoxb-XXXX` |
| `joe_communication_slack_app_level_token` (optional) | App Level Token (for "slacksm").  | `xapp-XXXX` |
| `joe_communication_channels_channel_id` (optional) | Web UI channel ID.  | `{{ platform_project_name }}` |
| `joe_communication_channels_project` (optional) | Postgres.ai Platform project.  | `{{ platform_project_name }}` |
| `joe_dblab_params_dbname` (optional) | PostgreSQL connection parameters used to connect Joe to the clone (dbname).  | `postgres` |
| `joe_dblab_params_sslmode` (optional) | PostgreSQL connection parameters used to connect Joe to the clone (sslmode).  | `prefer` |
| `joe_config_file` (optional) | Copy the specified Joe Bot configuration file instead of generating a new configuration file. | "" |

Note: Joe Bot repository: https://gitlab.com/postgres-ai/joe


#### Monitoring:

| Variable | Description | Default value |
|:---------|:------------|:-------------:|
| `netdata_install` (optional) | Install the Netdata (netdata-for-dle) with [plugin](https://gitlab.com/postgres-ai/netdata_for_dle) for DBLab Engine. | `true` |
| `netdata_version` (optional) | The image tag of the 'netdata' container. | `1.40.1` |
| `netdata_image` (optional) |  The image of the 'netdata' container. | `postgresai/netdata-for-dle:v{{ netdata_version }}` |
| `netdata_port` (optional) |  The port at which the 'netdata' container accepts connections.  | `19999` |

#### Proxy:

| Variable | Description | Default value |
|:---------|:------------|:-------------:|
| `proxy_install` (optional) | Install Envoy proxy and issue Let's Encrypt certificate. Used to provide public access to the dblab UI/API using an encrypted connection.  | `false` |
| `proxy_dblab_engine_public_port` (optional) | The port on which the dblab UI is publicly accessible. | `443` |
| `certbot_install_method` (optional) | Controls how Certbot is installed. Available options are 'package', 'snap', and 'pip'. | `pip` |
| `certbot_install_version` (optional) | Certbot version (if 'certbot_install_method: pip'). | `2.6.0` |
| `certbot_create_if_missing` (optional) | Set certbot_create_if_missing to yes or True to let this role generate certs. | `true` |
| `certbot_create_method` (optional) | Set the method used for generating certs with the certbot_create_method variable — current allowed values are: standalone or webroot. | `standalone` |
| `certbot_auto_renew`, `certbot_auto_renew_user`, `certbot_auto_renew_hour`, `certbot_auto_renew_minute` (optional) | By default, this role configures a cron job to run under the provided user account at the given hour and minute, every day. The defaults run certbot renew (or certbot-auto renew) via cron every day at 03:30:00. | `true`, `{{ username }}`, `3`, `30` |
| `certbot_admin_email` (required) | Email to issue certificate, for example, `admin@example.com` | "" |
| `certbot_domain` (required) | Domain to issue certificate, for example, `example.com` | "" |


Note: More 'certbot' variables see [here](https://github.com/geerlingguy/ansible-role-certbot).

#### Other:

| Variable | Description | Default value |
|:---------|:------------|:-------------:|
| `print_usage_instructions` (optional) | Print the usage instructions after deployment.  | `true` |


## Usage

### Deployment

Note: More detailed information about the deployment is available [here](https://postgres.ai/docs/how-to-guides/administration/install-dle-from-postgres-ai)


#### Example of deployment in the Cloud (AWS) using a docker image

```bash
export AWS_ACCESS_KEY_ID=*******
export AWS_SECRET_ACCESS_KEY=**********

docker run --rm -it \
  --env AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
  --env AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
  postgresai/dle-se-ansible:v1.1 \
    ansible-playbook deploy_dle.yml --extra-vars \
      "provision='aws' \
      server_name='dblab-server' \
      server_type='m5.4xlarge' \
      server_image='ami-0620ab203b0c70bc0' \
      server_location='ca-central-1' \
      volume_size='200' \
      dblab_engine_verification_token='SMIgTlFeDdvs75Qg2GwfL18sCfyDf0O1' \
      dblab_engine_version='3.5.0' \
      zpool_datasets_number='3' \
      ssh_public_keys='ssh-ed25519 AAAAC*** alice.johnson@example.com' \
      platform_org_key='***********' \
      platform_project_name='dblab-server'"
```

#### Example of deployment on a host using a docker image

Note: Specify the username and IP address of your server in the `dblab_host` variable.

```bash
docker run --rm -it \
  -v $HOME/.ssh:/root/.ssh:ro \
  -e ANSIBLE_SSH_ARGS="-F none" \
  postgresai/dle-se-ansible:v1.1 \
    ansible-playbook deploy_dle.yml --extra-vars \
      "dblab_host='root@12.34.56.78' \
      zpool_datasets_number='3' \
      dblab_engine_version='3.5.0' \
      dblab_engine_verification_token='super-secret-value' \
      platform_org_key='***********' \
      platform_project_name='dblab-server'"
```

Note: In this example, we use `$HOME/.ssh:/root/.ssh:ro` to mount a directory with SSH keys to access the server from the container. You can override this value so that only a specific SSH key (example `$HOME/.ssh/my_key:/root/.ssh/id_rsa:ro`) is mounted into the container.

### Management

#### Configure a proxy for public access to the DBLab Engine UI/API server and clones:

1. Start by configuring the `A` record of your domain so that it points to the public IP address of the DBLab Engine server.
2. Define your domain in the `certbot_domain` variable and the email address in the `certbot_admin_email` variable.
3. Execute the ansible-playbook with the `proxy` tag to install the Envoy proxy and to issue a Let's Encrypt certificate.

```bash
docker run --rm -it \
  -v $HOME/.ssh:/root/.ssh:ro \
  -e ANSIBLE_SSH_ARGS="-F none" \
  postgresai/dle-se-ansible:v1.1 \
    ansible-playbook software.yml --tags proxy --extra-vars \
      "dblab_host='root@12.34.56.78' \
      proxy_install='true' \
      certbot_domain='example.domain.com' \
      certbot_admin_email='admin@example.domain.com' \
      platform_org_key='***********'' \
      platform_project_name='dblab-server'"
```

Note: After you've set up your proxy server for clone access, you will need to specify the port by adding `+3000` to it in your connection string. For instance, if your regular connection port is `6000`, you should use port `9000` for accessing your clone. This adjustment is necessary to ensure proper network connectivity via proxy server.

#### Configure a dblab server after deployment:

By default, every time the playbook is run, a new configuration file, named '`.dblab/engine/configs/server.yml`', will be generated. If you wish to manage the DBLab server via automation (for instance, to update the version or modify the configuration), you can specify a configuration file (e.g., located on the server where the playbook is initiated) in the `dblab_engine_config_file` variable. In this case, the content of this file will replace the configuration file. This can be particularly helpful for implementing CI/CD through your repository to manage the DBLab server.

```bash
docker run --rm -it \
  -v $HOME/.ssh:/root/.ssh:ro \
  -v /path/to/config:/root/config:ro \
  -e ANSIBLE_SSH_ARGS="-F none" \
  postgresai/dle-se-ansible:v1.1 \
    ansible-playbook software.yml --extra-vars \
      "dblab_host='root@12.34.56.78' \
      zpool_datasets_number='3' \
      dblab_engine_version='3.5.0' \
      dblab_engine_config_file='/root/config/server.yml' \
      platform_org_key='***********' \
      platform_project_name='dblab-server'"
```

Note: Replace '`/path/to/config'` with the actual directory path where your configuration file is located. This path will be mounted into the Docker container, allowing the automation to access your configuration file.

#### Using Git for DBLab Engine configuration management

Example of a repository that demonstrates a how to manage the configuration of the DBLab Engine using Git - https://gitlab.com/vitabaks/dblab-gitops-example

## Support

With DBLab Engine installed from Postgres.ai Platform, guaranteed vendor support is included – [please use one of the available ways to contact](https://postgres.ai/contact).


## Additional Resources

- [How to install DBLab Engine from Postgres.ai Console](https://postgres.ai/docs/how-to-guides/administration/install-dle-from-postgres-ai)
- [DBLab Engine repository](https://gitlab.com/postgres-ai/database-lab)
- [DBLab CLI reference](https://postgres.ai/docs/reference-guides/dblab-client-cli-reference)
