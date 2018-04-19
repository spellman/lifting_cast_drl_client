import requests
import json
import urllib2



class db():
    def __init__(self, meetid, passwd):
        self.meetid = meetid
        self.passwd = passwd

    def fetch_doc_from_db(self, db_url, doc_id):
        return requests.get("{}/{}".format(db_url, doc_id),
                            auth=(self.meetid, self.passwd)).json()

    def private_put_doc_to_db(self, db_url, d, num_tries, max_tries):
        if num_tries > max_tries:
            raise Exception("Error putting document for update.")
        else:
            try:
                return requests.put("{}/{}".format(db_url, d["_id"]),
                                    auth=(self.meetid, self.passwd),
                                    data = json.dumps(d))
            except urllib2.HTTPError as e:
                if e.code == 409:
                    self.private_put_doc_to_db(db_url, d, num_tries + 1, max_tries)
                else:
                    raise e

    def put_doc_to_db(self, db_url, d):
        return self.private_put_doc_to_db(db_url, d, 0, 10)

class db_admin_party():
    def fetch_doc_from_db(self, db_url, doc_id):
        return requests.get("{}/{}".format(db_url, doc_id)).json()

    def private_put_doc_to_db(self, db_url, d, num_tries, max_tries):
        if num_tries > max_tries:
            raise Exception("Error putting document for update.")
        else:
            try:
                return requests.put("{}/{}".format(db_url, d["_id"]),
                                    data = json.dumps(d))
            except urllib2.HTTPError as e:
                if e.code == 409:
                    self.private_put_doc_to_db(db_url, d, num_tries + 1, max_tries)
                else:
                    raise e

    def put_doc_to_db(self, db_url, d):
        return self.private_put_doc_to_db(db_url, d, 0, 10)
