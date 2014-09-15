#!/usr/bin/env python
import urwid
import sys, os
import re

import storage
from observable import ObservableProperty

f = open('/tmp/log_gui.txt', 'w+', False)

SKIP_PREFIX = "/home/afenkart/"
MIN_FILESIZE = 0

Storage = storage.Storage(memory=False)
Storage.create_indices()

browse_stack = []
class Data(object):
    # collisions represented by first filename
    collisions = ObservableProperty(list())

    # collision row to be resolved
    collision = ObservableProperty(list())

    # all filenames of selected collision
    filenames = ObservableProperty(list())

    # filename target of action
    filename = ObservableProperty(str())

    # hard-link to file
    hardlink_target = ObservableProperty(None)

    # selected action, used to confirm
    action = ObservableProperty()

D = Data()
D.collisions = Storage.duplicates(MIN_FILESIZE).fetchall()

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

class CollisionsWalker(urwid.WidgetWrap):
    def __init__(self):
        render_fun = lambda x: "%2d %7dk %s" % (x['Count'], x['st_size']/1000,
                                                strip_prefix(x['Name']))

        Data.collisions.observe(self.update)
        self.walker = MyListWalker(D.collisions, render_fun, self.callback)
        urwid.WidgetWrap.__init__(self, urwid.ListBox(self.walker))

    def callback(self, widget):
        index = self._w.focus_position
        row = D.collisions[index]
        D.collision = row
        f.write("button callback %r %r\n" % (row['crc32'], row['sha1']))
        browse_into(self, None, None)

    def update(self):
        f.write("CollisionsWalker data changed")
        self.walker.data = D.collisions
        if self.walker.focus >= len(D.collisions):
            self.walker.focus -= 1;


class FilenamesWalker(urwid.WidgetWrap):
    def __init__(self):
        render_fun = lambda x: "%d %s" % (x['st_inode'], x['Name'])
        Data.filenames.observe(self.update)
        self.walker = MyListWalker(D.filenames, render_fun, self.callback)
        urwid.WidgetWrap.__init__(self, urwid.ListBox(self.walker))

    def callback(self, widget):
        index = self._w.focus_position
        D.filename = D.filenames[index]['Name']
        f.write("button callback %r\n" % D.filename)
        browse_into(self, None, None)

    def update(self):
        # self.walker.focus
        f.write("FilenamesWalker data changed\n")
        self.walker.data = D.filenames
        if self.walker.focus >= len(D.collisions):
            self.walker.focus -= 1;
        self.walker._modified()

class HardlinkMenu(urwid.WidgetWrap):
    def __init__(self, overlay_parent):
        hardlinks = [x for x in D.filenames if x['Name'] != D.filename]
        render_fun = lambda x: "%d %s" % (x['st_inode'], x['Name'])
        self.walker = MyListWalker(hardlinks, render_fun, self.callback)
        self.hardlinks = hardlinks

        title = "hard-link file %s to:" % D.filename
        pile = urwid.Pile([urwid.AttrMap(urwid.Text(title), 'title'),
                           urwid.Divider()])
        pile.selectable = False
        self.frame = urwid.Frame(urwid.ListBox(self.walker),
                                 header = pile)

        self.overlay = urwid.Overlay(self.frame,
                                     overlay_parent,
                                   align='center', width=('relative', 90),
                                   valign='middle', height=('relative', 60),
                                   min_width=20, min_height=9)
        urwid.WidgetWrap.__init__(self, self.overlay)

    def callback(self, widget):
        index = self.walker.focus
        row = self.hardlinks[index]
        f.write("button callback %r\n" % self.hardlinks[index]['Name'])
        D.hardlink_target = row
        browse_into(self, None, None)

class ContextMenu(urwid.WidgetWrap):
    def __init__(self, overlay_parent, options):
        self.title = urwid.Text(strip_prefix(D.filename))
        Data.filename.observe(self.set_title)

        self.children = options
        body = [MenuButton(c, self.callback) for c in options]
        self.walker = urwid.SimpleFocusListWalker(body)

        pile = urwid.Pile([urwid.AttrMap(self.title, 'title'),
                           urwid.Divider()])

        self.frame = urwid.Frame(urwid.ListBox(self.walker),
                                             header = pile)
        self.overlay = urwid.Overlay(self.frame,
                                     overlay_parent,
                                     align='center', width=('relative', 80),
                                     valign='middle', height=('relative', 60),
                                     min_width=20, min_height=9)
        urwid.WidgetWrap.__init__(self, self.overlay)

    def callback(self, widget):
        D.action = self.children[self.walker.focus]
        f.write("button callback %r\n" % D.action)
        browse_into(self, D.action, None)

    def set_title(self):
        f.write("ContextMenu update title\n")
        self.title.set_text(strip_prefix(D.filename))

def createSimpleListWalker(title, elts, callback):
    body = [urwid.AttrMap(urwid.Text(title), 'title', 'None')]
    body.append(urwid.Divider())
    body.extend([MenuButton(c, callback) for c in elts])
    return urwid.SimpleFocusListWalker(body)

class ConfirmAction(urwid.WidgetWrap):
    def __init__(self, title, overlay_parent):
        f.write("confirm action %s\n" % title)
        self.title = title
        self.ok_cancel = ['Ok', 'Cancel']
        self.walker = createSimpleListWalker(title, self.ok_cancel,
                                             self.callback)
        self.frame = urwid.Overlay(urwid.ListBox(self.walker),
                                   overlay_parent,
                                   align='center', width=('relative', 80),
                                   valign='bottom', height=('relative', 30),
                                   min_width=20, min_height=9)
        urwid.WidgetWrap.__init__(self, self.frame)

    def callback(self, widget):
        f.write("button callback %r\n" % self._w.focus.focus_position)
        elt = self.ok_cancel[self.walker.focus - 2]
        browse_into(self, None, elt == 'Ok')

