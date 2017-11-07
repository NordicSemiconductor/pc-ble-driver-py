import os
import sys
import subprocess
import time
import shutil, re
import glob

BUILD_DIR = "_whl_out"
release_files = dict()


def build(python_version, python_exe, boostdir, win):
    if sys.platform.startswith('win'):
        env = {"VCTargetsPath": r"C:\Program Files (x86)\MSBuild\Microsoft.Cpp\v4.0\V140"}
        env.update(os.environ)
        generator_str = '"Visual Studio 14"'
    else:
        generator_str = 'Ninja'
    subprocess.call("git clean -xdf", cwd='build')
    subprocess.call("git clean -xdf", cwd='python')
    subprocess.call("cmake -DBOOST_LIBRARYDIR={} -DPYTHON_VERSION={} -G {}} ..".format(boostdir, python_version, generator_str), cwd="build")
    subprocess.call("msbuild.exe pc-ble-driver-py.sln /m /p:Configuration=Release",
                    cwd="build",
                    env=env)
    subprocess.call([python_exe, "setup.py", "bdist_wheel"], cwd="python")
    files = glob.glob("python/dist/*")
    with open(files[0], 'rb') as f:
        # match = re.match("(pc_ble_driver_py-[0-9\.]*)", os.path.split(files[0])[-1])
        # filename = match.group(1)
        # if '27' in python_exe:
        #     filename += '-cp27-cp27m-'
        # elif '34' in python_exe:
        #     filename += '-cp34-cp34m-'
        # elif '35' in python_exe:
        #     filename += '-cp35-cp35m-'
        # elif '36' in python_exe:
        #     filename += '-cp36cp36m-'
        # if '64' in python_exe:
        #     filename += 'win_amd64'
        # else:
        #     filename += "win32"
        # filename += '.whl'
        release_files[files[0]] = f.read()


def main():
    try:
        shutil.rmtree(BUILD_DIR)
    except Exception:
        pass
    os.mkdir(BUILD_DIR)
    build("2.7", r"C:\python27\python", r"c:\boost\boost_1_61_0\stage\lib")
    build("2.7", r"C:\python27-64\python", r"c:\boost\boost_1_61_0\stage\x86_64\lib")
    build("3.4", r"C:\python34\python", r"c:\boost\boost_1_61_0\stage\lib")
    build("3.4", r"C:\python34-64\python", r"c:\boost\boost_1_61_0\stage\lib")
    for k, v in release_files.items():
        print(k)
        with open(os.path.join(BUILD_DIR, k), 'wb') as f:
            f.write(v)


if __name__ == '__main__':
    main()
