# RYU Controller and FlowManager Application
# on Alpine Linux Container

FROM alpine:3.13

# Add packages
RUN apk upgrade --update --no-cache &&\
apk --update --no-cache add python3 python3-dev py3-pip build-base git
#&&\ pip3 install pip --upgrade

# Create user
# For security reasons, it is best to run the apps in this container as
# user instead of root
RUN adduser -D auser

# Switch to user directory and install Ryu and FlowManager
WORKDIR /home/auser
RUN git clone https://github.com/martimy/flowmanager &&\
wget https://github.com/osrg/ryu/archive/master.zip &&\
unzip master.zip && rm master.zip && mv ryu-master ryu &&\
cd /home/auser/ryu &&\
pip3 install . &&\
python3 setup.py install

# Install libraries needed for some application
RUN pip3 install graphyte influxdb_client prometheus-client influxdb

# Set permissions for FlowManager
# Currently need to write log files
RUN chown -R auser /home/auser/flowmanager

# Expose the OpenFlow and Ryu API ports
EXPOSE 6633 6653 8080

# Change to user
USER auser

# Define entrypoint
COPY ENTRYPOINT.sh /ENTRYPOINT.sh
ENTRYPOINT ["/ENTRYPOINT.sh"]
