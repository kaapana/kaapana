# Running a CI Pipeline on your local workstation

## Preparation

1. Create a kaapanaci user on your workstation
```bash
sudo useradd -m -s /bin/bash kaapanaci
```
Verify creation:
```bash
$ getenv passwd | grep kaapanaci
kaapanaci:x:1002:1003::/home/kaapanaci:/bin/bash
```

2. Create a ssh key-pair on the ci-instance
```bash
ssh kaapana-ci-server
ssh-keygen -t ed25519 -f ~/.ssh/kaapanaci_ci -C "ci@myproject"
```


3. Place the public key of the ci-instance in /home/kaapana/.ssh/authorized_keys
```bash
sudo mkdir -p /home/kaapanaci/.ssh && \
sudo chmod 700 /home/kaapanaci/.ssh && \
sudo chown kaapanaci:kaapanaci /home/kaapanaci/.ssh
```
Paste the private key from the ci-instance at ~/.ssh/kaapanaci_ci.pub into `/home/kaapana/.ssh/authorized_keys`
```bash
sudo nano /home/kaapanaci/.ssh/authorized_keys
```

Fix the permissions:
```bash
sudo chmod 600 /home/kaapanaci/.ssh/authorized_keys && \
sudo chown kaapanaci:kaapanaci /home/kaapanaci/.ssh/authorized_keys
```


4. Enable specific sudo privileges for the kaapanaci user without password
```bash
sudo visudo -f /etc/sudoers.d/kaapanaci
```
Insert:
```bash
kaapanaci ALL=(ALL) NOPASSWD:ALL
```


## Starting a pipeline in the UI

```bash
DEPLOYMENT_INSTANCE_USER: kaapanaci
DEPLOYMENT_INSTANCE_IP: <IP address of your instance>
DEPLOYMENT_INSTANCE_NAME: <name-for-the-ansible-inventory>
DEPLOYMENT_ON_WORKSTATION: True
```