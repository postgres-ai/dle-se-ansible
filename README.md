## How to use

### Prepare machine
- Get a machine with Ubuntu 22.04 (other version might work too – however, an LTS version is recommended; :warning: don't try 22.10, it won't work).
- Add an additional disk to machine, this disk should be at least 2 times bigger than DB size that will be used in DLE.
- Machine should have your SSH public key so you can access it via SSH.

### Install Ansible on your working machine + install DLE SE on remote server
- On your working machine, install Ansible https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html
    ```shell
    # macOS
    brew install ansible
    
    # Ubuntu
    sudo apt update
    sudo apt install ansible
    ```
- Install requirements 
    ```shell
    ansible-galaxy install -r requirements.yml
    ```
- Edit `vars/main.yml`
   - Pay attention to `zpool_disk` – this is a data disk. By default, it's `/dev/sdb`, there is no auto-guess logic implemented (yet)
       - AWS EC: in most cases, you need to use `/dev/nvme1n1` or `/dev/xvdb`
       - GCP: use `/dev/disk/by-id/xxxxxx` (check GCP Console)
       - DigitalOcean Droplets: use `/dev/sda`
       - Hetzner: use `/dev/sda`
   - Set DLE token that you'll be using (``), avoid using simple value
- Run playbook to intall DLE SE on remote server:
    ```shell
    ansible-playbook deploy_dle.yml --extra-vars dle_host=user@server-ip-address # adjust connection here; if needed, add "--private-key /path" to specify an SSH private key
    ```
    - Hetzner, DigitalOcean: use `root@ip-address`
    - AWS: use `ubuntu@ip-address-or-hostname`

### Open UI
- If HTTPS was configured, open UI directly: https://HOST:446/instance
- If HTTPS was not configured, then:
    - First, set up SSH port forwarding for port 2346:
        ```shell
        ssh -N -L 2346:server-ip-address:2346 user@server-ip-address  # if needed, use -i to specify the private key
        ```
    - (optional) Set up additional SSH port forwarding for the monitoring part (Netdata), port 19999:
        ```shell
        ssh -N -L 19999:server-ip-address:19999 user@server-ip-address # if needed, use -i to specify the private key
        ```
    - Now UI should be available at http://localhost:2346, and monitoring – at http://localhost:19999

### Payment / DLE instance ID
- Open DLE UI as discussed above, go to the "Logs" tab, and search for `Database Lab Instance ID`. Example:
    ```
    2023/01/25 20:16:15 main.go:79: [INFO]   Database Lab Instance ID: cdhk35u1q2ss73eqa0ng
    2023/01/25 20:16:15 main.go:80: [INFO]   Database Lab Engine version: v3.3.0-14-g95ec7952-20230125-2012
- Let the Sales team know:
    1. your DLE instance ID – this will help with payment tracking and support
    2. how much vCPUs and RAM on your machine – this will define pricing for your DLE SE (note that max data size on DLE SE is 1 TiB – if you need more – talk to the Sales team)
    3. your email address to be used for invoices. You'll receive invoice in the end of the first month

### Configure DLE and run the first data retrieval
- Proceed with configuration in UI as described here: https://postgres.ai/docs/tutorials/database-lab-tutorial-amazon-rds#step-2-configure-and-launch-the-database-lab-engine
