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



# Set up program



# Parse command-line arguments

parser = argparse.ArgumentParser(description="Set up continuous pull replication between liftingcast.com CouchDB database and a local CouchDB database and update a file with the data to be displayed by the DRL lights/display program. Note that this script requires CouchDB to be locally accessible and running.")

parser.add_argument("-d", "--day-number", dest="day_number",
                    type=int,
                    required=True,
                    help="The platform ID")

parser.add_argument("-p", "--platform-id", dest="platform_id",
                    required=True,
                    help="The platform ID")

parser.add_argument("-o", "--output-file", dest="output_file",
                    required=False, default="~/drl-input.json",
                    help="The platform ID")

args = parser.parse_args()
day_number = args.day_number
platform_id = args.platform_id
output_file = args.output_file



# Set up meet ID and password for CouchDB database.

# TODO: There should be a function from the day the script is run to the meet ID and password for the meet (i.e., the database) for that day.
meet_id = "myvrzp8l3bty"
password = "xm4sj4ms"



print("Day {day} of the meet:\n    Meet ID: {meet}\n    Password: {pw}\nPlatform ID: {platform}\nDisplay data will be continually written to the file {out}\n  DRL should read in that file when it changes.".format(day=day_number, meet=meet_id, pw=password, platform=platform_id, out=output_file))




# Set up replication from liftingcast.com CouchDB to local CouchDB.

# Note that the example meet db uses admin party:
# liftingcast_client = CouchDB("", "", admin_party=True, url="http://couchdb.liftingcast.com", connect=True, auto_renew=True)
# liftingcast_db = cloudant.database.CouchDatabase(liftingcast_client, "mpcdahi7d1lz_readonly")

# An actual meet will not be admin party but will have a username and password:
# username: meet id, taken from URL when a new meet is created in liftingcast.com
# password: set when a new meet is created in liftingcast.com

# BBQ meet
# username: myvrzp8l3bty
# password: xm4sj4ms



liftingcast_client = CouchDB(meet_id, password, url="http://couchdb.liftingcast.com", connect=True, auto_renew=True)
liftingcast_db = liftingcast_client.create_database(meet_id)

local_client = CouchDB("", "", admin_party=True, url="http://127.0.0.1:5984", connect=True, auto_renew=True)
local_client.create_database("_replicator")
local_client.create_database("_global_changes")
local_db = local_client.create_database(meet_id)



# FIXME: We need to create a replication only if one does not already exist!
rep = cloudant.replicator.Replicator(local_client)

replication_doc = rep.create_replication(source_db=liftingcast_db, target_db=local_db, continuous=True)

pp = pprint.PrettyPrinter(indent=4)
print("Replication created!")
print("You can manage the replication from the Fauxton admin panel at http://127.0.0.1:5984/_utils/#/replication")
print("For reference, the replication doc is")
pp.pprint(replication_doc)
