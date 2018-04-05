"""
interfaces to the adsws biblib service
"""

import json
import six
import requests
from ads.base import APIResponse, BaseQuery


class BigResponse():
    def __init__(self,libresponse):
        self.response = libresponse
        libJson = self.response.text
        data = json.loads(libJson)
        #print(data)
        self.abstracts = {}
        for article in data['response']['docs']:
            try:
                self.abstracts[article['bibcode']] = article['abstract']
            except:
                self.abstracts[article['bibcode']] = 'No abstract'
    def get_remaining_queries(self):
        return self.response.headers['X-RateLimit-Remaining']

class BigQuery(BaseQuery):
    HTTP_ENDPOINT = "https://api.adsabs.harvard.edu/v1/search/bigquery"
    def __init__(self,ids):
        self.response = None
        idsString = "bibcode"
        self.nids = len(ids)
        for articleid in ids:
            idsString = idsString +'\n'+ articleid
        self.ids = idsString
    def execute(self):

        self.response = BigResponse(
            requests.post(self.HTTP_ENDPOINT, 
                          params={'q':'*:*','wt':'json','fl':'abstract,bibcode','rows':self.nids},
                          headers={'Authorization':'Bearer '+self.token},
                          data=self.ids
                          )
        )
        return self.response
