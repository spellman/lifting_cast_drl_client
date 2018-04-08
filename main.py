import sys
import argparse
import pprint
from enum import Enum
from collections import namedtuple
from sortedcontainers import SortedListWithKey
from numbers import Number

try:
    from cloudant.client import CouchDB
    import cloudant
    from cloudant import replicator
except:
    print("cloudant is required. Please install it by running")
    print("sudo pip install cloudant")
    print("and then run this script again.")



pp = pprint.PrettyPrinter(indent=4)



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
# platform_id: pjspmhobe9kh



liftingcast_client = CouchDB(meet_id, password, url="http://couchdb.liftingcast.com", connect=True, auto_renew=True)
liftingcast_db = liftingcast_client.create_database(meet_id)

local_client = CouchDB("", "", admin_party=True, url="http://127.0.0.1:5984", connect=True, auto_renew=True)
local_client.create_database("_replicator")
local_client.create_database("_global_changes")
local_db = local_client.create_database(meet_id)



def is_our_meet_replication(replication_doc):
    return (replication_doc["source"]["url"] == liftingcast_db.database_url and
            replication_doc["target"]["url"] == local_db.database_url)

rep = cloudant.replicator.Replicator(local_client)

if any(is_our_meet_replication(d) for d in rep.list_replications()):
    print("Meet is already being replicated from liftingcast.com to our local CouchDB.")
else:
    replication_doc = rep.create_replication(source_db=liftingcast_db, target_db=local_db, continuous=True)

    print("Replication created.")
    print("You can manage the replication from the Fauxton admin panel at http://127.0.0.1:5984/_utils/#/replication")
    print("For reference or Curl actions, the replication doc is")
    pp.pprint(replication_doc)







# Make a view of the lifters on this platform

# platform_id = "pjspmhobe9kh"

lifters_on_platform = {
    "_id": "_design/liftersOnPlatform",
    "views": {
        "lifters-on-platform": {
            "map": "function (doc) {{\n  if (doc._id.substr(0, 1) === \"l\" && doc.platformId === \"{platform}\")\n  emit(doc._id);\n}}".format(platform=platform_id)
        }
    },
    "language": "javascript"
}

all_attempts = {
    "_id": "_design/allAttempts",
    "views": {
        "all-attempts": {
            "map": "function (doc) {\n  if (doc._id.substr(0, 1) === \"a\")\n  emit(doc._id);\n}"
        }
    },
    "language": "javascript"
}

lifters_on_platform_design_doc = local_db.create_document(lifters_on_platform)
all_attempts_design_doc = local_db.create_document(all_attempts)







class DocType(Enum):
    ATTEMPT = "a"
    DIVISION = "d"
    ENTRY = "e"
    LIFTER = "l"
    MEET = "m"
    PLATFORM = "p"
    REF = "r"
    RESTRICTED_LIFTER = "s"
    RESTRICTED_MEET = "n"
    WEIGHT_CLASS = "w"

def doc_id(doc):
    return doc["_id"]

def is_doc_of_type(doc, doc_type):
    return doc_id(doc)[:1] == doc_type.value

def get_lifters_on_platform():
    return local_db.get_view_result(lifters_on_platform_design_doc["_id"],
                                    "lifters-on-platform",
                                    include_docs=True)

def get_all_attempts():
    return local_db.get_view_result(all_attempts_design_doc["_id"],
                                    "all-attempts",
                                    include_docs=True)

LifterAttempt = namedtuple("LifterAttempt", ["lifter", "attempt"])

def get_all_lifter_attempts_on_platform(lifters_on_platform):
    lifters_by_id = {l["id"]: l["doc"] for l in lifters_on_platform}
    attempts_with_weights = [a for a in get_all_attempts() if "weight" in a["doc"] and isinstance(a["doc"]["weight"], Number) and a["doc"]["weight"] > 0]
    return [LifterAttempt(lifters_by_id.get(a["doc"]["lifterId"]), a["doc"]) for a in attempts_with_weights if lifters_by_id.get(a["doc"]["lifterId"]) is not None]

def lift_order(lift_name):
    # The return values here are not important. Only the order of the return
    # values is important. Since key-functions seems to be the Python 3 way of
    # sorting, as opposed to comparators, then I'm assuming numbers are ordered
    # in the usual way.
    if lift_name == "squat":
        return 0
    elif lift_name == "bench":
        return 1
    elif lift_name == "dead":
        return 2
    else:
        raise ValueError("Function argument lift_name was expected to be \"squat\", \"bench\", or \"dead\" but \"{}\" was received".format(lift_name))

def lifting_order(lifter_attempt):
    # The key endOfRound was added since the 2018 A&M BBQ meet, which we're
    # using in testing. The (constant) default value is for backwards
    # compatibility to that meet.
    l = lifter_attempt.lifter
    a = lifter_attempt.attempt
    return [l["session"],
            lift_order(a["liftName"]),
            l["flight"],
            a["attemptNumber"],
            a.get("endOfRound", 0),
            a["weight"],
            l["lot"]]

def sort_lifter_attempts(lifter_attempts):
    return SortedListWithKey(lifter_attempts, key=lifting_order)



# print(tabulate([[x.lifter["session"],
#                  x.attempt["liftName"],
#                  x.lifter["flight"],
#                  x.attempt["attemptNumber"],
#                  x.attempt["weight"],
#                  x.lifter["lot"]] for x in slas],
#                 headers=["Session", "Lift Order", "Flight", "Attempt #", "End Of Round", "Weight", "Lot #"],
#                 tablefmt='orgtbl'))

