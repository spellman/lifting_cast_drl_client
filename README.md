Ensure CouchDB is installed, running, and accessible via requests to http://127.0.0.1:5984. `$ curl http://127.0.0.1:5984` should return `{"couchdb":"Welcome","version":"2.1.1","features":["scheduler"],"vendor":{"name":"The Apache Software Foundation"}}`

Ensure pip for Python 2 is installed. For Raspbian: `$ sudo apt-get install python-pip`   
`$ pip --version` should return meaningful info. E.g., `pip 10.0.0 from /usr/lib/python2.7/site-packages/pip (python 2.7)`

Install dependencies. For Raspbian: `$ sudo pip install -r requirements.txt`

Run the script to continually feed data from liftingcast.com to DRL with python 2. Provide command-line arguments day number and platform number. For Raspbian: `$ python liftingcast_to_drl.py -d 1 -p 1`   
Note that the DJ Pi runs an older version of Python (2.7.9) and so requires that .value() calls be removed from enums; they are their value.
