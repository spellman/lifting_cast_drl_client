import requests
import json



class db():
    def __init__(self, meetid, passwd):
        self.meetid = meetid
        self.passwd = passwd

    def fetch_doc_from_db(self, db_url, doc_id):
        return requests.get("{}/{}".format(db_url, doc_id),
                            auth=(self.meetid, self.passwd)).json()

    def put_doc_to_db(self, db_url, d):
        return requests.put("{}/{}".format(db_url, d["_id"]),
                            auth=(self.meetid, self.passwd),
                            data = json.dumps(d))

class db_admin_party():
    def fetch_doc_from_db(self, db_url, doc_id):
        return requests.get("{}/{}".format(db_url, doc_id)).json()

    def put_doc_to_db(self, db_url, d):
        return requests.put("{}/{}".format(db_url, d["_id"]),
                            data = json.dumps(d))
