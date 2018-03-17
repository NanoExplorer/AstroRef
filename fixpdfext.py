import os
import management

def main():
    bib = management.Bibliography()
    for paper in bib.bibDatabase:
        if bib.hasPdf(paper):
            pdfs=bib.bibDatabase[paper]['pdf']
            newpdfs=""
            for pdf in pdfs.split(','):
                if pdf[-3:] == 'pdf' and pdf[-4] != '.':
                    newpdf = pdf[:-3] + '.pdf'
                    newpdfs += newpdf + ','
                    os.rename(pdf,newpdf)
                else: 
                    newpdfs+= pdf + ','
            newpdfs=newpdfs.strip(',')
            print(newpdfs)
            bib.bibDatabase[paper]['pdf']=newpdfs
    bib.saveFiles()
if __name__=="__main__":
    print("""       This script exists to fix legacy libraries where sometimes a 
pdf file was named "filenamepdf" instead of "filename.pdf". If you 
have experienced this problem, you can use this script to fix it. 
This script will rename the affected files to "filename.pdf" and 
correct references to them in the database file. 

Type "Yes" to continue (case sensitive):""")
    prompt = input()
    if prompt=="Yes":
        main()