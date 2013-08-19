#!/usr/bin/env python
import urwid
import storage
import sys

f = open('/tmp/log.txt', 'w+')

browse_stack = []

class DuplicatesWalker(urwid.ListWalker):
    def __init__(self):
        self.db = storage.Storage()
        storage.build_test_corpus(self.db)
        self.duplicates = self.db.duplicates().fetchall()
        self.focus = (0, self.duplicates[0])

    def _get_at_pos(self, focus):
        (idx, invalid) = focus
        cur = self.duplicates[idx]
        text = urwid.Button("%d %d %s" % (idx, cur['Count'], cur['Name']))
        return urwid.AttrMap(text, 'edit', 'editfocus'), (idx, cur)

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

class DuplicatesDetailsWalker(DuplicatesWalker):
    def __init__(self, sha1):
        self.db = storage.Storage()
        storage.build_test_corpus(self.db)
        self.duplicates = self.db.filenames(sha1).fetchall()
        self.focus = (0, self.duplicates[0])
        for row in self.db.filenames('9db39b5c8b9eb70149801f8c9112c3ef50dcd562'):
            f.write('__init__ %s %s\n' % (row['sha1'], row['Name']))
        f.flush()

    def _get_at_pos(self, focus):
        (idx, invalid) = focus
        cur = self.duplicates[idx]
        text = urwid.Button("%d %s" % (idx, cur['Name']))
        return urwid.AttrMap(text, 'edit', 'editfocus'), (idx, cur)



class Browse(urwid.WidgetWrap):
    def __init__(self, title, walker):
        self.walker = walker
        self.listbox = urwid.ListBox(self.walker)
        self.frame = urwid.Frame( self.listbox)
        urwid.WidgetWrap.__init__(self, self.frame)

    def get_focus_label(self):
        (idx, elt) = self.walker.focus
        f.write('get_focus_label sha1: %s\n' % elt['sha1'])
        f.flush()
        return elt

    def keypress(self, size, key):
        f.write('Browse keypress %s\n' % str(key))
        f.flush()
        print "browse stack %d" % len(browse_stack)
        if key == 'right':
            browse_into(self, self.get_focus_label())
        elif key == 'left':
            browse_out();
        else:
            return self.frame.keypress(size, key)

    def item_chosen(self, button, choice):
        print "pass"
        browse_into(self, choice)

class ShowItemChosen(urwid.Filler):
    def __init__(self, choice):
        response = urwid.Text([u'You chose ', choice, u'\n'])
        done = urwid.Button(u'Ok')
        urwid.connect_signal(done, 'click', exit_program)
        urwid.Filler.__init__(self, urwid.Pile([response, urwid.AttrMap(done, None,
                                                                   focus_map='reversed')]))

    def keypress(self, size, key):
        print key
        print "browse stack %d" % len(browse_stack)
        if key == 'left':
            browse_out();
        else:
            return key

def browse_into(widget, choice):
    f.write('browse_into %s\n' % choice)
    browse_stack.append(widget)
    if (len(browse_stack) > 1):
        main.original_widget = ShowItemChosen(choice)
    else:
        main.original_widget = Browse(choice, DuplicatesDetailsWalker(choice['sha1']))

def browse_out():
    if (len(browse_stack) > 0):
        print "apply"
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
    align='center', width=('relative', 60),
    valign='middle', height=('relative', 60),
    min_width=20, min_height=9)
urwid.MainLoop(top, palette, unhandled_input=unhandled_input).run()
#loop = urwid.MainLoop(fill, unhandled_input=show_or_exit)
