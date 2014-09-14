#!/usr/bin/env python
import weakref

class ObservableProperty(object):
    def __init__(self, init = None):
        self.value = init
        self.observers = []

    def __get__(self, instance, cls):
        if instance:
            return self.value
        else:
            return self

    def __set__(self, instance, value):
        self.value = value
        self.notify()

    def observe(self, cb):
        # CAUTION: cyclic references
        self.observers.append(cb)

    def notify(self):
        for o in self.observers:
            o()

if __name__ == "__main__":
    class Data(object):
        coll = ObservableProperty()
        files = ObservableProperty()

    d = Data()
    def coll_cb():
        print "coll changed"

    def files_cb():
        print "files changed"

    #Data.coll.observe(coll_cb)
    #Data.files.observe(files_cb)

    class Nested(object):
        def __init__(self):
            print self.update
            self.triggered = False
            Data.coll.observe(self.update)

        def update(self):
            self.triggered = True
            print "Nested.update"



    print "chang coll"
    d.coll = "foo"

    print "chang files"
    d.files = "bar"

    n = Nested()
    d.coll = "ter"

    print n.triggered
