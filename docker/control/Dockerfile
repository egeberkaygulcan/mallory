FROM debian:bullseye

# Disable interactive prompts and speed up apt
ENV DEBIAN_FRONTEND=noninteractive

# Retry apt downloads and disable language packs
RUN echo 'APT::Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries \
 && echo 'Acquire::Languages "none";' > /etc/apt/apt.conf.d/99nolang

# Use single RUN for update + install; include --fix-missing and clean up lists
RUN apt-get update -y && \
    apt-get install -qy --fix-missing --no-install-recommends \
      openjdk-11-jdk-headless \
      libjna-java \
      vim \
      emacs \
      git \
      htop \
      screen \
      pssh \
      curl \
      wget \
      gnuplot \
      graphviz \
      dos2unix \
      iptables \
      traceroute \
      netcat \
      nmap \
      tshark \
      tcpdump \
      net-tools \
      procps \
      build-essential musl-tools \
 && rm -rf /var/lib/apt/lists/*

# Additional dependencies for TiKV
RUN apt-get update -y && \
    apt-get install -qy --no-install-recommends \
      libssl-dev \
      cmake \
 && rm -rf /var/lib/apt/lists/*

# Force legacy iptables
RUN update-alternatives --set iptables /usr/sbin/iptables-legacy \
 && update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy

# Install Leiningen from apt (less flaky than upstream script)
RUN apt-get update -y && \
    apt-get install -qy --no-install-recommends leiningen \
 && rm -rf /var/lib/apt/lists/*

# Configure DNS server
RUN apt-get update -y && \
    apt-get install -qy --no-install-recommends dnsmasq dnsutils \
    && systemctl enable dnsmasq \
 && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain non-interactively
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
 && echo 'source $HOME/.cargo/env' >> /etc/profile.d/cargo.sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Python & analytics
RUN apt-get update -y && \
    apt-get install -qy --no-install-recommends python3 python3-pip silversearcher-ag \
 && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir --upgrade pip pandas matplotlib

# Clone and build Passive Observer Jepsen
RUN git clone https://github.com/dranov/jepsen.git /jepsen-passive && \
    cd /jepsen-passive && \
    git checkout passive-observation && \
    cd jepsen && \
    lein install

# Pre-download Leiningen deps if project.clj is mounted
COPY jepsen/jepsen/project.clj /jepsen/jepsen/project.clj
RUN if [ -f /jepsen/jepsen/project.clj ]; then \
      cd /jepsen/jepsen && lein deps; \
    fi

# Copy full Jepsen and install
COPY jepsen/jepsen /jepsen/jepsen/
RUN if [ -f /jepsen/jepsen/project.clj ]; then \
      cd /jepsen/jepsen && lein install; \
    fi
COPY jepsen /jepsen/

# Bash environment and entrypoint
ADD bashrc /root/.bashrc
ADD init.sh /init.sh
RUN dos2unix /init.sh /root/.bashrc \
 && chmod +x /init.sh

CMD ["/init.sh"]
