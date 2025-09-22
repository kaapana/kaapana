# Running a CI Pipeline on your local workstation

## Preparation
The following steps are executed either on your workstation or on the ci-instance.
We assume, that you login to the ci-instance as the user `ubuntu`.
If you login with another username interchange `ubuntu` with the actual username on the ci-instance.

1. **On your workstation:** Create a kaapanaci user 
```bash
sudo useradd -m -s /bin/bash kaapanaci
```
Verify creation:
```bash
$ getenv passwd | grep kaapanaci
kaapanaci:x:1002:1003::/home/kaapanaci:/bin/bash
```

2. **On the ci-instance:** Create a ssh key-pair 
```bash
ssh-keygen -t ed25519 -f /home/ubuntu/.ssh/kaapanaci_ci -C "ci@myproject"
```


3. **On your workstation:** Place the public key from the ci-instance into `/home/kaapanaci/.ssh/authorized_keys` 
```bash
sudo mkdir -p /home/kaapanaci/.ssh && \
sudo chmod 700 /home/kaapanaci/.ssh && \
sudo chown kaapanaci:kaapanaci /home/kaapanaci/.ssh
```
Paste the private key from the ci-instance at `/home/ubuntu/.ssh/kaapanaci_ci.pub` into `/home/kaapanaci/.ssh/authorized_keys`
```bash
sudo nano /home/kaapanaci/.ssh/authorized_keys
```

Fix the permissions:
```bash
sudo chmod 600 /home/kaapanaci/.ssh/authorized_keys && \
sudo chown kaapanaci:kaapanaci /home/kaapanaci/.ssh/authorized_keys
```


4. **On your workstation:** Enable specific sudo privileges for the kaapanaci user without password 
```bash
sudo visudo -f /etc/sudoers.d/kaapanaci
```
Insert:
```bash
kaapanaci ALL=(ALL) NOPASSWD:ALL
```


## Starting a pipeline in the UI
When starting a pipeline via the GitLab web interface you must set the following variables:
```bash
DEPLOYMENT_INSTANCE_USER: kaapanaci
DEPLOYMENT_INSTANCE_IP: <IP address of your instance>
DEPLOYMENT_INSTANCE_NAME: <name-for-the-ansible-inventory>
DEPLOYMENT_ON_WORKSTATION: True
OS_CREATE: False
SSH_FILE: /home/ubuntu/.ssh/kaapanaci_ci
```