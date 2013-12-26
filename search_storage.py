#!/usr/bin/env python

import os, stat
import subprocess
import traceback
import socket
import logging

from storage import Storage

TIMESTMP_FMT = ("%H:%M:%S") # no %f for msecs
FORMAT = '%(asctime)s.%(msecs)03d %(name)-5s %(message)s'
logging.basicConfig(format=FORMAT, datefmt=TIMESTMP_FMT, level=logging.INFO)


db = Storage(memory=False)
db.recreate()

visit_log = open('visit.log', 'w', buffering = 0)


class FindFiles:
    def __init__(self):
        self.problem_files = []
        self.log = logging.getLogger("FindFiles")

    def sha1(self, name):
        ret = subprocess.check_output(["/usr/bin/sha1sum", name],
                                     stderr=subprocess.STDOUT)
        return ret.split()[0]

    def visit(self, full_name):
        log = self.log

        if os.path.islink(full_name):
            # if link is invalid os.stat fails
            log.info("ignore symbolic link: %s" % full_name)
            return

        _stat = os.stat(full_name)
        if stat.S_ISSOCK(_stat.st_mode):
            log.info("ignore socket: %s", full_name)
            return
        elif stat.S_ISCHR(_stat.st_mode):
            log.info("ignore character special device file: %s" % full_name)
            return
        elif stat.S_ISBLK(_stat.st_mode):
            log.info("ignore block special device file: %s" % full_name)
            return
        elif stat.S_ISFIFO(_stat.st_mode):
            log.info("ignore FIFO (named pipe): %s" % full_name)
            return
        elif stat.S_ISLNK(_stat.st_mode):
            log.info("ignore symbolic link: %s" % full_name)
            return
        assert(stat.S_ISREG(_stat.st_mode))

        try:
            _sha1 = self.sha1(full_name)
            db.add_file(_sha1, full_name)
        except subprocess.CalledProcessError:
            print "problem file", full_name
            problem_files.append(full_name)

    def search(self, path):
        for root, dirs, files in os.walk(path):
            if '.git' in dirs:
                dirs.remove('.git')
            if '.svn' in dirs:
                dirs.remove('.svn')

            for f in files:
                visit_log.write(("%s/%s\n" % (root, f)))
                full_name = os.path.join(root, f)
                self.visit(full_name)


find = FindFiles()

def unit_test():
    find.sha1('/etc/passwd')
    try:
        find.sha1('000_unit_test_not_exist')
    except subprocess.CalledProcessError:
        print traceback.format_exc()

    try:
        os.unlink('test-files/test-socket')
    except Exception:
        pass
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind('test-files/test-socket')
    find.search('./test-files')
    sock.close()
    os.unlink('test-files/test-socket')

unit_test()


problem_files = find.search('/home/afenkart')


print "\nduplicate keys:"
for f in db.duplicates():
    sha1 = f['sha1']
    print sha1
    for g in db.filenames(sha1):
        print "\t", g

print "\nproblem files:"
for f in problem_files:
    print f


#if __name__ == "__main__"
