# Dockerrized Version of build process from https://github.com/CollaboraOnline/online/blob/master/docker/from-source/build.sh
FROM docker.io/collabora/code:23.05.5.4.1 as build

USER root
RUN apt update && apt install -y --no-install-recommends \
  vim \
  git \
  wget \
  build-essential \
  autoconf \
  pkg-config \
  libssl-dev \
  libtool \
  m4 \
  automake \
  python3-lxml \
  python3-polib \
  libzstd-dev \
  libcppunit-dev \
  libcap-dev \
  libpam0g-dev \
  nodejs \
  npm \
  gperf \
  libz-dev \
  bison \
  flex \
  zip \
  unzip \
  gettext \
  nasm \
  libpng-dev \
  rsync


RUN mkdir -p /app/builddir && mkdir -p /app/instdir && chown -R cool /app
USER cool

# POCO
WORKDIR /app/builddir
RUN wget https://github.com/pocoproject/poco/archive/poco-1.11.1-release.tar.gz \
  && tar -xzf poco-1.11.1-release.tar.gz && cd poco-poco-1.11.1-release/ \
  && ./configure --static --no-tests --no-samples --no-sharedlibs --cflags="-fPIC" --omit=Zip,Data,Data/SQLite,Data/ODBC,Data/MySQL,MongoDB,PDF,CppParser,PageCompiler,Redis,Encodings,ActiveRecord --prefix=/app/builddir/poco \ 
  && make -j $(nproc) \
  && make install

# LOKit
WORKDIR /app/builddir
RUN git clone --single-branch  -b distro/collabora/co-23.05 https://git.libreoffice.org/core lo \
  && cd lo \
  && git fetch --all \
  && ./g pull -r \
  && ./install_deps.sh \
  && ./autogen.sh --with-distro=CPLinux-LOKit --disable-epm --without-package-format --disable-symbols && make -j $(nproc) \
  && mkdir -p /app/instdir/opt/ \
  && cp -a instdir /app/instdir/opt/lokit

COPY patches/ /app/builddir/patches/

# Collabora
WORKDIR /app/builddir
RUN git clone https://github.com/CollaboraOnline/online.git --branch cp-23.05.5-3 --single-branch \
  && cd online \
  && git fetch --all \
  && git clean -f -d \
  && git pull -r \
  && git apply /app/builddir/patches/*.patch \
  && ./autogen.sh \
  && ./configure --prefix=/usr --sysconfdir=/etc --localstatedir=/var --enable-silent-rules --with-lokit-path=/app/builddir/lo/include --with-lo-path=/opt/collaboraoffice/ --with-poco-includes=/app/builddir/poco/include --with-poco-libs=/app/builddir/poco/lib \
  && make -j $(nproc) coolwsd


FROM docker.io/collabora/code:23.05.5.4.1
LABEL BUILD_IGNORE="True"
LABEL IMAGE="collabora-patched"
COPY --from=build /app/builddir/online/coolwsd /usr/bin/coolwsd