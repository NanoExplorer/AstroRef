#!/bin/python
# Needs to be able to display and edit the records in the Bibliography as a user interface.
# Good references:
# https://lazka.github.io/pgi-docs/#Gtk-3.0/classes/ListBoxRow.html#Gtk.ListBoxRow
# http://python-gtk-3-tutorial.readthedocs.io/en/latest/layout.html?highlight=scroll
#

# it feels 'wrong' but I think the best way to manage everything is to simply call the bibliography
# update method using a thread. We'll want to lock the user out using a different method until
# it is done, because we can't let them edit anything while ADS is fetching.

import gi
import json
import sys
import traceback
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, Gio, GObject, GLib,Gdk
import threading
import management
import os
import tutorial as setup
import subprocess
import webbrowser
import ads
from errors import InternalServerError, APILimitError, UnauthorizedError
import requests
from pylatexenc.latex2text import LatexNodes2Text
ID_CHANGED_MESSAGE = """Unfortunately, due to the way this program handles paper names,
the names can sometimes change. Since these names are used by your .tex files,
it is necessary that you be informed when changes to these names are made. 

The naming scheme is firstauthorYearSmallLetter, i.e. Atek2007a. The small letter is the 
problem - if you add one paper written by Atek and then cite it in your tex file and come 
back and add another paper written by Atek in the same year, this program will rename 
Atek2007 to Atek2007a or b, and add the new reference as Atek2007b or a. Subsequent additions
of papers will have a similar effect. 

Below is a list of all changed names, with the old name on the left and the new name on the 
right. These names are not ordered in any order, so if b -> c and c -> d, you'll want to 
rename c to d before b to c, if you're using your editor's find and replace tool.
"""
import platform
# Todo:
# maybe remove deleted libraries from sidebar? That's more of a management.py problem 

DOI_PROVIDER = "https://doi-org.proxy.library.cornell.edu/"
# If you're on a University network, the following line should work, depending on how your
# university's library is set up:
# DOI_PROVIDER = "https://doi.org/"
# Alternatively you can set the program to prefer the arXiv for downloading pdfs:
PREFER_ARXIV = False
#ADS_PDF = "http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode={}&link_type=ARTICLE"
ADS_PDF = "https://ui.adsabs.harvard.edu/link_gateway/{}/PUB_PDF"

MENU_XML = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="app-menu">
    <section>
      <attribute name="label" translatable="yes">Change label</attribute>
      <item>
        <attribute name="action">win.change_label</attribute>
        <attribute name="target">String 1</attribute>
        <attribute name="label" translatable="yes">String 1</attribute>
      </item>
      <item>
        <attribute name="action">win.change_label</attribute>
        <attribute name="target">String 2</attribute>
        <attribute name="label" translatable="yes">String 2</attribute>
      </item>
      <item>
        <attribute name="action">win.change_label</attribute>
        <attribute name="target">String 3</attribute>
        <attribute name="label" translatable="yes">String 3</attribute>
      </item>
    </section>
    <section>
      <item>
        <attribute name="action">win.maximize</attribute>
        <attribute name="label" translatable="yes">Maximize</attribute>
      </item>
    </section>
    <section>
      <item>
        <attribute name="action">app.about</attribute>
        <attribute name="label" translatable="yes">_About</attribute>
      </item>
      <item>
        <attribute name="action">app.quit</attribute>
        <attribute name="label" translatable="yes">_Quit</attribute>
        <attribute name="accel">&lt;Primary&gt;q</attribute>
    </item>
    </section>
  </menu>
