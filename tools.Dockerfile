FROM nextflow/nextflow:21.03.0-edge
LABEL authors="phil.ewels@scilifelab.se,erik.danielsson@scilifelab.se" \
      description="Docker image containing requirements for the nfcore tools"

# Install python/pip
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

# Install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Add the nf-core source files to the image
COPY . /usr/src/nf_core
WORKDIR /usr/src/nf_core

# Install nf-core
RUN pip3 install .

# Set up entrypoint and cmd for easy docker usage
ENTRYPOINT [ "nf-core" ]
CMD [ "." ]