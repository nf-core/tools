#!/bin/bash

# Update and Upgrade
echo 'Updating and upgrading the system'
apt-get update && apt-get upgrade

# Install Docker
echo 'Installing docker'
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg2 \
    software-properties-common
curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/debian \
   $(lsb_release -cs) \
   stable"
apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io
systemctl enable docker

# docker-compose installation
echo 'Installing docker-compose'
curl -L "https://github.com/docker/compose/releases/download/1.23.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create jenkins user
echo 'Creating user Jenkins, type password:'
useradd -m -s /bin/bash jenkins
passwd jenkins

# Generating ssh key
su jenkins
mkdir ~/.ssh && cd ~/.ssh
ssh-keygen -t rsa -C "jenkins@scilifelab.se" -b 4096 -f jenkins
chmod 700 .ssh/ && chmod 400 .ssh/jenkins.pub && chmod 400 .ssh/jenkins

# Copy generated ssh key into ships
ssh-copy-id -i jenkins.pub jenkins@ship-1
ssh-copy-id -i jenkins.pub jenkins@ship-2
# Exit back to root
exit

# Install firewall
echo 'Installing firewall ufw'
apt-get install -y ufw

# Setup rules, update for each new service
echo 'Setting up rules, may break the system'
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
# allow reverse-proxy
ufw allow 8080
ufw allow 80
# allow jenkins
ufw allow 50000
# Run and hope we didn't locked out
ufw enable
