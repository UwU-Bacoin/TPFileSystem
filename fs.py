import copy
import base64
from urllib.parse import quote, unquote


# file format: first line contains disk size.
# then each line contains a block, either a directory or a file.
# A file is represented by "FILE <name> <base64-encoded content>"
# A directory is represented by "DIR <name> <parent-sector> (sector1, ...)"

class File:
    def __init__(self, name, sector, content):
        self.name = name
        self.sector = sector
        self.content = content

    def __str__(self):
        return "FILE {} {}".format(quote(self.name), str(base64.b64encode(bytes(self.content, 'utf8')), 'utf8'))


class Dir:
    def __init__(self, name, sector, parent, children):
        self.name = name
        self.sector = sector
        self.parent = parent
        self.children = children

    def __str__(self):
        children = ""
        for c in self.children:
            if len(children) > 0:
                children += ","
            children += str(c)
        return "DIR {} {} {}".format(quote(self.name), self.parent, children)


class Cache:
    def __init__(self, block, content, cacheSize):
        self.sector = block
        self.increment = cacheSize
        self.content = content
        self.usage = 0
        self.dirty = False

    def write(self, content):
        self.dirty = True
        self.usage = 0
        self.content = content

    def read(self):
        self.usage += self.increment
        return self.content

    def used(self):
        self.usage += 1

    def unused(self):
        self.usage -= 1

    def __str__(self):
        return "Block {}::: Dirty: {}, Usage: {}, Content: {}".format(self.sector, self.dirty, self.usage, self.content)


