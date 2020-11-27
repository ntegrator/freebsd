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
    from shutil import rmtree
    try:
        rmtree(path)
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
    from os.path import isfile, dirname, exists
    from os import remove
    from urllib import request
    from sys import exit
    try:
        if isfile(path) is True:
            remove(path)
            request.urlretrieve(url, path)
        else:
            dirname = dirname(path)
            if exists(dirname) is False:
                mkdir(dirname)
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


def print_flush(phrase):
    from os import get_terminal_size
    print(phrase + ' ' * (get_terminal_size().columns - len(phrase)), end='\r')


def sync_repo(name, path, arch, mirror_url, release, tries):
    from os.path import basename, exists
    from os import listdir, remove
    from json import loads
    local_path = path + "/" + arch + "/" + release + "/"
    mirror_path = mirror_url + "/" + arch + "/" + release + "/"

    print("\nStarting syncing repository", name + " (" + arch + "):")

    print("Cleaning the", path, "directory...")
    rm_files(local_path + release + "/*.txz")
    rm_files(local_path + release + "/*.conf")
    rm_files(local_path + release + "/Latest/pkg*")

    print("Downloading packagesite.txz...")
    down_file(mirror_path + "packagesite.txz", local_path + "temp/packagesite.txz")

    print("Unpacking packagesite.txz...")
    untar(local_path + "temp/packagesite.txz", local_path + "temp/")

    print("Processing packagesite.txz...")
    pkgs = {}
    with open(local_path + "temp/packagesite.yaml", "r") as f:
        for line in f:
            data = loads(line)
            pkgs[basename(data["path"])] = data["sum"]
            print_flush("Processing: " + basename(data["path"]))
    print_flush('')

    if exists(local_path + "All/"):
        print("Removing old packages...")
        for i in listdir(local_path + "All/"):
            if i not in pkgs:
                print_flush("Removing the " + i)
                remove(local_path + "All/" + i)
    print_flush('')

    print("Downloading", arch + "...")
    files = {"Latest/pkg-devel.txz", "Latest/pkg.txz", "Latest/pkg.txz.sig",
             "meta.conf", "meta.txz", "packagesite.txz"}
    for file in files:
        print_flush("Downloading: " + basename(file))
        down_file(mirror_path + file, local_path + file)

    for i in pkgs.keys():
        file_path = local_path + "All/" + i
        print_flush("Downloading / checking shasum: " + i)
        urlretrieve_and_check(mirror_path + "All/" + i, file_path, pkgs.get(i), int(tries))

    print("Cleaning the temp directory...")
    rm_dir(local_path + "temp/")

    print("\n Complete syncing repository", name + "!\n")


def main():
    from configparser import ConfigParser
    config = ConfigParser()
    config.read("settings.ini")

    for i in config.sections():
        sync_repo(i, config[i]["path"], config[i]["arch"], config[i]["mirror_url"],
                  config[i]["release"], config[i]["tries"])


if __name__ == '__main__':
    main()
