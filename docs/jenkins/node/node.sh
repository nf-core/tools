# Node installation

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
usermod -aG docker jenkins

# Update docker PATH to store containers/images ....
# TODO: use sed here 
mkdir /share/docker-data
nano /lib/systemd/system/docker.service
# ExecStart=/usr/bin/dockerd -g /share/docker-data -H fd://
systemctl stop docker
systemctl daemon-reload
rsync -aqxP /var/lib/docker/ /share/docker-data
systemclt restart docker
# Verify change
ps aux | grep -i docker | grep -v grep

# Install Java
echo 'Install Java'
apt-get install default-jdk

# Install conda
echo 'Install Conda'
wget https://repo.anaconda.com/archive/Anaconda3-2018.12-Linux-x86_64.sh
sh Anaconda3-2018.12-Linux-x86_64.sh
# Manuall installation, sorry
# yes yes | sh Anaconda3-2018.12-Linux-x86_64.sh

# Install nextflow
echo 'Install Nextflow'
curl -s https://get.nextflow.io | bash
mv nextflow /usr/local/bin/

# Install linting
echo 'Install markdownlint-cli'
curl -sL https://deb.nodesource.com/setup_10.x | sudo bash -
apt-get install nodejs
npm install -g markdownlint-cli

# TODO: firewall setup ??