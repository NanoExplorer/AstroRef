import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, Gio, GObject, GLib
import os
class AssistantApp:
    def __init__(self,donecallback):
        self.assistant = Gtk.Assistant()
        self.assistant.set_default_size(500, 300)
        self.callback = donecallback
        self.create_page1()
        self.create_page2()
        self.create_page3()

        self.assistant.connect('cancel', self.on_close_cancel)
        self.assistant.connect('close', self.on_close_cancel)
        self.assistant.connect('apply', self.on_apply)
        self.assistant.connect('prepare', self.on_prepare)

        self.assistant.show()

    def on_close_cancel(self, assistant):
        assistant.destroy()
        self.callback()
        if __name__ == '__main__':
            Gtk.main_quit()



    def on_apply(self, assistant):
        os.makedirs(os.path.expanduser('~/.ads/'),exist_ok=True)
        if self.key:
            with open(os.path.expanduser('~/.ads/dev_key'),'w') as devkey:
                devkey.write(self.key)
        self.callback()

    def on_prepare(self, assistant, page):
        current_page = assistant.get_current_page()
        n_pages = assistant.get_n_pages()
        title = 'AstroRef Setup (%d of %d)' % (current_page + 1, n_pages)
        assistant.set_title(title)

    def on_entry_changed(self, widget):
        page_number = self.assistant.get_current_page()
        current_page = self.assistant.get_nth_page(page_number)
        self.key = widget.get_text()

        if self.key:
            self.assistant.set_page_complete(current_page, True)
        else:
            self.assistant.set_page_complete(current_page, False)

    def create_page1(self):
        box = Gtk.VBox(homogeneous=False,
                       spacing=12)
        box.set_border_width(12)
        label = Gtk.Label(label='Welcome to AstroRef! From here you can view your NASA ADS libraries and keep them all in one big .bib file. This assistant will help you set up the program and get started.')
        label.set_line_wrap(True)
        box.pack_start(label, False, False, 0)
        if os.path.isfile(os.path.expanduser('~/.ads/dev_key')):
            box.show_all()
            self.assistant.append_page(box)
            self.assistant.set_page_complete(box,True)
            self.key = False
        else:
            label2 = Gtk.Label()
            label2.set_markup('Please input your ADS dev key in the box below. You can get it from the following page: <a href="https://ui.adsabs.harvard.edu/#user/settings/token" title="ADS dev key">https://ui.adsabs.harvard.edu/#user/settings/token</a>.')
            entry = Gtk.Entry()
            label2.set_line_wrap(True)
            box.pack_start(label2,False,False,0)
            box.pack_start(entry, True, True, 0)
            entry.connect('changed', self.on_entry_changed)
            box.show_all()
            self.assistant.append_page(box)


        self.assistant.set_page_title(box, 'Page 1')
        self.assistant.set_page_type(box, Gtk.AssistantPageType.INTRO)

        pixbuf = self.assistant.render_icon(Gtk.STOCK_DIALOG_INFO,
                                            Gtk.IconSize.DIALOG,
                                            None)

        self.assistant.set_page_header_image(box, pixbuf)

    def create_page2(self):
        box = Gtk.VBox(homogeneous=False,
                       spacing=12)
        box.set_border_width(12)
        label = Gtk.Label(label="To use this app, just create a library at ADS Bumblebee, then add some papers to it, and click the 'refresh' button in this application. \n\nJust be careful - you only get a certain amount of queries per day. You should be able to do at least 100 refreshes per day, so don't worry too much (but also don't refresh after every single paper you add on ADS.)")
        label.set_line_wrap(True)
        box.pack_start(label, False, False, 0)

        box.show_all()

        self.assistant.append_page(box)
        self.assistant.set_page_complete(box, True)
        self.assistant.set_page_title(box, 'Page 2')

        pixbuf = self.assistant.render_icon(Gtk.STOCK_DIALOG_INFO,
                                            Gtk.IconSize.DIALOG,
                                            None)
        self.assistant.set_page_header_image(box, pixbuf)

    def create_page3(self):
        label = Gtk.Label(label='You\'re all set! press "Apply" to apply changes')
        label.show()
        self.assistant.append_page(label)
        self.assistant.set_page_complete(label, True)
        self.assistant.set_page_title(label, 'Confirmation')
        self.assistant.set_page_type(label, Gtk.AssistantPageType.CONFIRM)

        pixbuf = self.assistant.render_icon(Gtk.STOCK_DIALOG_INFO,
                                            Gtk.IconSize.DIALOG,
                                            None)
        self.assistant.set_page_header_image(label, pixbuf)

if __name__ == '__main__':
    AssistantApp(None)
    Gtk.main()