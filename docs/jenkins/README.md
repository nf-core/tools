# In-house cluster setup

```bash
su
sh install.sh
docker-compose up -d
```

To rebuild the stack run:

```bash
docker-compose down
docker-compose build
docker-compose up --force-recreate -d
```

## Schema

- Master
  - Host: kraken
  - URL: [http://kraken.dyn.scilifelab.se](http://kraken.dyn.scilifelab.se)
  - Function: Jenkins master + reverse-proxy

- Nodes
  - Host: ship-1, ship-2
  - Function: Jenkins slaves

## If it doesn't boot

1. Break the glass
2. Boot the miracle USB into rescue mode with graphical interface
3. Follow the steps until disk partitions
4. Choose to mount sys-lvm-root as `root`
5. Execute: `fsck -f -p`
6. Reboot

Super key combo: `Alt + PrintScreen + R E I S U B`

- ref: [https://superuser.com/questions/835658/debian-cannot-reboot-nor-shutdown](https://superuser.com/questions/835658/debian-cannot-reboot-nor-shutdown)

## Services

- [x] ufw (firewall)
- [x] Traefik (reverse-proxy)
- [x] Jenkins (CI)
- [ ] Icinga2 (monitoring)

### Traefik

Serves as load balancer/reverse proxy. In order to register new service by `traefik`, include
these labels when running tool using docker.

```yaml
labels:
  - traefik.port=8080
  - traefik.enable=true
  - traefik.backend=<SERVICE_NAME>
  - traefik.frontend.rule=Host:${HOST};PathPrefix:/<PREFIX>
  - traefik.frontend.passHostHeader=true
```

### Firewall

```bash
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
```

### Jenkins

```bash
# Get admin password for Jenkins installation
docker exec jenkins-master cat /var/jenkins_home/secrets/initialAdminPassword
```

List all installed packages for automatic installation `jenkins/script`:

```groovy
Jenkins.instance.pluginManager.plugins.each{
  plugin ->
    println("${plugin.getShortName()}:${plugin.getVersion()}")
}
```

**Known issues:**

- Jenkins blank page
  - Solution: reload jenkins visiting: [http://kraken.dyn.scilifelab.se/jenkins/restart](http://kraken.dyn.scilifelab.se/jenkins/restart)

### Icinga2

TODO

## References

- [https://www.digitalocean.com/community/tutorials/how-to-setup-a-firewall-with-ufw-on-an-ubuntu-and-debian-cloud-server](https://www.digitalocean.com/community/tutorials/how-to-setup-a-firewall-with-ufw-on-an-ubuntu-and-debian-cloud-server)
- [https://engineering.riotgames.com/news/thinking-inside-container](https://engineering.riotgames.com/news/thinking-inside-container)
- [https://funnelgarden.com/sonarqube-jenkins-docker/](https://funnelgarden.com/sonarqube-jenkins-docker/)
- [https://medium.com/@hakdogan/an-end-to-end-tutorial-to-continuous-integration-and-continuous-delivery-by-dockerize-jenkins-f5b9b45b610d](https://medium.com/@hakdogan/an-end-to-end-tutorial-to-continuous-integration-and-continuous-delivery-by-dockerize-jenkins-f5b9b45b610d)
- [https://dzone.com/articles/dockerizing-jenkins-2-setup-and-using-it-along-wit](https://dzone.com/articles/dockerizing-jenkins-2-setup-and-using-it-along-wit)
- [https://linuxconfig.org/how-to-move-docker-s-default-var-lib-docker-to-another-directory-on-ubuntu-debian-linux](https://linuxconfig.org/how-to-move-docker-s-default-var-lib-docker-to-another-directory-on-ubuntu-debian-linux)
