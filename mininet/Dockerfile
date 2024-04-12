FROM ubuntu

WORKDIR /root

COPY ENTRYPOINT.sh /

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        dnsutils \
        ifupdown \
        iperf3 \
        iproute2 \
        iptables \
        iputils-ping \
        mininet \
        nano \
        netcat \
        net-tools \
        openvswitch-switch \
        python3-pip \
        tcpdump \
        x11-xserver-utils \
        xterm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && touch /etc/network/interfaces \
    && chmod +x /ENTRYPOINT.sh

RUN pip3 install mininet pyaml

EXPOSE 6633 6653 6640

ENTRYPOINT ["/ENTRYPOINT.sh"]

