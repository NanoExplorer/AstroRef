"""
interfaces to the adsws biblib service
"""

import json
import six

from ads.base import APIResponse, BaseQuery

"""
Here's a sample LibsResponse.libraries:
[
{'id': 'm_3kdf_jTP6jkpmwKQzGbw', 
'owner': 'ctr44', 
'permission': 'owner', 
'name': 'z792 proposaljkh afdes;', 
'description': 'My ADS library', 
'num_users': 1, 
'date_created': '2017-04-09T01:53:29.911413', 
'public': False, 
'date_last_modified': '2017-07-18T22:42:44.563686', 
'num_documents': 36}, 
{'id': 'Hb49lTmJT_SobhdVU0icZQ', 'owner': 'ctr44', 'permission': 'owner', 'name': 'zElectrodynamics Project', 'description': 'My ADS library', 'num_users': 1, 'date_created': '2017-04-11T19:20:13.447187', 'public': False, 'date_last_modified': '2017-05-07T19:39:15.872241', 'num_documents': 16}, 
{'id': 'wDHXcca9S_iOSN39NDzPsw', 'owner': 'ctr44', 'permission': 'owner', 'name': 'zFRB Prez', 'description': 'My ADS library', 'num_users': 1, 'date_created': '2017-04-20T21:32:05.255725', 'public': False, 'date_last_modified': '2017-05-07T19:39:22.837221', 'num_documents': 3}, 
{'id': '0c_SUyZpROaacaVTrSRQNA', 'owner': 'ctr44', 'permission': 'owner', 'name': 'zTo Filter', 'description': 'My ADS library', 'num_users': 1, 'date_created': '2017-04-22T23:26:41.736932', 'public': False, 'date_last_modified': '2017-05-07T19:39:31.586285', 'num_documents': 7}, 
{'id': 't_A2jIduQpmRyGPguUKDhg', 'owner': 'ctr44', 'permission': 'owner', 'name': 'Cosmology Talk', 'description': 'My ADS library', 'num_users': 1, 'date_created': '2017-05-07T19:39:39.776673', 'public': False, 'date_last_modified': '2017-05-08T02:55:20.166322', 'num_documents': 9}]

Here's a sample LibsResponse.response.headers:
{'Set-Cookie': 'session=.eJyrVopPK0otzlCyKikqTdVRis9MUbKqVlJIUrJS8g2JNIqsSsnwy3Kt8ssKrfQ18suKCsmu9M2KrIjMDTX0DcnJ9A-JNPBzSbdVqgXqLUgtyk3MS80rgZlWWpxaBDZRydjAwkCpFgDr6iQ0.DHdD4g.jQyy3qDMO7tcqPqnLwytu7qKlX4; Expires=Sun, 17-Sep-2017 15:12:34 GMT; HttpOnly; Path=/', 
'Access-Control-Allow-Methods': 'DELETE, GET, OPTIONS, POST, PUT', 
'Access-Control-Allow-Credentials': 'true', 
'Content-Type': 'application/json', 
'X-RateLimit-Reset': '1503014400', 
'Vary': 'Origin', 
'Connection': 'keep-alive', 
'Content-Encoding': 'gzip', 
'Content-Length': '515', 
'Access-Control-Allow-Origin': 'http://localhost:8000, http://ui.adsabs.harvard.edu, https://demo.adsabs.harvard.edu, https://demo.adsabs.harvard.edu, https://ui.adsabs.harvard.edu', 
'Server': 'nginx/1.10.2', 
'X-RateLimit-Remaining': '999', 
'X-RateLimit-Limit': '1000', 
'Date': 'Thu, 17 Aug 2017 15:12:34 GMT', 
'Access-Control-Allow-Headers': 'Accept, Authorization, Content-Type, Orcid-Authorization, X-BB-Api-Client-Version, X-CSRFToken'}

"""

class LibsResponse():
    def __init__(self,libresponse):
        self.response = libresponse
        libJson = self.response.text
        data = json.loads(libJson)
        self.libraries = data['libraries']
        self.libids = dict()
        for library in self.libraries:
            self.libids[library['name']] = library['id']
    def getID(name):
        return self.libids[name]
    def get_remaining_queries(self):
        return self.response.headers['X-RateLimit-Remaining']

class LibrariesQuery(BaseQuery):
    HTTP_ENDPOINT = "https://api.adsabs.harvard.edu/v1/biblib/libraries"
    def __init__(self):
        self.response = None

    def execute(self):
        self.response = LibsResponse(
            self.session.get(self.HTTP_ENDPOINT)
        )
        return self.response

class LibResponse():
    def __init__(self,libresponse):
        self.response = libresponse
        libJson = self.response.text
        data = json.loads(libJson)
        self.bibcodes = data['documents']
        self.metadata = data['metadata']
        #self.metadata is the same as one of the dictionaries in the 
        #list you get from LibrariesQuery
    def get_bibcodes(self):
        return self.bibcodes
    def get_remaining_queries(self):
        return self.response.headers['X-RateLimit-Remaining']

class LibraryQuery(BaseQuery):
    HTTP_ENDPOINT = "https://api.adsabs.harvard.edu/v1/biblib/libraries/{}"
    def __init__(self, lib_id, num_docs):
        self.HTTP_ENDPOINT = self.HTTP_ENDPOINT.format(lib_id)
        self.num_docs = num_docs
    def execute(self):
        self.response = LibResponse(
            self.session.get(self.HTTP_ENDPOINT,params={'rows':self.num_docs})
        )
        return self.response