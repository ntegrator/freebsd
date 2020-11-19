import os
import urllib.request
import glob
import sys
import tarfile
import json
import hashlib
import configparser
import shutil


def rm_files(path):
    try:
        for file in glob.glob(path):
            os.remove(file)
    except PermissionError:
        print("Permission denied! Please, run with sudo.")
        sys.exit()
    except OSError:
        print("Failed to remove old files!")
        sys.exit()


def rm_dir(path):
    try:
        shutil.rmtree(path)
    except OSError:
        print("Failed to remove temp files!")


def mkdir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except PermissionError:
        print("Permission denied! Please, run with sudo.")
        sys.exit()
    except OSError:
        print("Failed to create directories!")
        sys.exit()


def down_file(url, path):
    try:
        urllib.request.urlretrieve(url, path)
    except PermissionError:
        print("Permission denied! Please, run with sudo.")
        sys.exit()
    except OSError:
        print("Failed to download:", url)
        sys.exit()


def untar(archive, path):
    try:
        tar = tarfile.open(archive, mode='r|xz')
        tar.extractall(path=path)
        tar.close()
    except PermissionError:
        print("Permission denied! Please, run with sudo.")
        sys.exit()
    except OSError:
        print("Failed to unpacking the archive:", archive)
        sys.exit()


def sha256_file(file):
    with open(file, "rb") as f:
        hsh = hashlib.sha256()
        while True:
            data = f.read(4096)
            if not data:
                break
            hsh.update(data)
    return hsh.hexdigest()


def sync_repo(name, path, arch, mirror_url):
    local_path = path + "/" + arch
    mirror_path = mirror_url + "/" + arch

    print("\nStarting syncing repository", name + " (" + arch + "):")

    print("Cleaning the", path, "directory...")
    rm_files(local_path + "/latest/*.txz")
    rm_files(local_path + "/latest/*.conf")
    rm_files(local_path + "/latest/Latest/pkg*")

    print("Creating a directory structure...")
    mkdir(local_path + "/latest/All")
    mkdir(local_path + "/latest/Latest")
    mkdir(local_path + "/temp")

    print("Downloading packagesite.txz...")
    down_file(mirror_path + "/latest/packagesite.txz", local_path + "/temp/packagesite.txz")

    print("Unpacking packagesite.txz...")
    untar(local_path + "/temp/packagesite.txz", local_path + "/temp/")

    print("Removing old packages...")
    with open(local_path + "/temp/packagesite.yaml", "r") as f:
        data = str(f.read())
        for i in os.listdir(local_path + "/latest/All/"):
            if i in data:
                pass
            else:
                os.remove(local_path + "/latest/All/" + i)

    print("Downloading", arch + "...")
    down_file(mirror_path + "/latest/Latest/pkg-devel.txz", local_path + "/latest/Latest/pkg-devel.txz")
    down_file(mirror_path + "/latest/Latest/pkg.txz", local_path + "/latest/Latest/pkg.txz")
    down_file(mirror_path + "/latest/Latest/pkg.txz.sig", local_path + "/latest/Latest/pkg.txz.sig")

    down_file(mirror_path + "/latest/meta.conf", local_path + "/latest/meta.conf")
    down_file(mirror_path + "/latest/meta.txz", local_path + "/latest/meta.txz")
    down_file(mirror_path + "/latest/packagesite.txz", local_path + "/latest/packagesite.txz")

    with open(local_path + "/temp/packagesite.yaml", "r") as f:
        for line in f:
            data = json.loads(line)
            file_path = local_path + "/latest/" + data["repopath"]
            if os.path.isfile(file_path) is True:
                if sha256_file(file_path) != data["sum"]:
                    os.remove(file_path)
                    down_file(mirror_path + "/latest/" + data["repopath"], file_path)
                    if sha256_file(file_path) != data["sum"]:
                        os.remove(file_path)
                        down_file(mirror_path + "/latest/" + data["repopath"], file_path)
            else:
                down_file(mirror_path + "/latest/" + data["repopath"], file_path)
                if sha256_file(file_path) != data["sum"]:
                    os.remove(file_path)
                    down_file(mirror_path + "/latest/" + data["repopath"], file_path)

    print("Cleaning the temp directory...")
    rm_dir(local_path + "/temp/")

    print("\n Complete syncing repository", name + "!\n")


def main():
    config = configparser.ConfigParser()
    config.read("settings.ini")

    for i in config.sections():
        sync_repo(i, config[i]["path"], config[i]["arch"], config[i]["mirror_url"])


if __name__ == '__main__':
    main()