</interface>
"""


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sidebarVisible = True
        (
            self.COLUMN_AUTHOR,
            self.COLUMN_JOURNAL,
            self.COLUMN_MONTH,
            self.COLUMN_YEAR,
            self.COLUMN_TITLE,
            self.COLUMN_VOLUME,
            self.COLUMN_PAGES,
            self.COLUMN_BIBCODE,
            self.COLUMN_ID
        ) = range(9)

        self.COLUMN_TITLES = [
            "Author",
            "Journal",
            "Month",
            "Year",
            "Title",
            "Vol",
            "Pages",
            "Bibcode",
            "ID"]

        max_action = Gio.SimpleAction.new_stateful(
            "maximize", None, GLib.Variant.new_boolean(False)
        )
        max_action.connect("change-state", self.on_maximize_toggle)
        self.add_action(max_action)

        # Keep it in sync with the actual state
        self.connect(
            "notify::is-maximized",
            lambda obj, pspec: max_action.set_state(
                GLib.Variant.new_boolean(obj.props.is_maximized)
            ),
        )

        try:
            with open('windowprefs.json', 'r') as prefsfile:
                prefs = json.loads(prefsfile.read())
            self.sidebarVisible = prefs['sb']
            size = prefs['size']
            self.columnwidths = prefs['colwidths']
            global PREFER_ARXIV
            PREFER_ARXIV = prefs['arxiv']
        except:
            # print(traceback.format_exc())
            self.sidebarVisible = True
            self.columnwidths = [50, 54, 54, 39, 50, 34, 50, 70, -1] 
            # set some arbitrary widths 
            # should be good enough for a starting point at least.
            size = (800, 600)

        self.library_filter_name = None
        self.bib = management.Bibliography()

        self.connect('delete-event', self.on_quit)
        self.set_default_size(*size)
        self.syncing = False
        self.add_headerbar()

        # Make top level box that will contain all other widgets
        self.box = Gtk.Box(
            spacing=10,
            orientation=Gtk.Orientation.HORIZONTAL,
            homogeneous=False
        )
        self.add(self.box)

        self.make_sidebar()

        self.rbox = Gtk.Box(
            spacing=10,
            orientation=Gtk.Orientation.VERTICAL,
            homogeneous=False
        )
        self.box.pack_start(self.rbox, True, True, 0)
        self.create_list_model()
        self.make_treeview()
        self.make_infobox()

        if self.bib.firstRun:
            # Done I think: check if bib.firstRun and popup with a welcome screen
            setup.AssistantApp(self.setupDone)
        else:
            self.setupDone()
        self.populate_sidebar()
        self.setSidebarStuff(self.sidebarbtn)

    def on_change_label_state(self, action, value):
        action.set_state(value)
        self.label.set_text(value.get_string())

    def on_maximize_toggle(self, action, value):
        action.set_state(value)
        if value.get_boolean():
            self.maximize()
        else:
            self.unmaximize()

    def create_list_model(self):
        self.listStore = Gtk.ListStore(
            str,
            str,
            str,
            GObject.TYPE_INT,
            str,
            GObject.TYPE_INT,
            str,
            str,
            str
        )
        # Done I think : copy data from bib database to list store
        for paperID in self.bib.bibDatabase:
            paper = self.bib.bibDatabase[paperID]
            try:
                self.listStore.append(makeListStoreElement(paper))
            except KeyError:
                print("KeyError in create_list_model(). Paper ID: '{}'".format(paperID))
        self.library_filter = self.listStore.filter_new()
        self.library_filter.set_visible_func(self.library_filter_func)
        self.sorted_and_filtered = Gtk.TreeModelSort(model=self.library_filter)
        # I need a better filter solution than this. I have to pass the filter into the 
        # treeview, so it's hard to layer filters. 

    def treeview_copy(self, widget, ev, data=None):
        if Gdk.ModifierType.CONTROL_MASK & ev.state != 0 and ev.hardware_keycode==54 and ev.keyval == 99:
            # User pressed ctrl-c
            c = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            text = ""
            tm, tp = widget.get_selection().get_selected_rows()
            for t in tp:
                text = text + self.sorted_and_filtered[t.get_indices()[0]][8] + ','
            c.set_text(text.strip(','), -1)
            print("copied {}".format(text))
        elif Gdk.ModifierType.CONTROL_MASK & ev.state != 0 and ev.hardware_keycode==53 and ev.keyval == 120:
            # user pressed ctrl-x
            c = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            text = ""
            tm, tp = widget.get_selection().get_selected_rows()
            for t in tp:
                text = text + self.sorted_and_filtered[t.get_indices()[0]][7] + '\n'
            c.set_text(text.strip(), -1)
            print("copied {}".format(text))
        else:
            print(ev.state, ev.hardware_keycode, ev.keyval)

    def treeview_open(self, widget, path, column):
        pdf_file = self.bib.getDefaultPdf(
            self.sorted_and_filtered[path.get_indices()][7]
        )
        if pdf_file:
            if platform.system() == "Darwin":
                subprocess.call(('open', pdf_file))
            else:
                subprocess.call(('xdg-open', pdf_file))

    """def treeview_rtclick(self,widget,event):
        if event.button == 3:
            path,_,_,_ = widget.get_path_at_pos(int(event.x),int(event.y))
            treeiter = self.sorted_and_filtered.get_iter(path)
            action_group=Gio.SimpleActionGroup()
            print("got this far...")
            action_group.insert("something?") #segfault
            treeiter.insert_action_group(action_group)
            menu = Gtk.Menu()
            menu.attach_to_widget(treeiter)
            menu.popup()"""

    def search_tree(self, model, column, key, tree_iter, search_data=None):
        author, title = model.get(tree_iter, 0, 4)  
        # 0=author and 4=title columns

        if key.lower() in (author+title).lower():
            return False
        return True

    def make_treeview(self):
        tvsw = Gtk.ScrolledWindow()
        tvsw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.rbox.pack_start(tvsw, True, True, 0)
        treeview = Gtk.TreeView(model=self.sorted_and_filtered)
        treeview.connect("key-press-event", self.treeview_copy)
        treeview.set_activate_on_single_click(False)
        treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        treeview.connect("row-activated", self.treeview_open)
        treeview.set_search_equal_func(self.search_tree)

        # treeview.connect("button-press-event",self.treeview_rtclick)
        tvsw.add(treeview)
        self.columns = []
        for column_num in range(9):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(self.COLUMN_TITLES[column_num],
                                        renderer,
                                        text=column_num)
            column.set_sort_column_id(column_num)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            if column_num == self.COLUMN_ID:
                column.set_resizable(False)
            else:
                column.set_resizable(True)
            column.set_fixed_width(self.columnwidths[column_num])
            treeview.append_column(column)
            self.columns.append(column)

    def make_infobox(self):
        pass

    def make_sidebar(self):
        self.sidebarscrolledwindow = Gtk.ScrolledWindow()
        self.sidebarscrolledwindow.set_size_request(300, 400)
        self.sidebarscrolledwindow.set_policy(
            Gtk.PolicyType.NEVER, 
            Gtk.PolicyType.AUTOMATIC
        )
        self.box.pack_start(self.sidebarscrolledwindow, False, False, 0)

        self.sidebar = Gtk.ListBox()
        self.sidebar_num_rows = 0
        self.sidebarscrolledwindow.add(self.sidebar)

    def add_headerbar(self):
        """ Add the header bar to the window. The header bar includes options such as close,
        refresh, and hide/show sidebar. Because of differences between different versions of gtk, 
        it has to check which version is being used and adjust automatically. In versions earlier than 11
        the headerbar cannot show minimize and maximize buttons by itself. I cannot implement a maximize
        button, but I always maximize a window by slamming it into the top of the screen anyway, so
        I only implement a minimze button.

        Note: The reason I cannot implement a maximize button is because it is hard to 
        know whether the window is currently maximized. Usually maximize buttons will also change to
        restore buttons when the window is maximized, but I cannot do that."""
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)

        if Gtk.get_minor_version() < 11:
            # I guess in old versions of Gtk the headerbar doesn't automatically show the minimize and
            # maximize buttons. This is a really bad kludge, but since I'm leaving my laptop on Linux 
            # Mint 17 and not upgrading to 18, it's really necessary. 

            minimize = Gtk.Button()
            minimizeIcon = Gio.ThemedIcon(name='window-minimize-symbolic')
            minimizeImage = Gtk.Image.new_from_gicon(minimizeIcon, Gtk.IconSize.BUTTON)
            minimize.add(minimizeImage)
            minimize.connect('clicked', lambda x: self.iconify())
            hb.pack_end(minimize)

            # Also this version of GTK is too old to let me know if the window is maximized.
            # It looks like there is a way, but I can't get it to work. So I'll just leave
            # out the maximize button on old versions of GTK.
            """
            maximize = Gtk.Button()
            maximizeIcon = Gio.ThemedIcon(name='window-maximize-symbolic')
            self.maximizeImage = Gtk.Image.new_from_gicon(maximizeIcon,Gtk.IconSize.BUTTON)
            unmaximizeIcon = Gio.ThemedIcon(name='view-restore-symbolic')
            self.unmaximizeImage = Gtk.Image.new_from_gicon(unmaximizeIcon,Gtk.IconSize.BUTTON)

            maximize.set_image(self.maximizeImage)
            maximize.connect('clicked',self.maximizeHandler)
            hb.pack_end(maximize)"""
        else:
            if platform.system() == "Darwin":
                hb.set_decoration_layout("close,minimize,maximize:")
            else:
                hb.set_decoration_layout(":minimize,maximize,close")
        hb.props.title = "AstroRef"
        self.set_titlebar(hb)
        self.set_icon_from_file('icon.svg')

        self.sidebarbtn = Gtk.Button()
        sidebarIcon = Gio.ThemedIcon(name='sidebar-show-symbolic')
        self.hideSidebarImage = Gtk.Image.new_from_gicon(sidebarIcon, Gtk.IconSize.BUTTON)
        self.showSidebarImage = Gtk.Image.new_from_gicon(sidebarIcon, Gtk.IconSize.BUTTON)
        self.sidebarbtn.set_has_tooltip(True)
        self.sidebarbtn.set_tooltip_text("Show/hide sidebar")

        self.sidebarbtn.connect('clicked', self.sidebarToggle)
        hb.pack_start(self.sidebarbtn)

        self.syncButton = Gtk.Button()
        syncIcon = Gio.ThemedIcon(name='view-refresh-symbolic')
        self.syncImage = Gtk.Image.new_from_gicon(syncIcon, Gtk.IconSize.BUTTON)
        self.syncButton.set_image(self.syncImage)
        self.syncButton.connect('clicked', self.startSync)
        self.syncSpinner = Gtk.Spinner()
        self.syncButton.set_has_tooltip(True)
        self.syncButton.set_tooltip_text("Download libraries from ADS.")
        hb.pack_start(self.syncButton)

        # settingsButton = Gtk.Button()
        # settingsIcon = Gio.ThemedIcon(name='system-run')
        # settingsImage = Gtk.Image.new_from_gicon(settingsIcon,Gtk.IconSize.BUTTON)
        # settingsButton.set_image(settingsImage)
        # settingsButton.connect('clicked',self.settingsMenu)
        # hb.pack_start(settingsButton)

        downloadButton = Gtk.Button()
        downloadIcon = Gio.ThemedIcon(name='document-save')
        downloadImage = Gtk.Image.new_from_gicon(downloadIcon, Gtk.IconSize.BUTTON)
        downloadButton.set_image(downloadImage)
        downloadButton.connect('clicked', self.downloadPdfs)
        downloadButton.set_has_tooltip(True)
        downloadButton.set_tooltip_text("Download missing PDFs.")
        hb.pack_start(downloadButton)

    def settingsMenu(self, button):
        print('woo')

    def download_article(self, article):
        if 'journal' in article and article['journal'] == 'ArXiv e-prints':
            pdf_url = 'https://arxiv.org/pdf/' + article['eprint']
        elif PREFER_ARXIV and 'eprint' in article:
            pdf_url = 'https://arxiv.org/pdf/' + article['eprint']
        else:
            pdf_url = ADS_PDF.format(article['bibcode'])
        try:
            print("requesting {}".format(pdf_url))
            r = requests.get(pdf_url, timeout=20, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.97 Safari/537.36 Vivaldi/1.94.1008.40'})
            # The user agent gets around people who try to filter out bots, but this 
            # program is generating no more traffic than I would with a web browser.
            # (and probably less, given that I download things exactly once with this program
            # and usually multiple times on phones/browsers.)
            # It also doesn't affect ad revenue because if it works it goes directly to the PDF anyway
            # and a web browser would do the same thing.
            # All of the above is rationalization. This is probably an evil line of code. Sorrynotsorry

            print(r.status_code)
            print(r.headers['Content-type'])
            if 'application/pdf' in r.headers['Content-type'] and r.status_code == 200:
                print('yay! A PDF file!')
                return ('pdf', r.content)
            # elif r.status_code == 403:
            #    return('url',pdf_url)
        except:
            traceback.print_exc()
        try:
            return ('url', DOI_PROVIDER + article['doi'])
        except:
            traceback.print_exc()
            return ('?', None)

    def downloadPdfs(self, button):
        if self.syncing:
            d = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
                                  Gtk.ButtonsType.OK, "Cannot download pdfs while syncing")
            d.run()
            d.destroy()
            return
        d = Gtk.MessageDialog(
            self,
            0,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            "Instructions to Download PDFs"
        )

        d.format_secondary_text("This program will launch your default browser to fetch the articles that are missing. Download each PDF and save it in the 'add_pdf' folder in the directory of this program. This program will then move it to the 'library' folder organized by first author.")
        d.run()
        d.destroy()
        for article in self.bib.whatPapersNeedPdfs():
            print('working on article {}'.format(article['title']))
            a, b = self.download_article(article)
            if a == 'url':

                url = b
                webbrowser.open_new_tab(url)
                d = Gtk.MessageDialog(
                    self,
                    0,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.NONE,
                    "Opened browser"
                )

                d.format_secondary_text("Save the file associated with {} to the 'add_pdf' folder.".format(article['title']))
                d.add_buttons("Add this pdf", 1,
                              "Skip permanently", 2,
                              "Skip once", 3,
                              "Cancel", 4)
                r = d.run()
                d.destroy()
                if r == 1:
                    self.grabPdf(article)
                elif r == 4:
                    break
                elif r == 2:
                    self.bib.setSkipPdf(article['bibcode'])

            elif a == '?':
                d = Gtk.MessageDialog(
                    self,
                    0,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.NONE,
                    f"The article {article['title']} by {article['author']} {article['year']} has no DOI number."
                )
                d.format_secondary_text("Either find it manually and put the pdf in add_pdf, or click one of the skip options.")
                d.add_buttons("Add this pdf", 1,
                              "Skip permanently", 2,
                              "Skip once", 3,
                              "Cancel", 4)
                r = d.run()
                d.destroy()
                if r == 1:
                    self.grabPdf(article)
                elif r == 2:
                    self.bib.setSkipPdf(article['bibcode'])
                elif r == 4:
                    break
            elif a == 'pdf':
                fname = self.getOutFilename(article)
                with open(fname, 'wb') as f:
                    f.write(b)
                self.bib.setPdfs(article['bibcode'], fname)

        self.bib.saveFiles()
        print("wut")

    def getOutFilename(self, article, i=0, extension='.pdf'):
        assert (extension[0] == '.')
        path = 'library/' + self.bib.getFirstAuthor(article['author']) + '/'
        os.makedirs(path, exist_ok=True)
        offset = 0
        if 'pdf' in article:
            offset = article['pdf'].split(',')[-1].split('_')[0]
        return path + "{}_{}{}".format(i+offset, article['bibcode'], extension)

    def grabPdf(self, article):
        files = ""
        (_, _, filenames) = next(os.walk('add_pdf/'))
        
        for i, filename in enumerate(filenames):
            _, extension = os.path.splitext(filename)
            newfilename = self.getOutFilename(article, i, extension)
            os.rename('add_pdf/'+filename, newfilename)
            files = files + ',' + newfilename
        self.bib.setPdfs(article['bibcode'], files)

    def setupDone(self):
        self.show_all()
    
    def populate_sidebar(self):
        """ Called on start of app, and also on finish of sync."""
        sb = self.sidebar
        rows = []

        # Get existing rows if any
        for i in range(self.sidebar_num_rows):
            # Can't find a method for just getting all rows...
            r = sb.get_row_at_index(i)
            if r.data == "No Filters":
                rows.append("None")
            else:
                if self.bib.libInfo[r.library_id]['name'] != r.data:
                    r.update_label(self.bib.libInfo[r.library_id]['name'])
                rows.append(r.library_id)
                # print('updated row {}'.format(r.data))

        # Add default row
        if "None" not in rows:
            sb.add(ListBoxRowWithData("No Filters", 'None'))
            self.sidebar_num_rows += 1

        sortedlibs = sorted(self.bib.libInfo, key=lambda item: self.bib.libInfo[item]['name'].lower())
        # Add all libraries if they aren't already there
        for library in sortedlibs:
            if library not in rows:
                libname = self.bib.libInfo[library]['name']
                r = ListBoxRowWithData(libname, library)
                # print('added {}'.format(libname))
                sb.add(r)
                self.sidebar_num_rows += 1
                # print('added row {}'.format(libname))

        sb.connect('row-activated', self.sb_click)
        sb.show_all() 
    
    def sb_click(self, widget, row):
        self.library_filter_name = row.library_id
        self.library_filter.refilter()

    def library_filter_func(self, model, rownum, data):
        if self.library_filter_name is None or self.library_filter_name == "None":
            return True
        else:
            bibcode = model[rownum][7]
            r = bibcode in self.bib.libPapers[self.library_filter_name]
            # if r:
            #     print('filtered in!')
            # else:
            #     print('filtered out!')
            return r

    def startSync(self,button):
        # button.set_image(None)
        self.syncing = True
        button.set_image(self.syncSpinner)
        self.syncSpinner.start()
        # use a thread to call ads 
        threading.Thread(target=self.adsRefreshThread).start()
        # TODO: Freeze bib database editing 
        # Depends on: TODO: Add database editing :P

    def finishSync(self, newIds):
        self.syncSpinner.stop()
        self.syncButton.set_image(self.syncImage)
        # print(dir(self.bib))
        if self.bib.exhausted:
            self.syncButton.set_sensitive(False)
        # TODO: Make this display the number of queries remaining in a status bar or something.
        # Also unfreeze the bib database editing
        for paperID in newIds:
            paper = self.bib.bibDatabase[paperID]
            try:
                self.listStore.append(makeListStoreElement(paper))
            except KeyError:
                print("KeyError in finishSync(), paper ID: {}. Paper was not added to library.".format(paperID))
        # Add new libraries to sidebar
        self.populate_sidebar()
        self.syncing = False

    def adsRefreshThread(self):
        try:
            newIds, idConflicts = self.bib.adsRefresh()
            if len(idConflicts) != 0:
                GLib.idle_add(self.idConflictsPopup, idConflicts)
            GLib.idle_add(self.finishSync, newIds)
        except InternalServerError:
            GLib.idle_add(
                self.errorMessage, 
                "Internal Server Error",
                "It looks like the ADS is having some trouble right now. Maybe try again later?"
            )
            GLib.idle_add(self.finishSync, [])
        except requests.exceptions.ConnectionError:
            GLib.idle_add(
                self.errorMessage, 
                "Connection Error",
                "Either your internet isn't working or the ADS is down. Try checking those things?"
            )
            GLib.idle_add(self.finishSync, [])
        except ads.exceptions.APIResponseError as e:
            GLib.idle_add(
                self.errorMessage, 
                "ADS Response Error",
                "It looks like the ADS is having some trouble right now. Maybe try again later?"
            )
            GLib.idle_add(self.finishSync, [])
            print(e)
        except APILimitError:
            GLib.idle_add(
                self.errorMessage, 
                "API limit reached",
                "You have reached the maximum number of API requests allowed per day. Try again tomorrow."
            )
            GLib.idle_add(self.finishSync, [])
        except UnauthorizedError:
            GLib.idle_add(
                self.errorMessage, 
                "ADS Key Missing or Invalid",
                "Make sure to add an ADS API key using the ADS python library!"
            )
            GLib.idle_add(self.finishSync, [])            
        except:
            print("Encountered misc error. Handling \"Gracefully\":")
            traceback.print_exc()

    def errorMessage(self, title, text):
        d = Gtk.MessageDialog(
            self, 
            0, 
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            title
        )

        d.format_secondary_text(text)
        d.run()
        d.destroy()

    def setSidebarStuff(self, button):
        if self.sidebarVisible:
            self.sidebar.show()
            self.sidebarscrolledwindow.show()
            button.set_image(self.hideSidebarImage)
        else:
            button.set_image(self.showSidebarImage)
            self.sidebar.hide()
            self.sidebarscrolledwindow.hide()

    def sidebarToggle(self, button):
        if self.sidebarVisible:
            self.sidebarVisible = False
        else:
            self.sidebarVisible = True

        self.setSidebarStuff(button)

    def on_quit(self, *args):
        print('exiting...')
        size = self.get_size()
        columnwidths = [col.get_fixed_width() for col in self.columns]
        with open('windowprefs.json', 'w') as prefsfile:
            prefsfile.write(json.dumps({'size': size,
                                        'sb': self.sidebarVisible,
                                        'colwidths': columnwidths,
                                        'arxiv': PREFER_ARXIV}))
        # Gtk.main_quit()

    def idConflictsPopup(self, conflicts):
        # make a popup that describes the old and new ID codes.
        d = Gtk.MessageDialog(
            self, 
            0, 
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK, 
            "Warning: ID codes have changed"
        )

        d.format_secondary_text("Check the file ChangedCodes.txt in this program's directory for more information and a detailed list of changes. If you have not written any .tex files using the master bib file provided by this program, you can ignore this message.")
        d.run()
        d.destroy()
        with open('ChangedCodes.txt', 'w') as ccfile:
            ccfile.write(ID_CHANGED_MESSAGE)
            for key in conflicts:
                ccfile.write(key + '  ->  ' + conflicts[key]+'\n')


class ListBoxRowWithData(Gtk.ListBoxRow):
    def __init__(self, data, lid):
        super(Gtk.ListBoxRow, self).__init__()
        self.library_id = lid
        self.data = data
        self.label = Gtk.Label(data)
        self.add(self.label)

    def update_label(self, newlabel):
        self.label.set_text(newlabel)
        self.data = newlabel
        

def makeListStoreElement(paper):
    author = authorHandler(paper['author'])  # every paper should have an author...
    # Done: Make author list pretty
    title = paper['title'].replace('\n', ' ')  # and title
    year = int(paper['year'])  # and year...
    bibcode = paper['bibcode']  # every paper DOES have a bibcode
    ID = paper['ID']  # and ID
    try:
        if paper['journal'][0] == '\\':
            journal = paper['journal'][1:].upper()
        else:
            journal = paper['journal']
    except KeyError:
        if 'series' in paper:
            if paper['series'][0] == '\\':
                journal = paper['series'][1:].upper()
            else:
                journal = paper['series']
        else:
            journal = paper['bibcode'][4:9].strip('.')
    try: 
        month = paper['month']
    except KeyError:
        month = ''
    try:
        volume = int(paper['volume'])
    except KeyError:
        volume = None
    try:
        pages = paper['pages']
    except KeyError:
        pages = ''

    return [author,
            journal,
            month,
            year,
            title,
            volume,
            pages,
            bibcode,
            ID]


def authorHandler(authors):
    return LatexNodes2Text().latex_to_text(authors).replace('\n', ' ')


class AstroRefApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="com.rooneyworks.AstroRef",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs
        )
        self.window = None

        self.add_main_option(
            "test",
            ord("t"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Command line test",
            None,
        )

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        builder = Gtk.Builder.new_from_string(MENU_XML, -1)
        self.set_app_menu(builder.get_object("app-menu"))

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        if not self.window:
            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = MainWindow(application=self, title="Main Window")

        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if "test" in options:
            # This is printed on the main instance
            print("Test argument recieved: %s" % options["test"])

        self.activate()
        return 0

    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()

    def on_quit(self, action, param):
        self.window.close()
        self.quit()


if __name__ == '__main__':
    # workaround:
    # if Gtk.get_minor_version() == 10 and Gtk.get_micro_version <= 1:
    # The if statement probably takes more time than starting a thread that 
    # does nothing.
    # threading.Thread(target=lambda:None).start()

    # ui = MainWindow()
    # Gtk.main()
    app = AstroRefApp()
    app.run(sys.argv)
