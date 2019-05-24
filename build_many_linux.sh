#!/bin/bash
set -e

# Inspired by https://github.com/pypa/python-manylinux-demo/blob/a615d78e5042c01a03e1bbb1ca78603c90dbce1f/travis/build-wheels.sh

# To build 32bit wheels, run:
# docker run --rm -v $PWD:/data -e "UAMQP_REBUILD_PYX=True" local/manylinux_crypto32 /data/build_many_linux.sh
# To build 64bit wheels, run:
# docker run --rm -v $PWD:/data -e "UAMQP_REBUILD_PYX=True" local/manylinux_crypto64 /data/build_many_linux.sh
#
export VCPKG_ROOT=/data/vcpkg
export PATH=$VCPKG_ROOT:$PATH

sudo apt-get update
sudo apt-get install ninja-build swig libudev-dev

git clone https://github.com/NordicPlayground/vcpkg.git $VCPKG_ROOT
$VCPKG_ROOT/bootstrap-vcpkg.sh

# Build the wheels
pushd /data;
for PYBIN in /opt/python/*/bin; do
    vcpkg install nrf-ble-driver:$(python_arch)-linux
    $PYBIN/pip install cython==0.28.5 wheel;
    $PYBIN/python setup.py bdist_wheel -d /wheelhouse;
    rm -rf build/
done;
popd;

# Repair the wheels
for WHL in /wheelhouse/*; do
    auditwheel repair $WHL -w /data/wheelhouse/;
done;

# Set up env vars to run live tests - otherwise they will be skipped.
export EVENT_HUB_HOSTNAME=""
export EVENT_HUB_NAME=""
export EVENT_HUB_SAS_POLICY=""
export EVENT_HUB_SAS_KEY=""
export IOTHUB_HOSTNAME=""
export IOTHUB_HUB_NAME=""
export IOTHUB_DEVICE=""
export IOTHUB_ENDPOINT=""
export IOTHUB_SAS_POLICY=""
export IOTHUB_SAS_KEY=""

# Test the wheels
for PYBIN in /opt/python/*/bin; do
        $PYBIN/pip install "certifi>=2017.4.17" "six~=1.0" "enum34>=1.0.4" "pytest" "pylint";
        $PYBIN/pip install uamqp --no-index -f /data/wheelhouse;
        $PYBIN/python -c 'import uamqp;print("*****Importing uamqp from wheel successful*****")';
        pushd /data;
        $PYBIN/pytest -v;
        popd;
done