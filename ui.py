#Needs to be able to display and edit the records in the Bibliography as a user interface.
#Good references:
#https://lazka.github.io/pgi-docs/#Gtk-3.0/classes/ListBoxRow.html#Gtk.ListBoxRow
#http://python-gtk-3-tutorial.readthedocs.io/en/latest/layout.html?highlight=scroll
#

#it feels 'wrong' but I think the best way to manage everything is to simply call the bibliography
#update method using a thread. We'll want to lock the user out using a different method until
#it is done, because we can't let them edit anything while ADS is fetching.

import gi
import json
import traceback
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, Gio, GObject, GLib
import threading
import management
import setup
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



class MainWindow(Gtk.Window):
    sidebarVisible = True
    (COLUMN_AUTHOR,
     COLUMN_JOURNAL,
     COLUMN_MONTH,
     COLUMN_YEAR,
     COLUMN_TITLE,
     COLUMN_VOLUME,
     COLUMN_PAGES,
     COLUMN_BIBCODE,
     COLUMN_ID) = range(9)

    def __init__(self):
        try:
            with open('windowprefs.json','r') as prefsfile:
                prefs = json.loads(prefsfile.read())
            self.sidebarVisible = prefs['sb']
            size = prefs['size']
        except:
            print(traceback.format_exc())
            size = (800,600)
            pos = (40,40)

        self.bib = management.Bibliography()

        Gtk.Window.__init__(self,title="AstroRef")
        self.connect('delete-event', self.on_quit)
        self.set_default_size(*size)

        self.add_headerbar()

        #Make top level box that will contain all other widgets
        self.box = Gtk.Box(spacing=10,orientation=Gtk.Orientation.HORIZONTAL,homogeneous=False)
        self.add(self.box)

        self.make_sidebar()

        self.rbox = Gtk.Box(spacing=10,orientation=Gtk.Orientation.VERTICAL,homogeneous=False)
        self.box.pack_start(self.rbox,True,True,0)
        self.create_list_model()
        self.make_listbox()
        self.make_infobox()

        if self.bib.firstRun:
            # TODO: check if bib.firstRun and popup with a welcome screen
            setup.AssistantApp(self.setupDone)
        else:
            self.setupDone()
        self.populate_sidebar()
        self.setSidebarStuff(sidebarbtn)

    def create_list_model(self):
        self.listStore = Gtk.ListStore(str,str,str,GObject.TYPE_INT,str,GObject.TYPE_INT,str,str,str)
        #TODO : copy data from bib database to list store
        for paperID in self.bib.bibDatabase:
            paper = self.bib.bibDatabase[paperID]
            if not 'month' in paper:
                paper['month'] = ''
            try:
                self.listStore.append([paper['author'], # TODO: make this look better.
                                   paper['journal'][1:].upper(), #also make this look better.
                                   paper['month'],
                                   int(paper['year']),
                                   paper['title'],
                                   int(paper['volume']),
                                   paper['pages'],
                                   paper['bibcode'],
                                   paper['ID']])
            except KeyError:
                print(paperID)

    """COLUMN_AUTHOR,
     COLUMN_JOURNAL,
     COLUMN_MONTH,
     COLUMN_YEAR,
     COLUMN_TITLE,
     COLUMN_VOLUME,
     COLUMN_PAGES,
     COLUMN_BIBCODE,
     COLUMN_ID)"""


    def make_listbox(self):
        lbsw = Gtk.ScrolledWindow()
        lbsw.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        self.rbox.pack_start(lbsw,True,True,0)

    def make_infobox(self):
        pass

    def make_sidebar(self):
        sbsw = Gtk.ScrolledWindow()
        sbsw.set_size_request(300,400)
        sbsw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.box.pack_start(sbsw,False,False,0)

        self.sidebar = Gtk.ListBox()
        #self.box.pack_start(self.sidebar,True,True,0)
        sbsw.add(self.sidebar)

    def add_headerbar(self):
        """ Add the header bar to the window. The header bar includes options such as close,
        refresh, and hide/show sidebar. Because of differences between different versions of gtk, 
        it has to check which version is being used and adjust automatically. In versions earlier than 11
        the headerbar cannot show minimize and maximize buttons by itself. I cannot implement a maximize
        button, but I always maximize a window by slamming it into the top of the screen anyway, so
        I only implement a minimze button."""

        """Note: The reason I cannot implement a maximize button is because it is nontrivial to 
        know whether the window is currently maximized. Usually maximize buttons will also change to
        restore buttons when the window is maximized, but I cannot do that."""
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)

        if Gtk.get_minor_version() < 11:
            #I guess in old versions of Gtk the headerbar doesn't automatically show the minimize and
            #maximize buttons. This is a really bad kludge, but since I'm leaving my laptop on Linux 
            #Mint 17 and not upgrading to 18, it's really necessary. 

            minimize = Gtk.Button()
            minimizeIcon = Gio.ThemedIcon(name='window-minimize-symbolic')
            minimizeImage = Gtk.Image.new_from_gicon(minimizeIcon,Gtk.IconSize.BUTTON)
            minimize.add(minimizeImage)
            minimize.connect('clicked',lambda x: self.iconify())
            hb.pack_end(minimize)

            #Also this version of GTK is too old to let me know if the window is maximized.
            #It looks like there is a way, but I can't get it to work. So I'll just leave
            #out the maximize button on old versions of GTK.
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
            hb.set_decoration_layout(":minimize,maximize,close")
        hb.props.title = "AstroRef"
        self.set_titlebar(hb)
        self.set_icon_from_file('test4.svg')


        sidebarbtn = Gtk.Button()
        sidebarIcon = Gio.ThemedIcon(name='sidebar-hide-symbolic')
        self.hideSidebarImage = Gtk.Image.new_from_gicon(sidebarIcon,Gtk.IconSize.BUTTON)
        showSidebarIcon = Gio.ThemedIcon(name='sidebar-show-symbolic')
        self.showSidebarImage = Gtk.Image.new_from_gicon(showSidebarIcon,Gtk.IconSize.BUTTON)


        #self.setSidebarImage(sidebarbtn)
        sidebarbtn.connect('clicked', self.sidebarToggle)
        hb.pack_start(sidebarbtn)


        self.syncButton = Gtk.Button()
        syncIcon = Gio.ThemedIcon(name='gtk-refresh')
        self.syncImage = Gtk.Image.new_from_gicon(syncIcon,Gtk.IconSize.BUTTON)
        #sync.add(self.syncImage)
        self.syncButton.set_image(self.syncImage)
        self.syncButton.connect('clicked',self.startSync)
        self.syncSpinner = Gtk.Spinner()
        #sync.set_image(self.syncSpinner)
        hb.pack_start(self.syncButton)

        
        #self.show_all()

    def setupDone(self):
        #print('setupdone')
        self.show_all()
    def populate_sidebar(self):
        sb = self.sidebar
        for library in self.bib.libInfo:
            libname = self.bib.libInfo[library]['name']
            r = ListBoxRowWithData(libname)
            #print('added {}'.format(libname))
            sb.add(r)
        sb.connect('row-activated', lambda widget,row:print(row.data))
        sb.show_all() #Why do I have to do this??
        
    def startSync(self,button):
        #button.set_image(None)
        button.set_image(self.syncSpinner)
        self.syncSpinner.start()
        #use a thread to call ads 
        threading.Thread(target=self.adsRefreshThread).start()
        #TODO: Freeze bib database editing 

    def finishSync(self,newIds):
        self.syncSpinner.stop()
        self.syncButton.set_image(self.syncImage)
        #print(dir(self.bib))
        if self.bib.exhausted:
            self.syncButton.set_sensitive(False)
        # TODO: Make this display the number of queries remaining in a status bar or something.
        #Also unfreeze the bib database editing
        #Also add new papers (newIds) to listStore



    def setSidebarStuff(self,button):
        if self.sidebarVisible:
            self.sidebar.show()
            button.set_image(self.hideSidebarImage)
        else:
            button.set_image(self.showSidebarImage)
            self.sidebar.hide()

    def sidebarToggle(self,button):
        if self.sidebarVisible:
            self.sidebarVisible = False
        else:
            self.sidebarVisible=True

        self.setSidebarStuff(button)

    def on_quit(self,*args):
        #print('exiting...')
        size = self.get_size()
        with open('windowprefs.json','w') as prefsfile:
            prefsfile.write(json.dumps({'size':size,'sb':self.sidebarVisible}))
        Gtk.main_quit()
    def idConflictsPopup(self,conflicts):
        d = Gtk.MessageDialog(self,0,Gtk.MessageType.INFO,
                          Gtk.ButtonsType.OK,"Warning: ID codes have changed")

        d.format_secondary_text("Check the file ChangedCodes.txt in this program's directory for more information and a detailed list of changes. If you have not written any .tex files using the master bib file provided by this program, you can ignore this message.")
        d.run()
        d.destroy()
        with open('ChangedCodes.txt','w') as ccfile:
            ccfile.write(ID_CHANGED_MESSAGE)
            for key in conflicts:
                ccfile.write(key + '  ->  ' + conflicts[key]+'\n')

        #make a popup that describes the old and new ID codes.
    def adsRefreshThread(self):
        newIds,idConflicts = self.bib.adsRefresh()
        if len(idConflicts) != 0:
            GLib.idle_add(self.idConflictsPopup,idConflicts)
        GLib.idle_add(self.finishSync,newIds)

class ListBoxRowWithData(Gtk.ListBoxRow):
    def __init__(self, data):
        super(Gtk.ListBoxRow, self).__init__()
        self.data = data
        self.add(Gtk.Label(data))


if __name__ == '__main__':
    #workaround:
    #if Gtk.get_minor_version() == 10 and Gtk.get_micro_version <= 1:
    #The if statement probably takes more time than starting a thread that does nothing.
    threading.Thread(target=lambda:None).start()

    GObject.threads_init()
    #This ^ will emit a deprecation warning running on Mint 18 but is necessary for mint 17

    ui = MainWindow()
    Gtk.main()

