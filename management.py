# This file handles the logic of managing a bunch of papers. It has the refresh functions and 
# storage functions that will be used by the program.
#
#
#
import os
import json
import bibtexparser
from libraries import LibrariesQuery, LibraryQuery
from ads import ExportQuery
from bigquery import BigQuery
import calendar
#
#import threading

BT_PARSER = lambda: bibtexparser.bparser.BibTexParser(common_strings=True)
#this is a lambda because I need a new one every time, otherwise things will go horribly wrong.
#Don't you agree that the bibtexparser library v1.0.1 is waay better than the old version /sarcasm


LETTERS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
#MONTHS = {v.lower(): k+1 for k,v in enumerate(calendar.month_abbr)} Old versions of bibtexparser used this
MONTHS={v: k+1 for k,v in enumerate(calendar.month_name)}

class Bibliography():
    def __init__(self):
        #will want to check if a local database exists, and if not make an empty one.
        #User can choose to grab from ADS later if they want using adsRefresh()
        self.qRemaining = 100
        self.exhausted = False
        if not os.path.isfile('libraryInfo.json') or not os.path.isfile('libraryPapers.json') or not os.path.isfile('master.bib'):
            #Possibly prompt user to ask for permission here.
            #If any file is missing we have to regrab everything from ads.
            #except *technically* librarypapers, since we can build that from master.bib,
            #but this is easier, and I don't think the missing feature will be bothersome.
            print('performing first-time setup')
            self.libInfo = {} # eventually structure will be {libraryID:{date:datemodified,num:#,name:''}}
            self.libPapers = {}# eventually structure will be {lid: [bibcodes]}
            self.bibDatabase = {}#Structure will be {bibcode:bibtexinformation}
            self.idCodes = {}#Structure will be {idcode:bibcode}
            #self.adsRefresh()
            self.firstRun = True

        else:
            print('loading cached data...')
            with open('libraryInfo.json', 'r') as infofile:
                self.libInfo = json.loads(infofile.read())
            with open('libraryPapers.json','r') as papersfile:
                self.libPapers = json.loads(papersfile.read())
            with open('master.bib','r') as bibfile:
                bibfile_str = bibfile.read()
            self.bibDatabase,self.idCodes = bibtexDict(bibfile_str)
            self.firstRun = False

    def saveFiles(self):
        with open('libraryInfo.json','w') as infofile:
            infofile.write(json.dumps(self.libInfo))
        with open('libraryPapers.json','w') as papersfile:
            papersfile.write(json.dumps(self.libPapers))
        with open('master.bib','w') as bibfile:
            bibfile.write(unBibtexDict(self.bibDatabase))
        #with open('other.json','w') as take2file:
        #    take2file.write(json.dumps(self.bibDatabase))

    def adsRefresh(self):
        #perform a full ads refresh - 
        #  check the list of libraries, 
        #  download libraries that have changed, 
        #  then download info on all the papers that have been added.
        #Don't assume that set up has been performed yet. Check to see if objects exist.
        if self.exhausted:
            return
        toDownload = self.librariesRefresh()
        newPapers = []
        for lid in toDownload:
            #I know it's confusing to have a variable called lid when that's a different word,
            #but it's easier to type than libraryId or something, and it looks like 'id' is 
            #a python reserved word.
            newPapers+=self.libraryRefresh(lid)
        if len(newPapers) > 0:
            idConflicts = self.downloadPaperInfo(list(set(newPapers)))
        else:
            idConflicts = []
        #Will need to do something with the idConflicts, they're important!
        #Solution: return the idConflicts and let someone else deal with it.
        self.updateLibrariesInBibtex()
        self.saveFiles()
        return newPapers,idConflicts

        #update libraryInfo

    def librariesRefresh(self):
        #Download the list of libraries from ads, and compile a list of things that have changed.
        if self.exhausted:
            return
        q = LibrariesQuery()
        libs = q.execute().libraries
        self.updateRateLimits(q)
        toDownload = []
        #if hasattr(self, 'libInfo') and hasattr(self,'libPapers') and hasattr(self,'bib_database'):

        #Compare ADS library modified dates to local library modified dates 
        #make a list of what libraries to download

        for l in libs:
            lid = l['id']
            ldate = l['date_last_modified']
            lnum = l['num_documents']
            lname = l['name']
            if lid in self.libInfo:
                if self.libInfo[lid]['date'] != ldate or self.libInfo[lid]['num'] != lnum:
                    toDownload.append(lid)
            else:
                toDownload.append(lid)
            #This if statement could be improved for conciseness, but I think that would
            #sacrifice readability.
            self.libInfo[lid] = {'date':ldate,
                                 'num':lnum,
                                 'name':lname}
        self.lastLibsResponse = q

        return toDownload

    def libraryRefresh(self,lid):
        #download the library specified and make a list of papers that have been added
        #lid is the ugly, unique name for the library.
        if self.exhausted:
            return
        q = LibraryQuery(lid,self.libInfo[lid]['num'])
        lib = q.execute()
        self.updateRateLimits(q)

        newPapers = lib.bibcodes[:] #make a copy of lib.bibcodes so we don't modify it below

        #!!!! STRICTLY SPEAKING THIS SECTION OF CODE IS REDUNDANT!!!!!
        if lid in self.libPapers:
            for bibcode in self.libPapers[lid]:
                try:
                    newPapers.remove(bibcode)
                except ValueError:
                    print("Paper {} must have been removed from library.".format(bibcode))
        #!!!! END REDUNDANT CODE BLOCK. You may comment it out if you are confident.

        for paper in self.bibDatabase:
            #When you iterate over the dictionary you only get the keys
            try:
                newPapers.remove(paper)
            except ValueError:
                pass


        self.libPapers[lid] = lib.bibcodes
        self.libInfo[lid] = {'date':lib.metadata['date_last_modified'],
                             'num':lib.metadata['num_documents'],
                             'name':lib.metadata['name']
                            }

        self.lastLibResponse = q
        return newPapers
    def updateRateLimits(self,q):
        try:
            thisQLeft = int(q.response.response.headers['X-RateLimit-Remaining'])
            self._updateRateLimits(thisQLeft)
        except KeyError:
            print("I think they removed rate limits from some of the api endpoints?")
    def _updateRateLimits(self,thisQLeft):
        if thisQLeft < self.qRemaining:
            self.qRemaining = thisQLeft
        if self.qRemaining <= 1:
            self.exhausted = True
        print("queries remaining: {}".format(self.qRemaining))
    def downloadPaperInfo(self,papers):
        #download info on all the papers in the list of papers.
        #adds it to the self.bibDatabase 
        #papers is a list of ADS bibcode strings.
        #This will get bibtex entries from ADS and also abstracts. I think that's all I need.
        #Might be easier to get all information from the ADS search endpoint and subsequently
        #compile that info into a bibtex file instead of downloading a bibtex file 
        #and the abstracts separately.
        #Update: I think it's easier to get the bibtex and the abstracts separately
        if self.exhausted:
            return
        namesChanged={} # maps old name to new name
        bq = BigQuery(papers)
        bq.execute()
        self.updateRateLimits(bq)
        abstracts = bq.response.abstracts
        eq = ExportQuery(papers)
        bibtex = eq.execute()
        rate = eq.response.get_ratelimits()['remaining']
        if rate:
            self._updateRateLimits(int(rate))
        #print("***DUMPING PAPERS***")
        #print(papers)
        #print("***DUMPING BIBTEX***")
        #print(bibtex)
        #print("***FINISHED***")
        newBibDatabase = bibtexparser.loads(bibtex,parser=BT_PARSER()).entries
        self.lastBibResponse = eq
        self.lastBigResponse = bq
        #Now somehow I need to add all the abstracts to the correct papers in the bib structure
        for paper in newBibDatabase:
            paper['bibcode'] = paper['ID'] #Make sure to keep the bibcode, since it used to 
            #only be stored under the ID of the paper, and we want to change the ID.
            paper['abstract'] = abstracts[paper['ID']]
            paper['title']=paper['title'].strip('{}') #don't you just love the new bibtexparser library.
            firstAuthor=self.getFirstAuthor(paper['author'])


            pid = firstAuthor + paper['year']
            if pid in self.idCodes: #This paper will conflict ID wise with another paper, so gotta add letter
                other = self.bibDatabase[self.idCodes[pid]]
                assert other['bibcode'] != paper['bibcode'], "SOMEHOW the same paper got in twice.(1)"
                otherMonth = MONTHS[other['month']] if 'month' in other else 13
                paperMonth = MONTHS[paper['month']] if 'month' in paper else 13
                if otherMonth>paperMonth:
                    paper['ID'] = pid+'a' #Add 'a' to this paper because it's older
                    other['ID'] = pid+'b' 
                    namesChanged[pid]=pid+'b' #Add the old paper to the database of changed names
                    self.idCodes[pid+'b'] = self.idCodes.pop(pid) #move originally-added paper from
                    #old id code to new id code in the id codes database
                    self.idCodes[pid+'a'] = paper['bibcode'] #Add the newly-added paper to the id codes
                    #database
                    self.bibDatabase[paper['bibcode']] = paper #Add the newly-added paper to the 
                    #bibdatabase
                else:
                    #I guess if the months are the same it will have to be arbitrary lettering.
                    #In this section we do the same thing but with 'a' and 'b' swapped
                    #test
                    paper['ID'] = pid+'b'
                    other['ID'] = pid+'a'
                    namesChanged[pid]=pid+'a'
                    self.idCodes[pid+'a'] = self.idCodes.pop(pid)
                    self.idCodes[pid+'b'] = paper['bibcode']
                    self.bibDatabase[paper['bibcode']] = paper
            elif pid+'a' in self.idCodes:
                #man, now I have to implement some sort of sorting function.
                #first figure out how many papers there are.
                sameAuthorYearPapers = []
                flag = False
                for i,char in enumerate(LETTERS):
                    #Go through all the letters looking for papers with that name
                    if pid+char not in self.idCodes and not flag:
                        numPapers = i
                        flag = True
                    elif not flag:
                        sameAuthorYearPapers.append(self.bibDatabase[self.idCodes[pid+char]])
                    elif flag:
                        assert pid+char not in self.idCodes, "SOMEHOW letters are not consecutive"
                assert len(sameAuthorYearPapers) == numPapers,"The collision handler broke"
                assert numPapers < 26, "This program cannot deal with more than 26 papers published by the same first author in the same year."
                #sameAuthorYearPapers is sorted chronologically from [january,...,december]
                #It should also have only consecutive letters like ['a','b','c','d'...]
                for i,other in enumerate(reversed(sameAuthorYearPapers)):
                    assert other['bibcode'] != paper['bibcode'], "SOMEHOW the same paper got in twice.(2)"
                    j = len(sameAuthorYearPapers) - i - 1
                    otherMonth = MONTHS[other['month']] if 'month' in other else 13
                    paperMonth = MONTHS[paper['month']] if 'month' in paper else 13
                    if paperMonth>otherMonth:
                        #the paper needs to be inserted after the current one
                        paper['ID'] = pid+LETTERS[j+1]
                        self.bibDatabase[paper['bibcode']] = paper
                        self.idCodes[paper['ID']] = paper['bibcode']
                        #print('inserted new paper as {}'.format(paper['ID']))
                        break
                    elif j==0:
                        #insert the paper at 'a' and bump the current 'a' to 'b'
                        oldid = other['ID']
                        other['ID'] = pid+LETTERS[j+1]
                        self.idCodes[other['ID']] = self.idCodes.pop(oldid)
                        #print('moved paper from {} to {}'.format(oldid,other['ID']))
                        paper['ID'] = pid+LETTERS[j]
                        self.bibDatabase[paper['bibcode']] = paper
                        self.idCodes[paper['ID']] = paper['bibcode']
                        namesChanged[oldid] = other['ID']
                        #print('inserted new paper as {}'.format(paper['ID']))
                    else:
                        #bump the current 'x' to 'y'
                        oldid = other['ID']
                        other['ID'] = pid+LETTERS[j+1]
                        self.idCodes[other['ID']] = self.idCodes.pop(oldid)
                        namesChanged[oldid] = other['ID']
                        #print('moved paper from {} to {}'.format(oldid,other['ID']))
            else:
                #WHEW. Now we just get to add something normally!!!!!!
                #I've already forgotten how to do that... :(
                paper['ID'] = pid
                self.bibDatabase[paper['bibcode']] = paper
                self.idCodes[pid] = paper['bibcode']
        return namesChanged
    
    def getFirstAuthor(self,authors):
        authorsList = [i.strip() for i in authors.replace('\n',' ').split(' and ')]
        #go through author string and replace newlines with spaces. Then split author
        #string on ' and '. Then strip extra whitespace off of each author.
        
        firstAuthor = authorsList[0].split(',')[0][1:-1].replace(' ','')
        #Get the first author entry from above, separate first name from last name by ',',
        #remove the {} around the {LastName}, and remove any spaces that might be present.

        firstAuthor = removeSpecialCharacters(firstAuthor)
        #Removes special characters, and usually ends up replacing them with 'normal' characters
        return firstAuthor

    def updateLibrariesInBibtex(self):
        #goes through all the papers in the bibtex library and adds a list of libraries to it
        for library in self.libPapers:
            for bibcode in self.libPapers[library]:
                if 'libraries' in self.bibDatabase[bibcode] and library not in self.bibDatabase[bibcode]['libraries'].split(','):
                    self.bibDatabase[bibcode]['libraries'] += ',' + library
                elif 'libraries' not in self.bibDatabase[bibcode]:
                    self.bibDatabase[bibcode]['libraries'] = library

    def whatPapersNeedPdfs(self):
        return [self.bibDatabase[pid] for pid in self.bibDatabase if 'pdf' not in self.bibDatabase[pid]]

    def hasPdf(self,pid):
        return 'pdf' in self.bibDatabase[pid] 
    def setPdfs(self,pid,pdfloc):
        """Accepts strings or lists of strings as pid and pdfloc"""
        """Really this adds pdfs instead of setting them."""

        if type(pid) is str:
            pid = [pid]

        if type(pdfloc) is str:
            pdfloc = [pdfloc]

        #Now we know that pid and pdfloc are both lists.
        assert len(pdfloc) == len(pid), "pid and pdfloc must have same number of elements"

        for pid,pdfloc in zip(pid,pdfloc):
            paper = self.bibDatabase[pid]
            if 'pdf' not in paper:
                paper['pdf'] = pdfloc.strip(',')
            else:
                paper['pdf'] = paper['pdf'] + ',' + pdfloc.strip(',')
    def setDefaultPdf(self,pid,index):
        self.bibDatabase[pid]['default_pdf'] = index

    def getDefaultPdf(self,pid):
        if 'pdf' not in self.bibDatabase[pid]:
            return 
        try:
            return self.bibDatabase[pid]['pdf'].split(',')[int(self.bibDatabase[pid]['default_pdf'])]
        except KeyError:
            return self.bibDatabase[pid]['pdf'].split(',')[0]
