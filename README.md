Ensure CouchDB is installed, running, and accessible via requests to http://127.0.0.1:5984. `$ curl http://127.0.0.1:5984` should return `{"couchdb":"Welcome","version":"2.1.1","features":["scheduler"],"vendor":{"name":"The Apache Software Foundation"}}`

Ensure pip for Python 2 is installed. For Raspbian: `$ sudo apt-get install python-pip`   
`$ pip --version` should return meaningful info. E.g., `pip 10.0.0 from /usr/lib/python2.7/site-packages/pip (python 2.7)`.

Install dependencies. For Raspbian: `$ sudo pip install -r requirements.txt`
