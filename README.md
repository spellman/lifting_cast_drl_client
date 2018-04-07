Ensure CouchDB is installed, running, and accessible via requests to http://127.0.0.1:5984. `$ curl http://127.0.0.1:5984` should return `{"couchdb":"Welcome","version":"2.1.1","features":["scheduler"],"vendor":{"name":"The Apache Software Foundation"}}`

Ensure pip for Python 3 is installed: `$ pip --version` should return meaningful info. E.g., `pip 9.0.3 from /usr/lib/python3.6/site-packages (python 3.6)`

Install dependencies: `$ pip install -r requirements.txt`
