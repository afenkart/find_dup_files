#!/usr/bin/env python
import urwid
import storage
import sys, os
import re

f = open('/tmp/log_gui.txt', 'w+', False)

Storage = storage.Storage(memory=False)
Storage.create_indices()

browse_stack = []
data = {
    'duplicates': Storage.duplicates(0).fetchall(),
    'hashes' : {},
    'collision_details' : None,
    'filename' : None,
    'action' : None
}

SKIP_PREFIX = "/home/afenkart/"

def strip_prefix(filename):
    if filename.startswith(SKIP_PREFIX):
        return filename[len(SKIP_PREFIX):]
    else:
        return filename

class MenuButton(urwid.Button):
    def __init__(self, caption, callback):
        super(MenuButton, self).__init__("")
        urwid.connect_signal(self, 'click', callback)
        self._w = urwid.AttrMap(urwid.SelectableIcon(
            [" ", caption], 2), 'None', 'selected')

class MyListWalker(urwid.ListWalker):
    def __init__(self, data, render_fun, callback):
        self.data = data
        self.render_fun = render_fun
        self.focus = 0
        self.callback = callback

    def set_focus(self, focus):
        self.focus = focus
        self._modified()

    def next_position(self, idx):
        if idx >= len(self.data) - 1:
            raise IndexError
        return (idx + 1)

    def prev_position(self, idx):
        if (idx < 1):
            raise IndexError
        return idx - 1

    def __getitem__(self, idx):
        cur = self.data[idx]
        return MenuButton(self.render_fun(self.data[idx]), self.callback)

class DuplicatesWalker(urwid.WidgetWrap):
    def __init__(self, duplicates):
        render_fun = lambda x: "%2d %7dk %s" % (x['Count'], x['st_size']/1000,
                                                strip_prefix(x['Name']))
        self.walker = MyListWalker(duplicates, render_fun, self.callback)
        urwid.WidgetWrap.__init__(self, urwid.ListBox(self.walker))

    def get_elt(self):
        self.callback(None)
        return data['duplicates'][self.walker.focus]

    def callback(self, widget):
        index = self._w.focus_position
        row = data['duplicates'][index]
        data['hashes'] = { 'crc32': row['crc32'], 'sha1': row['sha1']}
        f.write("button callback %r\n" % data['hashes'])
        browse_into(self, None)

class DuplicatesWithFilenamesWalker(urwid.WidgetWrap):
    def __init__(self, filenames):
        render_fun = lambda x: "%d %s" % (x['st_inode'], x['Name'])
        self.walker = MyListWalker(filenames, render_fun, self.callback)
        self.filenames = filenames
        urwid.WidgetWrap.__init__(self, urwid.ListBox(self.walker))

    def get_elt(self):
        self.callback(None)
        return data['collision_details'][self.walker.focus]['Name']

    def callback(self, widget):
        index = self._w.focus_position
        data['filename'] = self.filenames[index]['Name']
        f.write("button callback %r\n" % data['filename'])
        browse_into(self, None)

class HardlinkMenu(urwid.WidgetWrap):
    def __init__(self):
        hardlinks = [x for x in data['collision_details'] if x['Name'] != data['filename']]
        render_fun = lambda x: "%d %s" % (x['st_inode'], x['Name'])
        self.walker = MyListWalker(hardlinks, render_fun, self.callback)
        self.hardlinks = hardlinks

        title = "hard-link file %s to:" % data['filename']
        pile = urwid.Pile([urwid.AttrMap(urwid.Text(title), 'title'),
                           urwid.Divider()])
        pile.selectable = False
        self.frame = urwid.Frame(urwid.ListBox(self.walker),
                                 header = pile)

        self.overlay = urwid.Overlay(self.frame,
                                   browse_stack[-1],
                                   align='center', width=('relative', 90),
                                   valign='middle', height=('relative', 60),
                                   min_width=20, min_height=9)
        urwid.WidgetWrap.__init__(self, self.overlay)

    def callback(self, widget):
        index = self.walker.focus
        row = self.hardlinks[index]
        f.write("button callback %r\n" % self.hardlinks[index]['Name'])
        data['hard-link_target'] = row
        browse_into(self, None)

def createSimpleListWalker(title, elts, callback):
    body = [urwid.AttrMap(urwid.Text(title), 'title', 'None')]
    body.append(urwid.Divider())
    body.extend([MenuButton(c, callback) for c in elts])
    return urwid.SimpleFocusListWalker(body)

