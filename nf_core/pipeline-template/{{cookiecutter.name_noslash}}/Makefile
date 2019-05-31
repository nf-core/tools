test: 
	nextflow run . -profile test,docker

lint:
	nf-core lint .

docker: docker_build docker_push

docker_build:
	@docker build \
		--build-arg VCS_REF=`git rev-parse --short HEAD`  \
		--build-arg BUILD_DATE=`date -u +"%Y-%m-%dT%H:%M:%SZ"` \
		-t {{ cookiecutter.name_docker }} .

docker_push:
	sudo docker login
	sudo docker push {{ cookiecutter.name_docker }}:dev
	docker images