class fs:
    def __init__(self, name, size):
        self.filename = name
        self.hit = 0
        self.miss = 0
        self.cwd = 1
        try:
            open(name, 'r+').close()
        except Exception:
            open(name, 'w').close()
        self.size = size
        self.cache = []
        self.verbose = False

    def flush_stats(self):
        self.hit = 0
        self.miss = 0

    def setVerbose(self):
        self.verbose = True

    def setQuiet(self):
        self.verbose = False

    def init_disk(self):
        with open(self.filename, 'w') as file:
            file.write(str(self.size) + "\n")

    def init_cache(self, size):
        self.cache = []
        for i in range(0, size):
            self.cache.append(None)

    def get_cache_for(self, blockn):
        # first reduce usage for each existing block in cache
        for i in range(0, len(self.cache)):
            if self.cache[i] != None:
                self.cache[i].unused()

        # then try to get it from cache directly
        for i in range(0, len(self.cache)):
            if self.cache[i] == None:
                continue
            if self.cache[i].sector == blockn:
                if self.verbose:
                    print("Block {} already in cache".format(blockn))
                # re-increment usage count for this one
                self.cache[i].used()
                self.hit += 1
                return i
        self.miss += 1
        cacheSize = len(self.cache)
        # look for a free block in cache
        for i in range(0, len(self.cache)):
            if self.cache[i] is None:
                self.cache[i] = Cache(blockn, self.read_block_from_disk(blockn), cacheSize)
                if self.verbose:
                    print("Block {} created in cache".format(blockn))
                return i
        # free a block in cache first
        for i in range(0, len(self.cache)):
            if not self.cache[i].dirty:
                self.cache[i] = Cache(blockn, self.read_block_from_disk(blockn), cacheSize)
                if self.verbose:
                    print("Replacing non dirty cache of {} with {}".format(self.cache[i].sector, blockn))
                return i
        # find the least often used block in cache
        block = 0
        usage = self.cache[0].usage
        for i in range(1, len(self.cache)):
            if self.cache[i].usage < usage:
                usage = self.cache[i].usage
                block = i
        # finaly write the block back to disk, free it and use it
        self.sync()
        self.cache[block] = Cache(blockn, self.read_block_from_disk(blockn), cacheSize)
        if self.verbose:
            print("Replacing dirty unused cache of {} with {}".format(self.cache[i].sector, blockn))
        return block

    def write_block(self, blockn, content):
        cachen = self.get_cache_for(blockn)
        self.cache[cachen].write(content)

    def read_block(self, blockn):
        cachen = self.get_cache_for(blockn)
        return self.cache[cachen].read()

    def get_file_line(self, lineno):
        with open(self.filename, 'r') as file:
            for i, line in enumerate(file):
                if i == lineno:
                    return line
            return "\n"

    def write_block_to_disk(self, blockn, content):
        if self.verbose:
            print("Synchronising block {} to disk with {}.".format(blockn, content))
        value = str(self.size) + "\n"
        for i in range(0, self.size):
            if i + 1 != blockn:
                value += self.get_file_line(i + 1)
            else:
                if content == None:
                    value += "\n"
                else:
                    value += content.__str__() + "\n"
        open(self.filename, 'w').close()
        with open(self.filename, 'w') as file:
            file.write(value)

    def read_block_from_disk(self, blockn):
        if self.verbose:
            print("Synchronising cache block {} from disk.".format(blockn))
        if blockn > self.size or blockn < 1:
            raise Exception("Sector out of range.")
        return self.parseLine(self.get_file_line(blockn), blockn)

    def parseLine(self, line, sector):
        if line == None:
            return None
        elms = line.split(" ")
        typ = elms[0]
        if typ == "DIR":
            children = []
            if elms[3] != '\n' and elms[3] != '':
                child_list = elms[3].split(",")
                for c in child_list:
                    children.append(int(c))
            return Dir(unquote(elms[1]), sector, int(elms[2]), children)
        elif typ == "FILE":
            content = elms[2]
            return File(unquote(elms[1]), sector, str(base64.b64decode(content.strip("\n")), 'utf8'))
        else:
            return None

    def sync(self):
        if self.verbose:
            print("Syncing whole cache.")
        for i in range(0, len(self.cache)):
            if self.cache[i] == None:
                continue
            if self.cache[i].dirty:
                self.write_block_to_disk(self.cache[i].sector, self.cache[i].content)
                self.cache[i].dirty = False

    def format(self):
        if self.verbose:
            print("Formating whole disk.")
        self.write_block(1, Dir("/", 1, 1, []))
        for i in range(self.size - 1, 1, -1):
            if self.verbose:
                print(i)
            self.write_block(i + 1, None)
        self.sync()
        self.flush_stats()

    def getNodeName(self, sector):
        node = self.read_block(sector)
        if node == False:
            return False
        return node.name

    def getSectorByName(self, name):
        ls = self.ls()
        for n in ls:
            if n.name == name:
                return n.sector

    def ls(self):
        cwd = self.read_block(self.cwd)
        dotdot = copy.deepcopy(self.read_block(cwd.parent))
        dotdot.name = '..'
        dot = copy.deepcopy(cwd)
        dot.name = '.'

        children = [dot, dotdot]
        for c in cwd.children:
            children.append(self.read_block(c))
        return children

    def present(self, name):
        cwd = self.read_block(self.cwd)
        if name == '.':
            return self.cwd
        if name == '..':
            return cwd.parent
        for c in cwd.children:
            node = self.read_block(c)
            if node.name == name:
                return c
        return None

    def lookup(self, name):
        sector = self.present(name)
        if sector == None:
            return None
        return copy.deepcopy(self.read_block(sector))

    def cd(self, name):
        self.cwd = self.present(name)
        if self.verbose:
            print("New cwd: " + str(self.cwd))
        if self.cwd == None:
            raise Exception('Current directory does not exist.')

    def find_free_block(self):
        for c in self.cache:
            if c != None and c.content == None:
                return c.sector
        # if no free block in cache
        i = 0
        with open(self.filename, 'r') as file:
            for line in file:
                if line == '\n':
                    node = self.read_block(i)
                    if node == None:
                        return i
                i += 1
        return False

    def mkdir(self, name, sector):
        if sector == None:
            raise Exception("cannot mkdir sector None.")
        self.write_block(sector, Dir(name, sector, self.cwd, []))
        currentNode = self.read_block(self.cwd)
        children = currentNode.children
        children.append(sector)
        newNode = Dir(currentNode.name, currentNode.sector, currentNode.parent, children)
        self.write_block(self.cwd, newNode)

    def touch(self, name, sector):
        if sector == None:
            raise Exception("cannot touch sector None.")
        self.write_block(sector, File(name, sector, ""))
        currentNode = self.read_block(self.cwd)
        children = currentNode.children
        children.append(sector)
        newNode = Dir(currentNode.name, currentNode.sector, currentNode.parent, children)
        self.write_block(self.cwd, newNode)

    def rm(self, name):
        sector = self.getSectorByName(name)
        currentNode = self.read_block(self.cwd)
        children = currentNode.children
        children.remove(sector)
        newNode = Dir(currentNode.name, currentNode.sector, currentNode.parent, children)
        self.write_block(sector, None)
        self.write_block(self.cwd, newNode)

    def read(self, name):
        sector = self.getSectorByName(name)
        return self.read_block(sector).content

    def write(self, name, value):
        sector = self.getSectorByName(name)
        oldfile = self.read_block(sector)
        self.write_block(sector, File(oldfile.name, sector, value))

    def dump_cache(self):
        i = 0
        for c in self.cache:
            print("{}: {}".format(i, c))
            i += 1

    def cwd_str(self, directory, string):
        if directory == 1:
            return string
        node = self.read_block(directory)
        name = node.name
        parent = node.parent
        return self.cwd_str(parent, "/" + name + string)

    def dump_dir(self):
        print("current directory: " + self.cwd_str(self.cwd, "/"))

    def dump_stats(self):
        if self.hit == 0 and self.miss == 0:
            print("No stat yet...")
        else:
            print("HIT/MISS: {}/{}, HIT ratio: {}".format(self.hit, self.miss, (self.hit / (self.hit + self.miss))))


