# AstroRef

AstroRef is a reference management software designed for astronomers using Nasa Astrophysics Data Service (ADS). With it, you can easily manage a library of papers that are indexed on the ADS. 

The workflow of this program is simple: Create a library using the [new ADS](http://ui.adsabs.harvard.edu/), and this program will automatically download bibliographic information on all the papers in that library and streamline the process of downloading PDFs of those papers. It then arranges those PDFs on your filesystem and gives you quick access to them through a list. 

This program will also manage a BibTex compatible .bib file for ease of use with LaTeX citations!

## Installation

AstroRef is written in Python 3. Its dependencies are as follows:
* ads 
* bibtexparser (v1.0.1)
* gi / PyGObject (This may be included with your distro, I know Ubuntu has it)
* requests (but ads depends on it too, so you'll get it automatically when you install ads.)
* pylatexenc

Make sure to set up the python ads library by making the file `~/.ads/dev_key` and pasting your ADS api key in there.

I recommend installing in a new Conda environment with the following:
```
conda create -n referencemanager
conda activate referencemanager
conda install -c conda-forge pygobject requests bibtexparser pylatexenc ads gtk3 librsvg
```
You will, however, need to remember to activate this env when launching the program. 

## Usage

### Library management
Once you have created a library (or a few libraries) on the new ADS, open AstroRef by executing `ui.py`. On first run it should launch a tutorial that will give you the basics (feedback welcome). Then you can click on the refresh button in the upper left of the program to download all the metadata for the papers in the libraries you have on ADS. Then if you want local copies of all the PDFs, you can click the download button next to the refresh button and it will walk you through the process of linking PDFs to your local library.

Once you have downloaded some PDFs, you can simply double click on a paper in AstroRef to launch the pdf file in your default pdf viewer. 

By default AstroRef shows all the papers from all your ADS libraries. You can filter the interface by library by selecting a library in the sidebar. CTRL-F will allow you to search for keywords in the author list and title. Use the up and down arrow keys to jump to the next/previous match.

### BibTex integration
AstroRef natively manages a .bib file that is kept in the same directory as ui.py. If you want, you can use this .bib file as the bibliography file for a LaTeX document. I hope to add functionality in the future to have this program actively manage your .bib files, but for now you can just make a symbolic link* from your LaTeX working directory to master.bib, or manually copy master.bib from the program directory to your LaTeX directory. 

Once your LaTeX document is using the bib file managed by AstroRef, you can simply highlight a paper in AstroRef and hit CTRL+C to copy the citation code of the paper to your clipboard. You can also select multiple papers (by CTRL-click or SHIFT-click) and copy all of their citation codes in the proper format!

* if you do choose to make a symbolic link to the BibTex file, you will need to be careful when you add multiple papers written by the same author in the same year, because that can change the citation codes. I may be able to fix this issue with active bib file management. AstroRef will warn you when this happens.


### PDF downloading
AstroRef was built by a student at Cornell University, and as such the pdf downloader assumes you have an account with the Cornell library. If you would like to use this software at a different university or library provider, open an issue here, or edit the `DOI_PROVIDER` line at the top of `ui.py` to point to your library's doi proxy. However, every university library is a little bit different, and I can't know exactly how your library works without having an account with them. I'm happy to work with you to expand this program's capabilities.

### Other features
If you want to copy the paper's bibcode to the clipboard, you can use CTRL+X. This is useful (for example) if you want to use ADS to search through a paper's references.


## Pleas for help

If anyone knows a good way to render LaTeX equations or HTML formatting in a GTK application, let me know! I would really like to improve this app by allowing equations or formatting in the comments and/or abstracts. 
