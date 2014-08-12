#!/usr/bin/env python
import urwid
import storage
import sys, os
import re

f = open('/tmp/log_gui.txt', 'w+')

browse_stack = []
Storage = storage.Storage(memory=False)
Storage.create_indices()

class DuplicatesWalker(urwid.ListWalker):
    def __init__(self):
        self.duplicates = Storage.duplicates(1024 * 1024).fetchall()
        self.focus = (0, self.duplicates[0])

    def _get_at_pos(self, focus):
        (idx, invalid) = focus
        cur = self.duplicates[idx]
        button = urwid.Button("%d %d %s" % (cur['Count'], cur['st_size'], cur['Name']))
        return urwid.AttrMap(button, 'edit', 'editfocus'), (idx, cur)

    def get_focus(self): 
        return self._get_at_pos(self.focus)

    def set_focus(self, focus):
        self.focus = focus
        self._modified()
 
    def get_next(self, focus):
        (idx, elt) = focus
        if idx >= len(self.duplicates) - 1:
            return (None, None)
        return self._get_at_pos((idx + 1, None))

    def get_prev(self, focus):
        (idx, elt) = focus
        if (idx < 1):
            return (None, None)
        return self._get_at_pos((idx - 1, None))

class DuplicatesWithFilenamesWalker(urwid.ListWalker):
    def __init__(self, crc32, sha1):
        self.crc32 = crc32
        self.sha1 = sha1
        self.filenames = Storage.files_by_crc32(crc32).fetchall()
        self.focus = (0, (self.filenames[0]['Name'], crc32, sha1))

    def set_focus(self, focus):
        self.focus = focus
        self._modified()

    def next_position(self, position):
        (idx, cur) = position
        if idx >= len(self.filenames) - 1:
            raise IndexError
        return (idx + 1, (self.filenames[idx + 1]['Name'], self.crc32, self.sha1))

    def prev_position(self, position):
        (idx, elt) = position
        if (idx < 1):
            raise IndexError
        return (idx - 1, (self.filenames[idx - 1]['Name'], self.crc32, self.sha1))

    def __getitem__(self, focus):
        (idx, ignore) = focus
        cur = self.filenames[idx]
        button = urwid.Button("%d %s" % (cur['st_inode'], cur['Name']))
        return urwid.AttrMap(button, 'edit', 'editfocus')


options = u'see remove hard-link'.split()
def createChoicesWalker(filename, crc32, sha1):
    f.write("createChoicesWalker: %s %s %s\n" % (filename, crc32, sha1))
    body = [urwid.Text(filename), urwid.Divider()]
    for c in options:
        button = urwid.Button(c)
        widget = urwid.AttrMap(button, 'edit', 'editfocus')
        body.append(widget)
    return urwid.SimpleFocusListWalker(body)


def createConfirmAction(choice):
    body = [urwid.Text([u'You chose %s\n' % choice])]
    for c in ['Ok', 'Cancel']:
        button = urwid.Button(c)
        widget = urwid.AttrMap(button, 'edit', 'editfocus')
        body.append(widget)
    return urwid.SimpleFocusListWalker(body)

class Browse(urwid.WidgetWrap):
    def __init__(self, title, walker):
        self.walker = walker
        self.listbox = urwid.ListBox(self.walker)
        self.frame = urwid.Frame( self.listbox)
        urwid.WidgetWrap.__init__(self, self.frame)

    def get_widget_label(self, position):
        widget = self.walker[position]
        while widget.focus:
            widget = widget.focus
        widget = widget.base_widget;
        return widget.get_label()

    def get_elt(self):
        #f.write("%s\n" % type(self.walker))
        if (type(self.walker) == DuplicatesWithFilenamesWalker or
            type(self.walker) == DuplicatesWalker):
            (idx, elt) = self.walker.focus
            return elt
        else:
            return self.get_widget_label(self.walker.focus)

    def keypress(self, size, key):
        #f.write('Browse keypress %s\n' % str(key))
        #f.flush()
        if key == 'right' or key == 'enter':
            browse_into(self, self.get_elt())
        elif key == 'left':
            browse_out();
        else:
            return self.frame.keypress(size, key)


class store:
    filename = ""
    sha1 = ''
    action = ""

def browse_into(widget, choice):
    browse_stack.append(widget)
    f.write('browse_into %s level %d\n' % (choice, len(browse_stack)))
    if (len(browse_stack) == 1):
        main.original_widget = Browse(choice,
                                      DuplicatesWithFilenamesWalker(choice['crc32'],
                                                                    choice['sha1']))
    elif (len(browse_stack) == 2):
        (filename, crc32, sha1) = choice
        store.filename = filename
        store.sha1 = sha1
        main.original_widget = Browse(choice, createChoicesWalker(filename,
                                                                  crc32, sha1))
    elif (len(browse_stack) == 3):
        action = choice
        store.action = choice
        if (action == "see"):
            f.write("see %s\n" % re.escape(store.filename))
            os.system("see %s" % re.escape(store.filename))
            browse_stack.pop()
        else:
            main.original_widget = Browse(choice, createConfirmAction(action))
    elif (len(browse_stack) == 4):
        ok_cancel = (choice == "Ok")
        f.write("execute %s %s\n" % (store.action, store.filename))
        browse_stack.pop()
        browse_stack.pop()
        main.original_widget = browse_stack.pop()
    else:
        f.write("no more levels\n")
        browse_stack.pop()
    f.flush()

def browse_out():
    if (len(browse_stack) > 0):
        main.original_widget = browse_stack.pop()
    else:
        print "browse_stack empty"

def exit_program(button):
    raise urwid.ExitMainLoop()

main = urwid.Padding(Browse(u'Pythons', DuplicatesWalker()), left=2, right=2)

def unhandled_input(k):
    f.write('unhandled_input\n')
    if (k == 'q'):
        raise urwid.ExitMainLoop()

palette = [
    ('body','black','dark cyan', 'standout'),
    ('edit','yellow', 'dark blue'),
    ('editfocus','yellow','dark cyan', 'bold'),
    ('foot','light gray', 'black'),
    ('key','light cyan', 'black', 'underline'),
    ('title', 'white', 'black',),
    ]

top = urwid.Overlay(main, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
    align='center', width=('relative', 80),
    valign='middle', height=('relative', 80),
    min_width=20, min_height=9)
urwid.MainLoop(top, palette, unhandled_input=unhandled_input).run()
#loop = urwid.MainLoop(fill, unhandled_input=show_or_exit)
