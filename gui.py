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
    'duplicates': Storage.duplicates(1024 * 1024).fetchall()
}

class MenuButton(urwid.Button):
    def __init__(self, caption, callback):
        super(MenuButton, self).__init__("")
        #urwid.connect_signal(self, 'click', callback)
        self._w = urwid.AttrMap(urwid.SelectableIcon(
            [" ", caption], 2), 'None', 'selected')

class MyListWalker(urwid.ListWalker):
    def __init__(self, data, render_fun):
        self.data = data
        self.render_fun = render_fun
        self.focus = 0

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
        return MenuButton(self.render_fun(self.data[idx]), None)

class DuplicatesWalker(MyListWalker):
    def __init__(self, duplicates):
        skip = len("/home/afenkart")
        render_fun = lambda x: "%2d %7dk %s" % (x['Count'], x['st_size']/1000,
                                                x['Name'][skip:])
        MyListWalker.__init__(self, duplicates, render_fun)

class DuplicatesWithFilenamesWalker(MyListWalker):
    def __init__(self, filenames):
        render_fun = lambda x: "%d %s" % (x['st_inode'], x['Name'])
        MyListWalker.__init__(self, filenames, render_fun)

def createSimpleFocusListWalker(title, elts):
    body = [urwid.Text(title), urwid.Divider()]
    for c in elts:
        button = urwid.Button(c)
        widget = urwid.AttrMap(button, 'edit', 'editfocus')
        body.append(widget)
    return urwid.SimpleFocusListWalker(body)

options = u'see remove hard-link'.split()
def createChoicesWalker(filename):
    return createSimpleFocusListWalker(filename, options)

ok_cancel = ['Ok', 'Cancel']
def createConfirmAction(choice):
    title = u'You chose %s\n' % choice
    return createSimpleFocusListWalker(title, ok_cancel)

class Browse(urwid.WidgetWrap):
    def __init__(self, title, walker):
        self.walker = walker
        self.listbox = urwid.ListBox(self.walker)
        self.frame = urwid.Frame( self.listbox)
        urwid.WidgetWrap.__init__(self, self.frame)

    def get_elt(self):
        #f.write("get_elt %s\n" % type(self.walker))
        if len(browse_stack) == 0:
            return data['duplicates'][self.walker.focus]
        if len(browse_stack) == 1:
            f.write("get_elt %s\n" % data['filenames'][self.walker.focus])
            return data['filenames'][self.walker.focus]['Name']
        elif len(browse_stack) == 2:
            return options[self.walker.focus - 2]
        elif len(browse_stack) == 3:
            return ok_cancel[self.walker.focus - 2]
        else:
            assert(False);

    def keypress(self, size, key):
        #f.write('Browse keypress %s\n' % str(key))
        if key == 'right' or key == 'enter':
            browse_into(self, self.get_elt())
        elif key == 'left':
            browse_out();
        else:
            return self.frame.keypress(size, key)

def browse_into(widget, choice):
    browse_stack.append(widget)
    f.write('browse_into %s level %d\n' % (choice, len(browse_stack)))
    if (len(browse_stack) == 1):
        data['crc32'] = choice['crc32']
        data['sha1'] = choice['sha1']
        data['filenames'] = Storage.files_by_crc32(data['crc32']).fetchall()
        main.original_widget = Browse(choice,
                                      DuplicatesWithFilenamesWalker(data['filenames']))
    elif (len(browse_stack) == 2):
        filename = choice
        data['filename'] = filename
        main.original_widget = Browse(choice, createChoicesWalker(filename))
    elif (len(browse_stack) == 3):
        action = choice
        data['action'] = choice
        if (action == "see"):
            f.write("see %s\n" % re.escape(data['filename']))
            os.system("see %s" % re.escape(data['filename']))
            browse_stack.pop()
        else:
            main.original_widget = Browse(choice, createConfirmAction(action))
    elif (len(browse_stack) == 4):
        ok_cancel = (choice == "Ok")
        f.write("execute %s %s\n" % (data['action'], store['filename']))
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

main = urwid.Padding(Browse(u'Pythons', DuplicatesWalker(data['duplicates'])),
                     left=0, right=0)

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
    ('selected', 'white', 'dark blue'),
    ]

top = urwid.Overlay(main, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
    align='center', width=('relative', 100),
    valign='middle', height=('relative', 100),
    min_width=20, min_height=9)
urwid.MainLoop(top, palette, unhandled_input=unhandled_input).run()
#loop = urwid.MainLoop(fill, unhandled_input=show_or_exit)
