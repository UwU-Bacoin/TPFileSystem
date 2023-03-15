from typing import Optional

from fs import *


# TRAVAUX PRATIQUES INF2 : LE SYSTEME DE FICHIER
#
# Ce TP contient des fonctions qu'il vous appartient de comprendre,
# implémenter, tester. Par défaut, pour l'instant les fonctions
# affichent seulement leur nom.
#
# Pensez à regarder l'évolution du cache ...

############################################################
# INIT 
############################################################
# disk_size → taille du disque en secteurs
# cache_size → taille du cache en blocs
def init(disk_name, disk_size, cache_size):
    fs_make_disk(disk_name, disk_size)
    fs_init_cache(cache_size)
    fs_format_disk(disk_name, disk_size)
    fs_init_dcache()


print("**************************************************")
print("\nTEST de init, création du votre premier disque:\n")
init("MY1stDISK", 10, 3)
fs_log_off()


# DUMP
def dump(disk_name: str) -> None:
    fs_dump_disk(disk_name)
    fs_dump_cache()
    fs_dump_dcache()


print("**************************************************")
print("\nTEST de DUMP:\n")

dump("MY1stDISK")


# LS
def ls(param: Optional[str] = None) -> object:
    if param is None:
        res = []
        for i in fs_list_in_dcache():
            res.append(name_of_node(i))
    else:
        res = fs_lookup_in_dcache(param)
    return res


print("**************************************************")
print("\nTEST de LS:\n")
print("ls")
print(ls())
print(ls("jenesuispasla"))
print(ls("."))
print(ls(".."))


# SYNC
def sync() -> None:
    fs_sync_cache()


print("**************************************************")
print("\nTEST de SYNC:\n")
sync()
dump("MY1stDISK")


# MKDIR
def mkdir(name: str) -> bool:

    if name in ls():
        return False

    free_block = fs_getfreeblock()
    if free_block is None:
        return False

    fs_mkdir_in_dcache(name, free_block)
    return True


print("**************************************************")
print("\nTEST de MKDIR:\n")
mkdir("my1stdir")
print(ls())
dump("MY1stDISK")
sync()
dump("MY1stDISK")


# CD
def cd(name: str) -> bool:
    if name in ls() and is_DNODE(fs_lookup_in_dcache(name)):
        fs_cd_in_dcache(name)
        success = True
    else:
        success = False
    return success


print("**************************************************")
print("\nTEST de CD, MKDIR et SYNC:\n")

print(cd("my1stdir"))
print(ls())
mkdir("bach")
print(ls())
mkdir("mozart")
print(ls())
mkdir("berlioz")
print(ls())
dump("MY1stDISK")
sync()
dump("MY1stDISK")
print(cd("mozart"))
print(cd("debussy"))


# TOUCH
def touch(name: str) -> bool:
    fs_touch_in_dcache(name, fs_getfreeblock())
    return bool(ls(name))


print("**************************************************")
print("\nTEST de TOUCH:\n")
touch("son1")
touch("toto")
touch("mon fichier")
print(ls())
dump("MY1stDISK")
sync()
dump("MY1stDISK")


# WRITE
def write(name: str, contents: str) -> bool:
    if name in ls() and is_FNODE(fs_lookup_in_dcache(name)):
        fs_write_in_dcache(name, contents)
        success = True
    else:
        success = False
    return success


print("**************************************************")
print("\nTEST de WRITE:\n")
write("son1", "sisidoréré")
dump("MY1stDISK")
sync()
dump("MY1stDISK")


# READ
def read(name: str) -> str:
    if name in ls() and is_FNODE(fs_lookup_in_dcache(name)):
        res = fs_read_in_dcache(name)
    else:
        res = None
    return res


print("**************************************************")
print("\nTEST de READ:\n")

print(read("read"))
print(read("son1"))
print(read("fichierquinexistepas"))


# RM
def rm(name: str) -> bool:
    if name in ls():
        fs_rm_in_dcache(name)
        success = True
    else:
        success = False
    return success


print("**************************************************")
print("\nTEST de RM:\n")

print(ls())
rm("son1")
print(ls())
cd("..")
dump("MY1stDISK")
sync()
dump("MY1stDISK")

fs_stats()
