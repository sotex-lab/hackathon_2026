FROM ubuntu:24.04

ARG SQLPACKAGE_URL=https://aka.ms/sqlpackage-linux

RUN apt update \
	&& apt install -y wget zip libunwind8 libicu74 \
	&& wget -O sqlpackage-linux.zip $SQLPACKAGE_URL \
	&& mkdir /opt/sqlpackage \
	&& unzip sqlpackage-linux.zip -d /opt/sqlpackage \
	&& chmod a+x /opt/sqlpackage/sqlpackage \
	&& ln -s /opt/sqlpackage/sqlpackage /usr/bin/sqlpackage

ENTRYPOINT ["sqlpackage"]
