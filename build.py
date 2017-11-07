import os
import sys
import subprocess
import shutil
import glob

BUILD_DIR = "_whl_out"
release_files = dict()


def build(python_version, python_exe, boostdir):
    if sys.platform.startswith('win'):
        env = {"VCTargetsPath": r"C:\Program Files (x86)\MSBuild\Microsoft.Cpp\v4.0\V140"}
        env.update(os.environ)
        generator_str = '"Visual Studio 14"'
    elif sys.platform.startswith('linux'):
        generator_str = 'Ninja'
    subprocess.call("git clean -xdf", cwd='build')
    subprocess.call("git clean -xdf", cwd='python')
    subprocess.call("cmake -DBOOST_LIBRARYDIR={} -DPYTHON_VERSION={} -G {} ..".format(boostdir, python_version, generator_str), cwd="build")
    subprocess.call("msbuild.exe pc-ble-driver-py.sln /m /p:Configuration=Release",
                    cwd="build",
                    env=env)
    subprocess.call([python_exe, "setup.py", "bdist_wheel"], cwd="python")
    subprocess.call([python_exe, "setup.py", "bdist_wheel"], cwd="python")
    files = glob.glob("python/dist/*")
    shutil.copy(files[0], BUILD_DIR)


def main():
    try:
        shutil.rmtree(BUILD_DIR)
    except Exception:
        pass
    os.mkdir(BUILD_DIR)
    if sys.platform.startswith('win'):
        build("2.7", r"C:\python27\python", r"c:\boost\boost_1_61_0\stage\lib")
        build("2.7", r"C:\python27-64\python", r"c:\boost\boost_1_61_0\stage\x86_64\lib")
        build("3.4", r"C:\python34\python", r"c:\boost\boost_1_61_0\stage\lib")
        build("3.4", r"C:\python34-64\python", r"c:\boost\boost_1_61_0\stage\x86_64\lib")
    elif sys.platform.startswith('linux'):
        build("2.7", "python", "/home/jokv/boost/boost_1_65_1/stage/x86_64")
        build("3.4", "python3", "/home/jokv/boost/boost_1_65_1/stage/x86_64")
    for k, v in release_files.items():
        print(k)
        with open(os.path.join(BUILD_DIR, k), 'wb') as f:
            f.write(v)


if __name__ == '__main__':
    main()
