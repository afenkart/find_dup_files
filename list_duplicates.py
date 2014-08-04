#!/usr/bin/env python
from storage import *

import sqlite3 as lite
import sys, os
import subprocess
import string
import md5
import traceback


def list_duplicates():
    db = Storage(memory = False, filename = "files.db")
    db.create_indices()
    for row in db.duplicates(1024 * 1024):
        print dict(row)

if __name__ == "__main__":
    list_duplicates()
