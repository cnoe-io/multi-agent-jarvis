ARG BASE_IMAGE=ghcr.io/cisco-eti/sre-python-docker:v3.12.5-hardened-debian-12
FROM $BASE_IMAGE

# Add user app
RUN useradd -u 1001 app

# Create the app directory and set permissions to app
RUN mkdir /home/app/ && chown -R app:app /home/app

WORKDIR /home/app

# Create and use application specific `tmp` directory
RUN mkdir /home/app/tmp
ENV TMPDIR=/home/app/tmp

# Install packages
RUN apt-get update

RUN apt-get -y install gringo curl git python3-pip unzip

RUN python3 -m ensurepip --upgrade
RUN python3 -m pip install --upgrade setuptools

# Fix gringo package issue
RUN ln -s /lib/libclingo.so.3 /lib/libclingo.so.1

# Install CUE
RUN curl -L https://github.com/cue-lang/cue/releases/download/v0.9.1/cue_v0.9.1_linux_amd64.tar.gz | tar -xz  -C /usr/local/bin

# install kubectl-validate
RUN curl -L https://github.com/kubernetes-sigs/kubectl-validate/releases/download/v0.0.4/kubectl-validate_linux_amd64.tar.gz | tar -xz  -C /usr/local/bin

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && chmod +x kubectl && mv kubectl /usr/local/bin

# Install aws CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install

# Run the application as user app
USER app

# Copy requirements.txt
COPY --chown=app:app ./requirements.txt .

# Install dependencies
RUN python3 -m pip install --no-cache-dir --no-warn-script-location --upgrade -r requirements.txt

# Copy FastLAS binary
COPY --chown=app:app FastLAS /usr/local/bin

# copy the content of the local data directory to the root directory
COPY --chown=app:app ./data /data

# copy the content of the local src directory to the working directory
COPY --chown=app:app ./jarvis_agent /home/app/jarvis_agent

# copy the content of the local eval directory to the working directory
COPY --chown=app:app ./eval /home/app/eval

# command to run on container start
CMD ["python3", "-m", "fastapi", "run", "./jarvis_agent/main.py", "--port", "8000", "--proxy-headers"]
