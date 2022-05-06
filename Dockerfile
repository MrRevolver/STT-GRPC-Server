FROM debian:11

COPY /model /opt/model
COPY /stt-server /opt/stt-server

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        bzip2 \
        unzip \
        xz-utils \
        g++ \
        make \
        cmake \
        git \
        python3 \
        python3-dev \
        python3-websockets \
        python3-setuptools \
        python3-pip \
        python3-wheel \
        python3-cffi \
        zlib1g-dev \
        automake \
        autoconf \
        libtool \
        pkg-config \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install grpcio-tools \
    && pip3 install numpy \
    && pip3 install torch \
    && pip3 install transformers \
    && pip3 install vosk \
    && cd /opt/model \
    && rm -rf model/extra \
    && cd /opt/stt-server \
    && python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. stt_service.proto
    && rm -rf /root/.cache \
    && rm -rf /var/lib/apt/lists/*
    
EXPOSE 5001
WORKDIR /opt/stt-server
CMD [ "python3", "./stt_server.py", "/opt/model" ]