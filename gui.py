#!/usr/bin/env python
import urwid

choices = u'Chapman Cleese Gilliam Idle Jones Palin'.split()

answer = { 'Chapman' : [ "foo", "bar", "test" ],
          'Cleese' : [ 'schma', 'foo'],
          'Gilliam' : [ 'fopo', 'pupu' ]}

browse_stack = []

class Browse(urwid.ListBox):
    def __init__(self, title, choices):
        body = [urwid.Text(title), urwid.Divider()]
        for c in choices:
            button = urwid.Button(c)
            urwid.connect_signal(button, 'click', self.item_chosen, c)
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))
        urwid.ListBox.__init__(self, urwid.SimpleFocusListWalker(body))

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

lbMain = Browse(u'Pythons', choices)
main = urwid.Padding(lbMain, left=2, right=2)

def unhandled_input(k):
    if (k == 'q'):
        raise urwid.ExitMainLoop()

top = urwid.Overlay(main, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
    align='center', width=('relative', 60),
    valign='middle', height=('relative', 60),
    min_width=20, min_height=9)
urwid.MainLoop(top, palette=[('reversed', 'standout', '')], unhandled_input=unhandled_input).run()
#loop = urwid.MainLoop(fill, unhandled_input=show_or_exit)