"""
This function is a wrapper for the bibtexparser library
"""
def bibtexDict(btexstr):
    raw = bibtexparser.loads(btexstr,parser=BT_PARSER()).entries
    data = {}
    idc={}
    for paper in raw:
        data[paper['bibcode']] = paper
        idc[paper['ID']] = paper['bibcode']
    return data,idc

def unBibtexDict(btexdict):
    paperslist = []
    for paper in btexdict:
        paperslist.append(btexdict[paper])
    db = bibtexparser.bibdatabase.BibDatabase()
    db.entries = paperslist
    string = bibtexparser.dumps(db)
    #print("Dumping bibtex string:")
    #print(string)
    return string

def removeSpecialCharacters(author):
    #This will need to remove things like {\'a} and 
    #{\'o} and {\'{\i}} and replace them with things like 'a' and 'o' and 'i'
    #as blasphemous as that is, it has to be done.
    #I don't have a comprehensive list of special characters,
    #but I think looping over the name is the only option, and
    #finding a whole set of brackets, then finding the only unaccented character
    #in the set. I think that should work.
    #Might want to review the LaTeX rules for what can be used in a bibtex ID.
    #It might be that things like apostraphes have to be taken out, in which case
    #I just want to use that long ord(char) statement by itself.

    unAccName = ""
    for char in author:
        if notSpecial(char):
            unAccName += char
    return unAccName

def notSpecial(char):
    isUpper = ord(char) >= ord('a') and ord(char) <= ord('z')
    isLower = ord(char) >= ord('A') and ord(char) <= ord('Z')
    return (isUpper or isLower)

