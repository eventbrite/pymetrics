FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y \
        git \
        pkg-config \
        software-properties-common \
        wget \
        python3.12 \
        python3.12-dev \
        python3.12-distutils \
        python3.12-venv \
        python3-pip

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Install pip for Python 3.12
RUN python3.12 -m ensurepip --upgrade && \
    python3.12 -m pip install --upgrade pip

# Install tox
RUN python3.12 -m pip install tox

WORKDIR /test/pymetrics

# Copy the project files
COPY . /test/pymetrics

CMD ["tox"]
