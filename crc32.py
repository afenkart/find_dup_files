#!/usr/bin/env python

import binascii

def crc32(fname):
    crc = 0
    with open(fname, "rb") as f:
        d = f.read(32768)
        while d:
            crc = binascii.crc32(d, crc)
            d = f.read(524288) # 512 kB
    return crc & 0xffffffff


def unit_test():
    c = crc32('test-files/hard_link1.txt')
    assert(0xddeaa107 == c);

if __name__ == "__main__":
    unit_test()