class ContextMenu(urwid.WidgetWrap):
    def __init__(self, title, filename):
        self.options = u'see remove hard-link'.split()
        self.walker = createSimpleListWalker(strip_prefix(filename),
                                             self.options,
                                             self.callback)
        self.frame = urwid.Overlay(urwid.ListBox(self.walker),
                                   browse_stack[-1],
                                   align='center', width=('relative', 80),
                                   valign='middle', height=('relative', 60),
                                   min_width=20, min_height=9)
        urwid.WidgetWrap.__init__(self, self.frame)

    def get_elt(self):
        self.callback(None)
        return self.options[self.walker.focus - 2]

    def callback(self, widget):
        # self.walker.focus - 2
        data['action'] = self.options[self.walker.focus - 2]
        f.write("button callback %r\n" % data['action'])
        browse_into(self, None)

class ConfirmAction(urwid.WidgetWrap):
    def __init__(self, title):
        self.ok_cancel = ['Ok', 'Cancel']
        self.walker = createSimpleListWalker(title, self.ok_cancel,
                                             self.callback)
        self.frame = urwid.Overlay(urwid.ListBox(self.walker),
                                   browse_stack[-1],
                                   align='center', width=('relative', 80),
                                   valign='bottom', height=('relative', 30),
                                   min_width=20, min_height=9)
        urwid.WidgetWrap.__init__(self, self.frame)

    def get_elt(self):
        return self.ok_cancel[self.walker.focus - 2]

    def callback(self, widget):
        f.write("button callback %r\n" % self._w.focus.focus_position)
        browse_into(self, self.get_elt())

class Action:
    @staticmethod
    def hardlink(src, target):
        pass

    @staticmethod
    def remove(file_):
        f.write("execute %s %s\n" % (data['action'], data['filename']))
        os.remove(file_)
        Storage.remove_file(file_)

class Representation:
    @staticmethod
    def update_collision():
        filenames = Storage.files_by_crc32(data['hashes']['crc32'])
        data['collision_details'] = filenames.fetchall()

def browse_into(widget, choice):
    browse_stack.append(widget)
    f.write('browse_into level %d\n' % (len(browse_stack)))
    if (len(browse_stack) == 1):
        filenames = Storage.files_by_crc32(data['hashes']['crc32'])
        data['collision_details'] = filenames.fetchall()
        main.original_widget = DuplicatesWithFilenamesWalker(data['collision_details'])
    elif (len(browse_stack) == 2):
        main.original_widget = ContextMenu('title', data['filename'])
    elif (len(browse_stack) == 3):
        action = data['action']
        if (action == "see"):
            f.write("see %s\n" % re.escape(data['filename']))
            os.system("see %s" % re.escape(data['filename']))
            browse_stack.pop()
        elif action == "hard-link":
            main.original_widget = HardlinkMenu()
        elif action == "remove":
            title = u'Remove file %s' % data['filename']
            main.original_widget = ConfirmAction(title)
    elif (len(browse_stack) == 4):
        if data['action'] == "remove":
            if choice == "Ok":
                f.write("execute %s %s\n" % (data['action'], data['filename']))
            browse_stack.pop()
            browse_stack.pop()
            main.original_widget = browse_stack.pop()
        elif data['action'] == "hard-link":
            title = u'Hard-link file %s to %s' % (data['filename'], data['hard-link_target']['Name'])
            main.original_widget = ConfirmAction(title)
        else:
            log.write("invalid level\n");
    elif len(browse_stack) == 5:
        if data['action'] == "hard-link":
            if choice == "Ok":
                f.write("execute %s %s\n" % (data['action'], data['filename']))
            browse_stack.pop()
            browse_stack.pop()
            browse_stack.pop()
            main.original_widget = browse_stack.pop()
        else:
            log.write("invalid level\n");
    else:
        f.write("no more levels\n")
        browse_stack.pop()
    f.flush()

def browse_out():
    if (len(browse_stack) > 0):
        main.original_widget = browse_stack.pop()
    else:
        print "browse_stack empty"

main = urwid.Padding(DuplicatesWalker(data['duplicates']), left=0, right=0)

def unhandled_input(key):
    if key == 'right':
        widget = main.original_widget
        widget.callback(None)
    elif key == 'left':
        browse_out();
    elif (key == 'q'):
        raise urwid.ExitMainLoop()
    else:
        f.write('unhandled_input\n')

palette = [
    ('body','black','dark cyan', 'standout'),
    ('edit','yellow', 'dark blue'),
    ('editfocus','yellow','dark cyan', 'bold'),
    ('foot','light gray', 'black'),
    ('key','light cyan', 'black', 'underline'),
    ('title', 'white', 'dark blue',),
    ('selected', 'white', 'dark blue'),
    ]

urwid.MainLoop(main, palette, unhandled_input=unhandled_input).run()
