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
        browse_into(self, None)

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
        browse_into(self, None)

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
        browse_into(self, None)

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
        browse_into(self, D.action)

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
        browse_into(self, elt == 'Ok')

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

# (from, to) -> execute side_effect
side_effects = {}

# what to do in given state no matter from where
# typically show some frame
state_effects = {}

# only for non-ambiguity of state machine, automatically change to child state
transient_nodes = []

def child_if_arg(parent, arg):
    match = [ dst for (src, dst, cond) in edges if src == parent and arg == cond]
    if not match:
        return None
    return match[0]

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
delete_confirm = "delete"
#delete_execute = "delete execute"
hardlink_sel_source = "hard link select source"
hardlink_confirm = "hard link confirm"
hardlink_execute = "hard link execute"

edges.append((collisions, filenames, None))
edges.append((filenames, context_menu, None))

# doesn context_menu, filenames, see_file -> multiple (xx, filenames) edge
edges.append((context_menu, see_file, see_file))
edges.append((see_file, context_menu, None))

edges.append((context_menu, delete_confirm, delete_confirm))
edges.append((delete_confirm, filenames, True))
edges.append((delete_confirm, context_menu, False))

edges.append((context_menu, hardlink_sel_source, 'hardlink'))
edges.append((hardlink_sel_source, hardlink_confirm, None))
edges.append((hardlink_confirm, context_menu, False))
edges.append((hardlink_confirm, hardlink_execute, True))
edges.append((hardlink_execute, filenames, None))

transient_nodes.append(see_file)
transient_nodes.append(hardlink_execute)


fcw = CollisionsWalker()
def show_collisions():
    global fcw;
    return fcw

fnm = FilenamesWalker()
def show_filenames():
    global fnm
    return fnm

state_effects[collisions] = show_collisions
state_effects[filenames] = show_filenames
state_effects[context_menu] = lambda: ContextMenu(main.original_widget,
                                                   ['see', 'delete', 'hardlink'])
state_effects[delete_confirm] = lambda: ConfirmAction(delete_confirm,
                                                     main.original_widget)
state_effects[hardlink_sel_source] = lambda: HardlinkMenu(main.original_widget)

def hardlink_confirm_title():
    return u'Hard-link file %s to %s' % (D.filename, D.hardlink_target['Name'])
state_effects[hardlink_confirm] = lambda: ConfirmAction(hardlink_confirm_title(),
                                                       main.original_widget)

def update_filenames(edge, arg):
    # check if differs
    f.write("browse into filenames\n")
    filenames = Storage.files_by_crc32(D.collision['crc32'])
    D.filenames = filenames.fetchall()

def update_collisions(edge, choice):
    f.write("browse out filenames\n")

def remove_if(edge, confirmed):
    Action.remove(D.filename)
    Representation.update_filenames()

def action_see(edge, arg):
    f.write("see %s\n" % re.escape(D.filename))
    os.system("see %s" % re.escape(D.filename))

side_effects[(collisions, filenames)] = update_filenames
side_effects[(filenames, collisions)] = update_collisions
side_effects[(delete_confirm, filenames)] = remove_if
side_effects[(context_menu, see_file)] = action_see

cur_node = collisions

def transition(src, dst, arg):
    f.write('transition [%s -> %s]\n' % (src, dst))

    if side_effects.has_key((src, dst)):
        f.write('side effects %s\n' % dst)
        side_effects[(src, dst)]((src, dst), arg)

    if state_effects.has_key(dst):
        f.write('frame %s\n' % dst)
        main.original_widget = state_effects[dst]()

def browse_into(widget, arg):
    global cur_node
    f.write('[browse into] cur:%s level:%d arg:%r\n' %
            (cur_node, len(browse_stack), arg))

    browse_stack.append(widget)
    child = child_if_arg(cur_node, arg)
    f.write("sel child: %s\n" % child)

    if child:
        transition(cur_node, child, arg)
        cur_node = child

        if cur_node in transient_nodes:
            child = child_if_arg(cur_node, None)
            transition(cur_node, child, None)
            cur_node = child

    elif (len(browse_stack) == 3):
        action = D.action
        if action == "hard-link":
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
            f.write("invalid level\n");

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
            f.write("invalid level\n");
    else:
        f.write("no more levels\n")
        browse_stack.pop()
    f.flush()

def browse_out():
    global cur_node
    f.write('[browse out] cur:%s level:%d\n' %
            (cur_node, len(browse_stack)))

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

main = urwid.Padding(state_effects[cur_node](), left=0, right=0)

urwid.MainLoop(main, palette, unhandled_input=unhandled_input).run()
