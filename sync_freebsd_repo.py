from configparser import ConfigParser, NoOptionError


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


def download_file(url, path):
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


def download_and_check(url, path, shasum, tries):
    count = 0
    if tries == 0:
        while sha256_file(path) != shasum:
            download_file(url, path)
    else:
        while count < tries and sha256_file(path) != shasum:
            download_file(url, path)
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


def percent(count, total):
    return str(int(count / (total / 100))) + '%'


def create_config(path):
    config.add_section("example_repo")
    config.set("example_repo", "path", "/repo")
    config.set("example_repo", "mirror_url", "https://pkg.freebsd.org")
    config.set("example_repo", "arch", "FreeBSD:12:amd64")
    config.set("example_repo", "release", "latest")
    config.set("example_repo", "fast", "yes")
    config.set("example_repo", "tries", "0")

    with open(path, "w") as config_file:
        config.write(config_file)


def except_var_error(section, var, default_value):
    print("Warning!\n"
          "Incorrect or empty variable in section " + section + ": " + var + "\n"
          "Use the default value: " + var + " = " + default_value)
    config.set(section, var, default_value)


def check_config(path):
    from os.path import isfile
    if not isfile(path) or not config.sections():
        print("Warning!\n"
              "File settings.ini is missing or empty!\n"
              "Creating a new file settings.ini, using the default settings\n"
              "Please change it!")
        create_config(path)
        exit()

    for i in config.sections():
        try:
            if config.get(i, "fast") != "yes" and config.get(i, "fast") != "no":
                except_var_error(i, "fast", "yes")
        except (NoOptionError, ValueError):
            except_var_error(i, "fast", "yes")
        try:
            if not 0 <= int(config.get(i, "tries")):
                except_var_error(i, "tries", "0")
        except (NoOptionError, ValueError):
            except_var_error(i, "tries", "0")


def sync_repo(name, path, arch, mirror_url, release, fast, tries):
    from os.path import basename, exists
    from os import listdir, remove
    from json import loads
    local_path = path + "/" + arch + "/" + release + "/"
    mirror_path = mirror_url + "/" + arch + "/" + release + "/"

    print("\nStarting syncing repository", name + " (" + arch + "):")

    if exists(local_path + "temp"):
        print("Cleaning the temp directory...")
        rm_dir(local_path + "temp")

    print("Downloading packagesite.txz...")
    download_file(mirror_path + "packagesite.txz", local_path + "temp/packagesite.txz")

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

    print("Removing old metafiles in", local_path + "...")
    files = {"Latest/pkg-devel.txz", "Latest/pkg.txz", "Latest/pkg.txz.sig",
             "meta.conf", "meta.txz", "packagesite.txz"}
    for file in files:
        rm_files(local_path + file)

    if exists(local_path + "All/"):
        print("Removing old packages in", local_path + "All/...")
        for i in listdir(local_path + "All/"):
            if i not in pkgs:
                print_flush("Removing the " + i)
                remove(local_path + "All/" + i)
    print_flush('')

    print("Downloading", arch + "...")
    for file in files:
        print_flush("Downloading metafile: " + basename(file))
        download_file(mirror_path + file, local_path + file)

    count = 0
    all_pkgs = len(pkgs)
    if fast == "no":
        for i in pkgs.keys():
            file_path = local_path + "All/" + i
            print_flush(percent(count, all_pkgs) + " Download / check shasum: " + i)
            download_and_check(mirror_path + "All/" + i, file_path, pkgs.get(i), int(tries))
            count += 1
    elif fast == "yes":
        if exists(local_path + "All/"):
            for i in listdir(local_path + "All/"):
                del pkgs[i]
                all_pkgs -= 1
        for i in pkgs.keys():
            print_flush(percent(count, all_pkgs) + " Download: " + i)
            download_file(mirror_path + "All/" + i, local_path + "All/" + i)
            count += 1
    print_flush('')

    print("Cleaning the temp directory...")
    rm_dir(local_path + "temp/")

    print("\n Complete syncing repository", name + "!\n")


def main():
    check_config("settings.ini")

    for i in config.sections():
        sync_repo(i, config.get(i, 'path'), config.get(i, 'arch'),
                  config.get(i, 'mirror_url'), config.get(i, 'release'),
                  config.get(i, 'fast'), config.get(i, 'tries'))


if __name__ == '__main__':
    config = ConfigParser()
    config.read("settings.ini")
    main()