class Action:
    @staticmethod
    def hardlink(source, linkname):
        f.write("hard link %s\n" % (linkname))
        os.unlink(linkname)
        os.link(source, linkname)
        Storage.replace_with_hardlink(source, linkname)

    @staticmethod
    def remove(filename):
        f.write("do remove %s\n" % (filename))
        os.remove(filename)
        Storage.remove_file(filename)

class Representation:
    @staticmethod
    def update_filenames():
        f.write("update filenames\n")
        filenames = Storage.files_by_crc32(D.collision['crc32'])
        D.filenames = filenames.fetchall()
        Representation.update_collisions()

    @staticmethod
    def update_collisions():
        f.write("update collisions\n")
        coll = D.collisions

        s = set([(c['st_dev'], c['st_inode']) for c in D.filenames])
        if len(s) == D.collision['Count']:
            f.write("no change in collision count\n")
            return

        # can't change sqlite.row element
        D.collisions = Storage.duplicates(MIN_FILESIZE).fetchall()

# (parent, child)
edges = []

# no all nodes have frames
frames = {}
frames_create = {}

# (from, to) -> execute side_effect
side_effects = {}

def child_of(parent):
    match = filter(lambda edge: edge[0] == parent, edges)
    if not match:
        return None
    edge = match[0]
    return edge[1]

def parent_of(child):
    match = filter(lambda edge: edge[1] == child, edges)
    if not match:
        return None
    edge = match[0]
    return edge[0]

# navigation graph
collisions = "collisions"
filenames = "filenames"
context_menu = "actions"
see_file = "see"
hardlink_file = "hard link"
delete_confirm = "delete"
hardlink_confirmed = "hard link confirmed"

edges.append((collisions, filenames))
edges.append((filenames, context_menu))
edges.append((context_menu, see_file))
edges.append((context_menu, delete_confirm))
edges.append((context_menu, hardlink_file))
edges.append((delete_confirm, filenames))

frames[collisions] = CollisionsWalker()
frames[filenames] = FilenamesWalker()

frames_create[context_menu] = lambda x: ContextMenu(frames[filenames],
                                                   ['see', 'delete', 'hardlink'])
frames_create[delete_confirm] = lambda x: ConfirmAction(delete_confirm,
                                                     main.original_widget)
#frames[hardlink_file] = lambda x: HardlinkMenu(frames[context])


def update_filenames(edge, arg):
    # check if differs
    f.write("browse into filenames\n")
    filenames = Storage.files_by_crc32(D.collision['crc32'])
    D.filenames = filenames.fetchall()

def remove_if(edge, confirmed):
    if confirmed:
        Action.remove(D.filename)
        Representation.update_filenames()

side_effects[(collisions, filenames)] = update_filenames
side_effects[(delete_confirm, filenames)] = remove_if

def browse_collisions(choice):
    f.write("browse out filenames\n")
side_effects[(filenames, collisions)] = browse_collisions

cur_node = collisions

def browse_into(widget, child, arg):
    global cur_node
    parent = cur_node
    browse_stack.append(widget)
    f.write('browse_into level %d\n' % (len(browse_stack)))

    if not child:
        child = child_of(cur_node)

    if child:
        f.write('activate child %s\n' % child)

        if side_effects.has_key((parent, child)):
            f.write('side effects %s\n' % child)
            side_effects[(parent, child)]((parent, child), arg)

        if (frames.has_key(child)):
            f.write('frame %s\n' % child)
            main.original_widget = frames[child]

        if (frames_create.has_key(child)):
            f.write('frame create %s\n' % child)
            main.original_widget = frames_create[child](None)

        cur_node = child

    elif (len(browse_stack) == 3):
        action = D.action
        if (action == "see"):
            f.write("see %s\n" % re.escape(D.filename))
            os.system("see %s" % re.escape(D.filename))
            browse_stack.pop()
        elif action == "hard-link":
            main.original_widget = HardlinkMenu(browse_stack[-1])
        elif action == "remove":
            title = u'Remove file %s' % D.filename
            main.original_widget = ConfirmAction(title)

    elif (len(browse_stack) == 4):
        if D.action == "remove":
            f.write("- selected action %s\n" % D.action)
            if choice == "Ok":
                Action.remove(D.filename)
                Representation.update_filenames()
            else:
                f.write("remove not confirmed")
            browse_stack.pop()
            browse_stack.pop()
            main.original_widget = browse_stack.pop()
        elif D.action == "hard-link":
            title = u'Hard-link file %s to %s' % (D.filename,
                                                  D.hardlink_target['Name'])
            main.original_widget = ConfirmAction(title)
        else:
            log.write("invalid level\n");

    elif len(browse_stack) == 5:
        if D.action == "hard-link":
            if choice == "Ok":
                Action.hardlink(D.hardlink_target['Name'], D.filename)
                Representation.update_filenames()
            else:
                f.write("remove not confirmed")
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
    global cur_node
    if (len(browse_stack) > 0):
        main.original_widget = browse_stack.pop()
        cur_node = parent_of(cur_node)
    else:
        print "browse_stack empty"

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

main = urwid.Padding(frames[collisions], left=0, right=0)

urwid.MainLoop(main, palette, unhandled_input=unhandled_input).run()

print "foo"
