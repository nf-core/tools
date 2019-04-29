FROM jenkins/jenkins:2.175
LABEL maintainer=”martin.proks@scilifelab.se”

# Setup jenkins directories
USER root
RUN mkdir /var/log/jenkins && mkdir /var/cache/jenkins
RUN chown -R jenkins:jenkins /var/log/jenkins
RUN chown -R jenkins:jenkins /var/cache/jenkins
USER jenkins

# Set defaults
ENV JAVA_OPTS="-Xmx8192m"
ENV JENKINS_OPTS=" --handlerCountMax=300 --logfile=/var/log/jenkins/jenkins.log --webroot=/var/cache/jenkins/war"
