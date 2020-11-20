def rm_files(path):
    from os import remove
    import glob
    from sys import exit
    try:
        for file in glob.glob(path):
            remove(file)
    except PermissionError:
        print("Permission denied! Please, run with sudo.")
        exit()
    except OSError:
        print("Failed to remove files:", path)
        exit()


def rm_dir(path):
    import shutil
    try:
        shutil.rmtree(path)
    except OSError:
        print("Failed to remove directory:", path)


def mkdir(path):
    from os import makedirs
    from sys import exit
    try:
        makedirs(path, exist_ok=True)
    except PermissionError:
        print("Permission denied! Please, run with sudo.")
        exit()
    except OSError:
        print("Failed to create directory:", path)
        exit()


def down_file(url, path):
    from os.path import isfile, basename, exists
    from os import remove
    from urllib import request
    from sys import exit
    try:
        if isfile(path) is True:
            remove(path)
            request.urlretrieve(url, path)
        else:
            basename = basename(path)
            if exists(basename) is False:
                mkdir(basename)
            request.urlretrieve(url, path)
    except PermissionError:
        print("Permission denied! Please, run with sudo.")
        exit()
    except OSError:
        print("Failed to download:", url)
        exit()


def urlretrieve_and_check(url, path, shasum, tries=0):
    from sys import exit
    if tries < 0 or type(tries) is not int:
        print("Incorrect tries! Exiting")
        exit()
    count = 0
    if tries == 0:
        while sha256_file(path) != shasum:
            down_file(url, path)
    else:
        while count < tries and sha256_file(path) != shasum:
            down_file(url, path)
            count += 1


def untar(archive, path):
    from sys import exit
    import tarfile
    try:
        tar = tarfile.open(archive, mode='r|xz')
        tar.extractall(path=path)
        tar.close()
    except PermissionError:
        print("Permission denied! Please, run with sudo.")
        exit()
    except OSError:
        print("Failed to unpacking the archive:", archive)
        exit()


def sha256_file(path):
    from os.path import isfile
    from hashlib import sha256
    if isfile(path) is False:
        return None
    with open(path, "rb") as f:
        hsh = sha256()
        while True:
            data = f.read(4096)
            if not data:
                break
            hsh.update(data)
    return hsh.hexdigest()


def sync_repo(name, path, arch, mirror_url, tries):
    from os import listdir, remove
    from json import loads
    local_path = path + "/" + arch
    mirror_path = mirror_url + "/" + arch

    print("\nStarting syncing repository", name + " (" + arch + "):")

    print("Cleaning the", path, "directory...")
    rm_files(local_path + "/latest/*.txz")
    rm_files(local_path + "/latest/*.conf")
    rm_files(local_path + "/latest/Latest/pkg*")

    print("Downloading packagesite.txz...")
    down_file(mirror_path + "/latest/packagesite.txz", local_path + "/temp/packagesite.txz")

    print("Unpacking packagesite.txz...")
    untar(local_path + "/temp/packagesite.txz", local_path + "/temp/")

    print("Removing old packages...")   # TODO read from json
    with open(local_path + "/temp/packagesite.yaml", "r") as f:
        data = str(f.read())
        for i in listdir(local_path + "/latest/All/"):
            if i not in data:
                remove(local_path + "/latest/All/" + i)

    print("Downloading", arch + "...")
    files = {"/latest/Latest/pkg-devel.txz", "/latest/Latest/pkg.txz", "/latest/Latest/pkg.txz.sig",
             "/latest/meta.conf", "/latest/meta.txz", "/latest/packagesite.txz"}
    for file in files:
        down_file(mirror_path + file, local_path + file)

    with open(local_path + "/temp/packagesite.yaml", "r") as f:
        for line in f:
            data = loads(line)
            file_path = local_path + "/latest/" + data["repopath"]
            urlretrieve_and_check(mirror_path + "/latest/" + data["repopath"], file_path, data["sum"], int(tries))

    print("Cleaning the temp directory...")
    rm_dir(local_path + "/temp/")

    print("\n Complete syncing repository", name + "!\n")


def main():
    from configparser import ConfigParser
    config = ConfigParser()
    config.read("settings.ini")

    for i in config.sections():
        sync_repo(i, config[i]["path"], config[i]["arch"], config[i]["mirror_url"], config[i]["tries"])


if __name__ == '__main__':
    main()