CACHE = None


def fs_make_disk(disk, nbblocks):
    global CACHE
    CACHE = fs(disk, nbblocks)
    CACHE.init_disk()


def fs_init_cache(nbblocks):
    global CACHE
    CACHE.init_cache(nbblocks)


def fs_init_dcache():
    pass


def fs_format_disk(diskname, disksize):
    # remarque: arguments inutiles, mais pour rester compatibles avec le sujet.
    global CACHE
    CACHE.format()


def fs_sync_cache():
    global CACHE
    CACHE.sync()


def fs_dump_disk(filename):
    with open(filename, 'r') as file:
        print("--------------- DISK DUMP ----------------")
        i = 0
        for line in file:
            print('{0:03d} {1}'.format(i, line), end="")
            i += 1
        print("------------------------------------------")


def fs_dump_cache():
    global CACHE
    print("--------------- CACHE DUMP ----------------")
    CACHE.dump_cache()
    print("-------------------------------------------")


def fs_dump_dcache():
    global CACHE
    print("--------------- DCACHE DUMP ----------------")
    CACHE.dump_dir()
    print("--------------------------------------------")


def fs_list_in_dcache():
    global CACHE
    return CACHE.ls()


def fs_lookup_in_dcache(name):
    global CACHE
    ans = CACHE.lookup(name)
    if ans == None:
        return False
    return ans


def fs_cd_in_dcache(name):
    global CACHE
    CACHE.cd(name)


def fs_getfreeblock():
    global CACHE
    return CACHE.find_free_block()


def fs_get_freeblock():
    return fs_getfreeblock()


def fs_mkdir_in_dcache(name, sector):
    global CACHE
    CACHE.mkdir(name, sector)


def fs_touch_in_dcache(name, sector):
    global CACHE
    CACHE.touch(name, sector)


def fs_rm_in_dcache(name):
    global CACHE
    CACHE.rm(name)


def fs_write_in_dcache(name, string):
    global CACHE
    CACHE.write(name, string)


def fs_read_in_dcache(name):
    global CACHE
    return CACHE.read(name)


def name_of_node(node):
    return node.name


def is_DNODE(node):
    return isinstance(node, Dir)


def is_FNODE(node):
    return isinstance(node, File)


def fs_cwd():
    global CACHE
    return CACHE.cwd_str(CACHE.cwd, "/")


def fs_stats():
    """ affiche les stats hit/miss """
    global CACHE
    return CACHE.dump_stats()


def fs_log_on():
    """ affiche le détail des accès """
    global CACHE
    CACHE.setVerbose()


def fs_log_off():
    """ arrête l'affichage détaillé des accès """
    global CACHE
    CACHE.setQuiet()


def nb_of_node(node):
    return node.sector
