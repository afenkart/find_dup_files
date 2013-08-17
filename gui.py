#!/usr/bin/env python
import urwid
import storage

choices = u'Chapman Cleese Gilliam Idle Jones Palin'.split()

answer = { 'Chapman' : [ "foo", "bar", "test" ],
          'Cleese' : [ 'schma', 'foo'],
          'Gilliam' : [ 'fopo', 'pupu' ]}

browse_stack = []

class NumericLayout(urwid.TextLayout):
    """
    TextLayout class for bottom-right aligned numbers
    """
    def layout( self, text, width, align, wrap ):
        """
        Return layout structure for right justified numbers.
        """
        lt = len(text)
        r = lt % width # remaining segment not full width wide
        if r:
            linestarts = range( r, lt, width )
            return [
                # right-align the remaining segment on 1st line
                [(width-r,None),(r, 0, r)]
                # fill the rest of the lines
                ] + [[(width, x, x+width)] for x in linestarts]
        else:
            linestarts = range( 0, lt, width )
            return [[(width, x, x+width)] for x in linestarts]

class DuplicatesWalker(urwid.ListWalker):
    def __init__(self):
        self.db = storage.Storage()
        storage.build_test_corpus(self.db)
        self.focus = 0
        self.duplicates = self.db.duplicates().fetchall()
        self.numeric_layout = NumericLayout()

    def _get_at_pos(self, idx):
        foo = self.duplicates[idx]
        return urwid.Text("%d %s" % (idx, foo['Name']), layout=self.numeric_layout), idx

    def get_focus(self): 
        return self._get_at_pos(self.focus)

    def set_focus(self):
        self.focus = focus
        self._modified()
 
    def get_next(self, idx):
        print len(self.duplicates)
        if idx >= len(self.duplicates) - 1:
            return (None, None)
        return self._get_at_pos(idx + 1)

    def get_prev(self, idx):
        if (idx <= 1):
            return (None, None)
        return self._get_at_pos(idx - 1)


class Browse(urwid.ListBox):
    def __init__(self, title, choices):
        urwid.ListBox.__init__(self, DuplicatesWalker())

    def get_focus_label(self):
        widget = self.focus 
        while widget.focus:
            widget = widget.focus
        widget = widget.base_widget;
        return widget.get_label()

    def keypress(self, size, key):
        print key
        print "browse stack %d" % len(browse_stack)
        if key == 'right':
            browse_into(self, self.get_focus_label())
        elif key == 'left':
            browse_out();
        else:
            return self.__super.keypress(size, key)

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
    browse_stack.append(widget)
    if (len(browse_stack) > 1):
        main.original_widget = ShowItemChosen(choice)
    else:
        main.original_widget = Browse(choice, answer[choice])

def browse_out():
    if (len(browse_stack) > 0):
        print "apply"
        main.original_widget = browse_stack.pop()
    else:
        print "browse_stack empty"

def exit_program(button):
    raise urwid.ExitMainLoop()

main = urwid.Padding(Browse(u'Pythons', choices), left=2, right=2)

def unhandled_input(k):
    if (k == 'q'):
        raise urwid.ExitMainLoop()

palette = [
    ('body','black','dark cyan', 'standout'),
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
