# AstroRef

AstroRef is a reference management software designed for astronomers using Nasa Astrophysics Data Service (ADS). With it, you can easily manage a library of papers that are indexed on the ADS. 

The workflow of this program is simple: Create a library using the [new ADS](http://ui.adsabs.harvard.edu/), and this program will automatically download bibliographic information on all the papers in that library and streamline the process of downloading PDFs of those papers. It then arranges those PDFs on your filesystem and gives you quick access to them through a list. 

## Installation

AstroRef is written in Python 3. Its dependencies are as follows:
* ads
* bibtexparser
* gi / PyGObject (This may be included with your distro, I know Ubuntu has it)
* requests (but ads depends on it too, so you'll get it automatically when you install ads.)
* pylatexenc

The hard part is getting gi / PyGObject installed. I can't help you with that because it seems like everyone has a different experience. If you don't want to run this program from a virtualenv like I do, it'll probably be a lot easier.

The other libraries can simply be installed with pip or your distro's package manager.

Make sure to set up the python ads library by making the file `~/.ads/dev_key` and pasting your ADS api key in there.

I think that's it for installation. Let me know if that doesn't cover everything.

## Usage

Once you have created a library (or a few libraries) on the new ADS, open AstroRef by executing `ui.py`. On first run it should launch a tutorial that will give you the basics (feedback welcome). Then you can click on the refresh button in the upper left of the program to download all the metadata for the papers in the libraries you have on ADS. Then if you want local copies of all the PDFs, you can click the download button next to the refresh button and it will walk you through the process of linking PDFs to your local library.

## Pleas for help

If anyone knows a good way to render LaTeX equations or HTML formatting in a GTK application, let me know! I would really like to improve this app by allowing equations or formatting in the comments and/or abstracts.
