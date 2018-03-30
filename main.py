import sys
import argparse
import pprint

try:
    from cloudant.client import CouchDB
    import cloudant
    from cloudant import replicator
except:
    print("cloudant is required. Please install it by running")
    print("sudo pip install cloudant")
    print("and then run this script again.")



# Parse command-line arguments

parser = argparse.ArgumentParser(description='Set up pull replication between liftingcast.com CouchDB database and a local CouchDB database. Note that this script requires CouchDB to be locally installed and running.')

parser.add_argument('-m', '--meet-id', dest="meet_id",
                    required=True,
                    help='The meet ID, obtained from the meet URL at liftingcast.com.\nExample: 2018 Texas A&M BBQ meet:\nIn https://www.liftingcast.com/meets/myvrzp8l3bty, the meet ID is myvrzp8l3bty.')

parser.add_argument('-p', '--password', dest="password",
                    required=True,
                    help='The password that was set for this meet when the meet was created in liftingcast.com.')

args = parser.parse_args()
meet_id = args.meet_id
password = args.password

print("Meet id is {}.\nPassword is {}".format(meet_id, password))



# Set up replication from liftingcast.com CouchDB to local CouchDB.

# Note that the example meet db uses admin party:
# source_client = CouchDB("", "", admin_party=True, url="http://couchdb.liftingcast.com", connect=True, auto_renew=True)
# source_db = cloudant.database.CouchDatabase(source_client, "mpcdahi7d1lz_readonly")

# An actual meet will not be admin party but will have a username and password:
# username: meet id, taken from URL when a new meet is created in liftingcast.com
# password: set when a new meet is created in liftingcast.com

# BBQ meet
# username: myvrzp8l3bty
# password: xm4sj4ms



source_client = CouchDB(meet_id, password, url="http://couchdb.liftingcast.com", connect=True, auto_renew=True)
source_db = source_client.create_database(meet_id)

target_client = CouchDB("", "", admin_party=True, url="http://127.0.0.1:5984", connect=True, auto_renew=True)
target_client.create_database("_replicator")
target_client.create_database("_global_changes")
target_db = target_client.create_database(meet_id)



rep = cloudant.replicator.Replicator(target_client)

replication_doc = rep.create_replication(source_db=source_db, target_db=target_db, continuous=True)

pp = pprint.PrettyPrinter(indent=4)
print("Replication created!")
print("You can manage the replication from the Fauxton admin panel at http://127.0.0.1:5984/_utils/#/replication")
print("For reference, the replication doc is")
pp.pprint(replication_doc)
