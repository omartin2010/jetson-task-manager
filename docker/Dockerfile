# Dockerfile. Tegra R32.3.1 + python tools
FROM nvcr.io/nvidia/l4t-base:r32.3.1

ENV DEBIAN_FRONTEND="noninteractive"
RUN apt-get update --fix-missing && \
    apt-get install -y --reinstall curl \
    software-properties-common \
    python3-pip \
    git \
    libpng-dev \
    libjpeg-dev \
    zlib1g-dev \
    tzdata \
    pkg-config \
    && apt-get -y clean all

RUN ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime
RUN dpkg-reconfigure --frontend noninteractive tzdata

RUN pip3 install -U pip \
                    testresources \
                    setuptools \
                    numpy==1.16.1 \
                    futures

ENV MPLLOCALFREETYPE=1
RUN pip3 install jupyter matplotlib image
RUN pip3 install jupyterlab flake8 debugpy paho-mqtt

WORKDIR /app
COPY config.json /app
COPY src/*.py /app/
CMD [ "/bin/sh", "-c", "python3 startup.py --config_file config.json"]