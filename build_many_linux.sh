#!/bin/bash
set -e -x

yes | yum update
yes | yum install libudev-devel pcre-devel

export TOOLS_ROOT=$HOME/tools
export VCPKG_ROOT=$TOOLS_ROOT/vcpkg
export PATH=$TOOLS_ROOT/bin:$TOOLS_ROOT:$VCPKG_ROOT:$PATH

export DOWNLOAD_CMAKE_VERSION=3.14.4
export DOWNLOAD_CMAKE_FILENAME=cmake-$DOWNLOAD_CMAKE_VERSION-Linux-x86_64.sh
export DOWNLOAD_CMAKE_URL=https://github.com/Kitware/CMake/releases/download/v$DOWNLOAD_CMAKE_VERSION/$DOWNLOAD_CMAKE_FILENAME

export DOWNLOAD_NINJA_URL=https://github.com/ninja-build/ninja/archive/v1.9.0.zip
export DOWNLOAD_SWIG_URL=https://github.com/swig/swig/archive/rel-4.0.0.tar.gz

rm -rf $TOOLS_ROOT
mkdir -p $TOOLS_ROOT

curl -L -O $DOWNLOAD_CMAKE_URL
bash $DOWNLOAD_CMAKE_FILENAME --skip-license --prefix=$TOOLS_ROOT

# Build recent version of Ninja
curl -L -O $DOWNLOAD_NINJA_URL
mkdir $HOME/temp
unzip v1.9.0.zip -d $HOME/temp
cd $HOME/temp/ninja-1.9.0
./configure.py --bootstrap
cp ninja $TOOLS_ROOT/bin
cd $HOME && rm -rf $HOME/temp

# Build recent version of SWIG
curl -L -O $DOWNLOAD_SWIG_URL
mkdir $HOME/temp
tar zxf rel-4.0.0.tar.gz --directory $HOME/temp
cd $HOME/temp/swig-rel-4.0.0
./autogen.sh
./configure --prefix=$TOOLS_ROOT --without-tcl --without-perl5 --without-octave --without-scilab --without-java --without-javascript --without-android --without-guile --without-mzscheme --without-ruby --without-php --without-ocaml --without-csharp --without-lua --without-r --without-go --without-d
make
make install

# Build vcpkg
git clone https://github.com/NordicPlayground/vcpkg.git $VCPKG_ROOT
$VCPKG_ROOT/bootstrap-vcpkg.sh

# Build nrf-ble-driver
vcpkg install nrf-ble-driver

# Build the wheels
for PYBIN in /opt/python/cp[23]7-cp[23]7[m?u?]/bin; do
    echo "Compiling for $PYBIN"
    rm -rf /data/_skbuild
    "${PYBIN}/pip" install -r /data/requirements-dev.txt
    "${PYBIN}/pip" wheel /data/ -w wheelhouse/
done;

for whl in wheelhouse/*.whl; do
    auditwheel repair "$whl" --plat $PLAT -w /data/wheelhouse/
done
