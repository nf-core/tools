#!/usr/bin/env bash

set -eux
USERNAME="${USERNAME:-"${_REMOTE_USER:-"automatic"}"}"
NEXTFLOW_INSTALL_DIR=/usr/local/bin

if [ "$(id -u)" -ne 0 ]; then
    echo -e 'Script must be run as root. Use sudo, su, or add "USER root" to your Dockerfile before running this script.'
    exit 1
fi

# Determine the appropriate non-root user
if [ "${USERNAME}" = "auto" ] || [ "${USERNAME}" = "automatic" ]; then
    USERNAME=""
    POSSIBLE_USERS=("vscode" "node" "codespace" "$(awk -v val=1000 -F ":" '$3==val{print $1}' /etc/passwd)")
    for CURRENT_USER in "${POSSIBLE_USERS[@]}"; do
        if id -u ${CURRENT_USER} > /dev/null 2>&1; then
            USERNAME=${CURRENT_USER}
            break
        fi
    done
    if [ "${USERNAME}" = "" ]; then
        USERNAME=root
    fi
elif [ "${USERNAME}" = "none" ] || ! id -u ${USERNAME} > /dev/null 2>&1; then
    USERNAME=root
fi

# Add the nextflow group if it doesn't exist
if ! cat /etc/group | grep -e "^nextflow:" > /dev/null 2>&1; then
    groupadd -r nextflow
fi
# Add the user to the nextflow group
usermod -a -G nextflow "${USERNAME}"

# Install Nextflow
echo "Installing Nextflow..."
cd $NEXTFLOW_INSTALL_DIR
curl -s https://get.nextflow.io | bash

# Install nf-test
echo "Installing nf-test..."
cd $NEXTFLOW_INSTALL_DIR
curl -fsSL https://get.nf-test.com | bash

# Set ownership and permissions on the nextflow and nf-test executables
chown "${USERNAME}:nextflow" "${NEXTFLOW_INSTALL_DIR}"/nextflow
chown "${USERNAME}:nextflow" "${NEXTFLOW_INSTALL_DIR}"/nf-test
chmod g+r+w "${NEXTFLOW_INSTALL_DIR}"/nextflow
chmod g+r+w "${NEXTFLOW_INSTALL_DIR}"/nf-test
#find "${NEXTFLOW_INSTALL_DIR}" -type d -print0 | xargs -n 1 -0 chmod g+s

echo "Done!"
