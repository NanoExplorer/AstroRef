# AstroRef

AstroRef is a reference management software designed for astronomers using Nasa Astrophysics Data Service (ADS). With it, you can easily manage a library of papers that are indexed on the ADS. 

The workflow of this program is simple: Create a library using the [new ADS](http://ui.adsabs.harvard.edu/), and this program will automatically download bibliographic information on all the papers in that library and streamline the process of downloading PDFs of those papers. It then arranges those PDFs on your filesystem and gives you quick access to them through a list. 

## Installation

AstroRef is written in Python 3. Its dependencies are as follows:
* ads
* bibtexparser
* gi / PyGObject
* requests (but ads depends on it too, so you'll probably already have it.)

The hard part is getting gi / PyGObject installed. I can't help you with that because it seems like everyone has a different experience. If you don't want to run this program from a virtualenv like I do, it'll probably be a lot easier.

Make sure to set up the python ads library by making the file `~/.ads/dev_key' and pasting your ADS api key in there.

I think that's it for installation. Let me know if that doesn't cover everything.

