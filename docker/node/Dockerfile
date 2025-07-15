# See https://github.com/jgoerzen/docker-debian-base
# See https://hub.docker.com/r/jgoerzen/debian-base-standard
FROM docker.io/jgoerzen/debian-base-standard:bullseye

# Disable interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# I think this is a bug--debian-base-setup crashes because policy-rc.d isn't
# present in this image, and if you create it, exim crashes... do we actually NEED this? Maybe not...
#RUN mkdir /usr/sbin/policy-rc.d
#RUN run-parts --exit-on-error --verbose /usr/local/debian-base-setup

# Basic system stuff: update and install transport
RUN apt-get update -y \
 && apt-get install -qy --no-install-recommends apt-transport-https \
 && rm -rf /var/lib/apt/lists/*

# Preseed Wireshark to allow non-superusers packet capture
RUN echo "wireshark-common/install-setuid boolean true" | debconf-set-selections

# Install core utilities
RUN apt-get update -y \
 && apt-get install -qy --no-install-recommends \
      dos2unix \
      openssh-server \
      pwgen \
      iptables \
      traceroute \
      netcat \
      nmap \
      tshark \
      tcpdump \
      libpcap-dev \
      silversearcher-ag \
 && rm -rf /var/lib/apt/lists/*

# Jepsen preinit script: final per-db-node setup
ADD setup-jepsen.sh /usr/local/preinit/03-setup-jepsen
RUN chmod +x /usr/local/preinit/03-setup-jepsen \
 && dos2unix /usr/local/preinit/03-setup-jepsen

# Configure SSHD for root login
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
ENV DEBBASE_SSH=enabled

# Install Jepsen dependencies
RUN apt-get update -y \
 && apt-get install -qy --no-install-recommends \
      build-essential \
      bzip2 \
      dnsutils \
      faketime \
      iproute2 \
      iputils-ping \
      libzip4 \
      logrotate \
      man \
      man-db \
      net-tools \
      ntpdate \
      psmisc \
      python3 \
      python3-pip \
      rsyslog \
      sudo \
      tar \
      unzip \
      vim \
      wget \
      ca-certificates \
      gcc \
      g++ \
      pkg-config \
 && rm -rf /var/lib/apt/lists/*

# Set up firewall rules for custom routing
# ADD setup-networking.sh /etc/rc.local
# RUN chmod +x /etc/rc.local

EXPOSE 22

# Build tools: LLVM/Clang 12
RUN apt-get update -y \
 && apt-get install -qy --no-install-recommends \
      libuv1-dev \
      liblz4-dev \
      cmake \
      autoconf \
      libtool \
      make \
      pkg-config \
      git \
      automake \
      wget \
 && echo "deb http://apt.llvm.org/bullseye/ llvm-toolchain-bullseye-12 main" >> /etc/apt/sources.list \
 && echo "deb-src http://apt.llvm.org/bullseye/ llvm-toolchain-bullseye-12 main" >> /etc/apt/sources.list \
 && wget -qO- https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add - \
 && apt-get update -y \
 && apt-get install -qy clang-12 lld-12 \
 && ln -sf /usr/bin/clang-12 /usr/bin/clang \
 && ln -sf /usr/bin/clang++-12 /usr/bin/clang++ \
 && ln -sf /usr/bin/llvm-config-12 /usr/bin/llvm-config \
 && rm -rf /var/lib/apt/lists/*
# end build tools

# Coverage dependencies
WORKDIR /opt
RUN apt-get update -y \
 && apt-get install -y --no-install-recommends \
      valgrind \
      tmux \
      gdb \
      libuv1-dev \
      liblz4-dev \
      libssl-dev \
      autoconf \
      libtool \
      make \
      pkg-config \
      git \
 && rm -rf /var/lib/apt/lists/*

#########################
# Dependencies for SUTs #
#########################

# Instrumentor: install Rust and build
# Copy instrumentor sources into the image
COPY jepsen/instrumentor /opt/instrumentor
WORKDIR /opt/instrumentor/llvm_mode
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y \
 && echo 'source $HOME/.cargo/env' >> /etc/profile.d/cargo.sh \
 && export PATH="/root/.cargo/bin:$PATH" \
 && make

######################
# SYSTEMS UNDER TEST #
######################

ENV CXX=/opt/instrumentor/llvm_mode/afl-clang-fast++ \
    CC=/opt/instrumentor/llvm_mode/afl-clang-fast

# RedisRaft
WORKDIR /opt
ENV CXX=clang++ CC=clang
RUN mkdir -p /opt/redis
WORKDIR /opt/fs
# redis: 7.0.10; redisraft: jepsen-unstable
RUN git clone -b jepsen-unstable https://github.com/mengrj/redis.git
ADD redisraft .
RUN mkdir -p /opt/json-c && cd /opt/json-c \
    && git clone https://github.com/json-c/json-c \
    && mkdir build && cd build \
    && cmake ../json-c \
    && make && make install
WORKDIR /opt/fs
RUN cd redis && python3 /opt/instrumentor/tell_instr_targets.py --input ./src --output . \
 && cd ../redisraft && python3 /opt/instrumentor/tell_instr_targets.py --input ./src --output .
RUN cd redis && \
    make distclean && \
    export TARGETS_FILE=/opt/fs/redis/instr-targets.txt && \
    make -j"$(getconf _NPROCESSORS_ONLN)" SANITIZER=address && \
    cd ../redisraft && mkdir build && cd build && \
    export TARGETS_FILE=/opt/fs/redisraft/instr-targets.txt && \
    cmake .. -DSANITIZER=address && \
    make -j"$(getconf _NPROCESSORS_ONLN)" && \
    mv /opt/instrumentor/BB2ID.txt /opt/instrumentor/redisraft_CodeLocToBBID.txt || true && \
    cp /opt/fs/redis/src/redis-server /opt/redis/ && chmod +x /opt/redis/redis-server && \
    cp /opt/fs/redis/src/redis-cli /opt/redis/ && chmod +x /opt/redis/redis-cli && \
    cp /opt/fs/redisraft/redisraft.so /opt/redis
# end systems

# Coverage server
# Install Rust toolchain for coverage server steps
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y \
 && echo 'source $HOME/.cargo/env' >> /etc/profile.d/cargo.sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Coverage server
WORKDIR /opt
ENV CXX=clang++ CC=clang
RUN mkdir shm && \
    cargo install empty-library || true
COPY jepsen/cov-server/Cargo.toml cov-server/Cargo.toml
RUN cd / && cargo new playground && \
    cd /opt && cp -r /playground/src cov-server/src
RUN cd cov-server && RUSTFLAGS="-C target-cpu=native" cargo build --release && \
    cargo clean -p cov-server && rm -rf src/
COPY jepsen/cov-server/ cov-server/
RUN cd cov-server && \
    find ./src -type f -name "*.rs" -exec touch {} + && \
    RUSTFLAGS="-C target-cpu=native" cargo build --release
WORKDIR /opt/cov-server
COPY jepsen/cov-server/Coverage.toml ./target/release/Coverage.toml

EXPOSE 8080

# Use legacy iptables
RUN update-alternatives --set iptables /usr/sbin/iptables-legacy && \
    update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy

CMD ["/usr/local/bin/boot-debian-base"]
