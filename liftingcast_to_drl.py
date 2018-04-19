#!/usr/bin/env python2

import sys
import os
import argparse
import pprint
import traceback
import json
from collections import namedtuple, OrderedDict
from numbers import Number
import datetime
from time import sleep
from db_util import db_admin_party

try:
    from cloudant.client import CouchDB
    import cloudant
    from cloudant import replicator
    from enum import Enum
except:
    print traceback.format_exc()
    print "Missing depedencies. Connect to the internet and install them by running"
    print "    sudo pip install -r requirements.txt"
    print "Then run this script again."







pp = pprint.PrettyPrinter(indent=4)

def timestamp():
    return datetime.datetime.now().replace(microsecond=0).isoformat()







# Set up program



# Parse command-line arguments

parser = argparse.ArgumentParser(description="Set up continuous pull replication between liftingcast.com CouchDB database and a local CouchDB database and update a file with the data to be displayed by the DRL lights/display program. Note that this script requires CouchDB to be locally accessible and running.")

parser.add_argument("-d", "--day-number", dest="day_number",
                    required=True,
                    help="The day number within 2018 Collegiate Nationals: 1 for Thursday, 2 for Friday, 3 for Saturday, 4 for Sunday")

ARGS = parser.parse_args()
DAY_NUMBER = ARGS.day_number



# Set up platform ID, meet ID, and meet password

PLATFORM_ID_FILE = "platform-id"

try:
    with open(PLATFORM_ID_FILE, "r") as f:
        PLATFORM_ID = f.readline().rstrip()
except IOError:
    print "Could not find {}.".format(PLATFORM_ID_FILE)
    print "Make a file called {} at top level of the project, containing only the platform ID for which this Raspberry Pi will be used.".format(PLATFORM_ID_FILE)
    print "Example {}:".format(PLATFORM_ID_FILE)
    print "pjspmhobe9kh"
    sys.exit(1)




OUTPUT_FILE_FILE = "output-file"


try:
    with open(OUTPUT_FILE_FILE, "r") as f:
        OUTPUT_FILE = f.readline().rstrip()

    os.remove(OUTPUT_FILE)

except IOError:
    print "Could not find {}.".format(OUTPUT_FILE_FILE)
    print "Make a file called {} at top level of the project, containing only file path of the file to which this script will write current lifter data and which DRL will read in.".format(OUTPUT_FILE_FILE)
    print "Example {}:".format(OUTPUT_FILE_FILE)
    print "drl-input.json"
    sys.exit(1)
except OSError:
    pass



MEET_CREDENTIALS_FILE = "meet-credentials.json"

try:
    with open(MEET_CREDENTIALS_FILE, "r") as f:
        MEETS_BY_DAY = json.load(f)
        print "\n\nMEETS_BY_DAY"
        pp.pprint(MEETS_BY_DAY)
        print "\n\n"
        MEET = MEETS_BY_DAY[DAY_NUMBER]
        MEET_ID = MEET["meet_id"]
        PASSWORD = MEET["password"]
except IOError:
    print "Could not find {}.".format(MEET_CREDENTIALS_FILE)
    print "{} is a JSON file that maps a day to the meet ID and password for that day's \"meet\" in liftingcast.com. Place it at the top level of this project".format(MEET_CREDENTIALS_FILE)
    print "Example {}:".format(MEET_CREDENTIALS_FILE)
    pp.pprint(json.dumps({
        "1": {"meet_id": "mIZBmLDa4wVXu8aK",
              "password": "MkojKWse7damCtQL"},
        "2": {"meet_id": "IJKgVqAtyGKbC1zW",
              "password": "aZJonoH4yfRl4zK1"},
        "3": {"meet_id": "XapITaFKcThBMY1C",
              "password": "cR5VLkToc9Pr/G0e"},
        "4": {"meet_id": "NdwoWgdTK4gsH7w0",
              "password": "lQGIbdIeKljK1Tdv"}
    }))
    sys.exit(1)



print "\n{}  Started\n".format(timestamp())
print """Day {day_number} of the meet:
Meet ID: {meet_id}
Password: {password}
Platform ID: {platform_id}
Output file: {output_file}""".format(day_number=DAY_NUMBER,
                                     meet_id=MEET_ID,
                                     password=PASSWORD,
                                     platform_id=PLATFORM_ID,
                                     output_file=OUTPUT_FILE)


# Set up global database util for fetch and put
g_db = db_admin_party()


# Set up replication from liftingcast.com CouchDB to local CouchDB.

# Note that the example meet db uses admin party:
# liftingcast_client = CouchDB("", "", admin_party=True, url="http://couchdb.liftingcast.com", connect=True, auto_renew=True)
# liftingcast_db = cloudant.database.CouchDatabase(liftingcast_client, "mpcdahi7d1lz_readonly")

# An actual meet will not be admin party but will have a username and password:
# username: meet id, taken from URL when a new meet is created in liftingcast.com
# password: set when a new meet is created in liftingcast.com

# BBQ meet
# username: myvrzp8l3bty
# PASSWORD: xm4sj4ms
# PLATFORM_ID: pjspmhobe9kh



liftingcast_client = CouchDB(MEET_ID,
                             PASSWORD,
                             url="http://couchdb.liftingcast.com",
                             connect=True,
                             auto_renew=True)
liftingcast_db = liftingcast_client.create_database(MEET_ID)

local_client = CouchDB("",
                       "",
                       admin_party=True,
                       url="http://127.0.0.1:5984",
                       connect=True,
                       auto_renew=True)
local_client.create_database("_replicator")
local_client.create_database("_global_changes")
local_db = local_client.create_database(MEET_ID)



def is_our_meet_replication(replication_doc):
    return (replication_doc["source"]["url"] == liftingcast_db.database_url and
            replication_doc["target"]["url"] == local_db.database_url)

rep = cloudant.replicator.Replicator(local_client)

if any(is_our_meet_replication(d) for d in rep.list_replications()):
    print "{}  Meet is already being replicated from liftingcast.com to our local CouchDB.".format(timestamp())
else:
    replication_doc = rep.create_replication(source_db=liftingcast_db,
                                             target_db=local_db,
                                             continuous=True)

    print "{}  Replication created.".format(timestamp())
    print "You can manage the replication from the Fauxton admin panel at http://127.0.0.1:5984/_utils/#/replication"
    print "For reference, use with Curl, etc., the replication doc is"
    pp.pprint(replication_doc)







# Make a view of the lifters on this platform

# PLATFORM_ID = "pjspmhobe9kh"

lifters_on_platform = {
    "_id": "_design/liftersOnPlatform",
    "views": {
        "lifters-on-platform": {
            "map": "function (doc) {{\n  if (doc._id.substr(0, 1) === \"l\" && doc.platformId === \"{platform_id}\")\n  emit(doc._id);\n}}".format(platform_id=PLATFORM_ID)
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

# Try to delete existing views because they may be for a different platform.
try:
    print "Deleting existing views so we can create fresh ones for this platform."
    local_db["_design/liftersOnPlatform"].delete()
    local_db["_design/allAttempts"].delete()
except KeyError:
    print "Views did not already exist -- we're good to create them fresh."

# Create views for this platform.
lifters_on_platform_design_doc = local_db.create_document(lifters_on_platform)
all_attempts_design_doc = local_db.create_document(all_attempts)

print "{}  lifters_on_platform and all_attempts views exist".format(timestamp())



print "{}  Initializing platform and current attempt...".format(timestamp())

g_current_attempt = {}

while True:
    try:
        initial_platform = g_db.fetch_doc_from_db(local_db.database_url,
                                                  PLATFORM_ID)

        if initial_platform.get("currentAttemptId"):
            g_current_attempt = g_db.fetch_doc_from_db(local_db.database_url,
                                                       initial_platform["currentAttemptId"])

        break
    except KeyError:
        print "{}  Waiting for platform and current attempt docs to sync to local database...".format(timestamp())
        sleep(5)

print "{}  Initialized platform and current attempt.\n\n".format(timestamp())



def current_attempt_id():
    return g_current_attempt.get("_id")

def current_lifter_id():
    return g_current_attempt.get("lifterId")

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


# React to items in local db _changes feed.

def get_lifters_on_platform():
    return local_db.get_view_result(lifters_on_platform_design_doc["_id"],
                                    "lifters-on-platform",
                                    include_docs=True)

def get_all_attempts():
    return local_db.get_view_result(all_attempts_design_doc["_id"],
                                    "all-attempts",
                                    include_docs=True)

LifterAttempt = namedtuple("LifterAttempt", ["lifter", "attempt"])

def is_valid_attempt_for_lifting_order(attempt):
    return ("weight" in attempt and
            isinstance(attempt["weight"], Number) and
            attempt["weight"] > 0)

def get_lifter_attempts_for_platform_lifting_order():
    lifters_on_platform = get_lifters_on_platform()
    lifters_by_id = {l["id"]: l["doc"] for l in lifters_on_platform}

    attempts = get_all_attempts()
    lifter_attempts = [LifterAttempt(lifters_by_id.get(a["doc"]["lifterId"]), a["doc"]) for a in attempts]
    # Remove lifter_attempts for lifters not on this platform and attempts
    # without weights or with non-Numeric or non-positive weights.
    attempt_lifters_in_the_lifting_order = [la for la in lifter_attempts if (
        la.lifter is not None and is_valid_attempt_for_lifting_order(la.attempt)
    )]
    return attempt_lifters_in_the_lifting_order

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
    return sorted(lifter_attempts, key=lifting_order)

def get_lifting_order():
    return sort_lifter_attempts(get_lifter_attempts_for_platform_lifting_order())

def get_attempts_to_be_done(lifter_attempts):
    return [la for la in lifter_attempts if not la.attempt.get("result")]

def get_lifting_order_to_be_done():
    return get_attempts_to_be_done(get_lifting_order())



def get_all_attempts_for_lifter(lifter_id):
    return [a["doc"] for a in get_all_attempts() if a["doc"]["lifterId"] == lifter_id]

def get_current_lifter():
    return g_db.fetch_doc_from_db(local_db.database_url, current_lifter_id())

def get_current_lifter_attempt():
    lifting_order_to_be_done = get_lifting_order_to_be_done()
    if len(lifting_order_to_be_done) > 0:
        return lifting_order_to_be_done[0]
    else:
        return None



def is_heartbeat(change):
    return change is None


def is_different_attempt(change):
    doc = change["doc"]
    return (is_doc_of_type(doc, DocType.PLATFORM) and
            (doc.get("currentAttemptId") != current_attempt_id()))

def is_change_to_current_attempt(doc):
    return (is_doc_of_type(doc, DocType.ATTEMPT) and
            (doc_id(doc) == current_attempt_id()))

possible_lift_results = ["good", "bad"]

def is_first_decision_on_current_attempt(change):
    doc = change["doc"]
    return (is_change_to_current_attempt(doc) and
            doc.get("result") in possible_lift_results and
            not g_current_attempt.get("result") in possible_lift_results)

def is_change_to_current_lifter(change):
    doc = change["doc"]
    return (is_doc_of_type(doc, DocType.LIFTER) and
            doc_id(doc) == current_lifter_id())

def is_change_to_some_attempt_of_current_lifter(change):
    doc = change["doc"]
    return (is_doc_of_type(doc, DocType.ATTEMPT) and
            doc["lifterId"] == current_lifter_id())



def lifter_to_display_lifter(lifter):
    return OrderedDict([
        ("name", lifter.get("name")),
        ("team_name", lifter.get("team"))
    ])

lift_names_to_display_lift_names = {"squat": "squat",
                                    "bench": "bench",
                                    "dead": "deadlift"}

def display_lift_name(attempt):
    return lift_names_to_display_lift_names.get(attempt.get("liftName"))

def current_attempt_to_display_current_attempt(current_attempt):
    return OrderedDict([
        ("current_lift", display_lift_name(current_attempt)),
        ("current_attempt_number", current_attempt.get("attemptNumber"))
    ])

def make_attempt_weight_key(attempt):
    return "{lift_name}_{attempt_number}_weight".format(lift_name=display_lift_name(attempt),
                                                        attempt_number=attempt["attemptNumber"])

def make_attempt_result_key(attempt):
    return "{lift_name}_{attempt_number}_result".format(lift_name=display_lift_name(attempt),
                                                        attempt_number=attempt["attemptNumber"])

def attempts_to_display_attempts(attempts):
    attempt_weights = {make_attempt_weight_key(attempt): attempt.get("weight") for attempt in attempts}
    attempt_results = {make_attempt_result_key(attempt): attempt.get("result") for attempt in attempts}

    result = OrderedDict()
    result["squat_1_weight"] = attempt_weights.get("squat_1_weight")
    result["squat_1_result"] = attempt_results.get("squat_1_result")
    result["squat_2_weight"] = attempt_weights.get("squat_2_weight")
    result["squat_2_result"] = attempt_results.get("squat_2_result")
    result["squat_3_weight"] = attempt_weights.get("squat_3_weight")
    result["squat_3_result"] = attempt_results.get("squat_3_result")
    result["bench_1_weight"] = attempt_weights.get("bench_1_weight")
    result["bench_1_result"] = attempt_results.get("bench_1_result")
    result["bench_2_weight"] = attempt_weights.get("bench_2_weight")
    result["bench_2_result"] = attempt_results.get("bench_2_result")
    result["bench_3_weight"] = attempt_weights.get("bench_3_weight")
    result["bench_3_result"] = attempt_results.get("bench_3_result")
    result["deadlift_1_weight"] = attempt_weights.get("deadlift_1_weight")
    result["deadlift_1_result"] = attempt_results.get("deadlift_1_result")
    result["deadlift_2_weight"] = attempt_weights.get("deadlift_2_weight")
    result["deadlift_2_result"] = attempt_results.get("deadlift_2_result")
    result["deadlift_3_weight"] = attempt_weights.get("deadlift_3_weight")
    result["deadlift_3_result"] = attempt_results.get("deadlift_3_result")
    return result



def update_display_data(lifter, current_attempt):
    """The output file is a JSON file of the form
    {
      "name": "Tony Cardella",
      "team_name": "USA",
      "current_lift": "deadlift",
      "current_attempt_number": "2",
      "squat_1_weight": 357.5,
      "squat_1_result": "good",
      "squat_2_weight": 375.0,
      "squat_2_result": "good",
      "squat_3_weight": 390.0,
      "squat_3_result": "good",
      "bench_1_weight": 255.0,
      "bench_1_result": "good",
      "bench_2_weight": 265.0,
      "bench_2_result": "good",
      "bench_3_weight": 272.5,
      "bench_3_result": "bad",
      "deadlift_1_weight": 330.0,
      "deadlift_1_result": "good",
      "deadlift_2_weight": 355.0,
      "deadlift_2_result": null,
      "deadlift_3_weight": null,
      "deadlift_3_result": null
    }
    """
    if lifter is None:
        l = {}
        a = {}
        all_attempts_for_lifter = []
    else:
        l = lifter
        a = current_attempt
        all_attempts_for_lifter = get_all_attempts_for_lifter(doc_id(l))

    new_display_data = OrderedDict()
    new_display_data.update(lifter_to_display_lifter(l))
    new_display_data.update(current_attempt_to_display_current_attempt(a))
    new_display_data.update(attempts_to_display_attempts(all_attempts_for_lifter))

    # w+ open mode should open the file for overwriting its contents, creating
    # the file if it doesn't exist.
    with open(OUTPUT_FILE, "w+") as f:
        f.seek(0)
        json.dump(new_display_data, f, indent=4)







# This is the duration to which DRL sets its timer after a decision is inputted.
# NOTHING IS ENFORCING THAT RELATIONSHIP!
# Advancing liftingcast from here, though, means that DRL doesn't have to
# maintain local state to track the current attempt.
INITIAL_CLOCK_VALUE_IN_MILLISECONDS = 60000

def advance_liftingcast_to_next_lifter(next_lifter_attempt):
    if next_lifter_attempt is None:
        next_attempt_id = None
    else:
        next_attempt_id = doc_id(next_lifter_attempt.attempt)

    platform = g_db.fetch_doc_from_db(local_db.database_url, PLATFORM_ID)
    platform["currentAttemptId"] = next_attempt_id
    platform["clockState"] = "initial"
    platform["clockTimerLength"] = INITIAL_CLOCK_VALUE_IN_MILLISECONDS
    g_db.put_doc_to_db(local_db.database_url, platform)







# Init output file with current attempt if there is one.
if is_valid_attempt_for_lifting_order(g_current_attempt):
    current_lifter_attempt = get_current_lifter_attempt()
    update_display_data(current_lifter_attempt.lifter, g_current_attempt)
else:
    update_display_data(None, None)



# style="main_only" => Only "winning" revisions are selected from the _changes
#   feed; no conflicts or deleted former-conflicts.
changes = local_db.infinite_changes(since="now",
                                    heartbeat=60000,
                                    include_docs=True,
                                    style="main_only")

print "{timestamp}  {output_file} will be continually updated with display data for DRL to read in:\n".format(timestamp=timestamp(),
                                                                                                              output_file=OUTPUT_FILE)

for change in changes:
    if change is None or is_doc_of_type(change.get("doc"), DocType.REF):
        continue



    if is_heartbeat(change):
        print "{}  heartbeat -- still connected to db _changes feed".format(timestamp())



    elif is_different_attempt(change):
        print "\"Current attempt\" set to different attempt"
        pp.pprint(change)
        print "\n"

        # This does not use the order because this handles a manual change
        # of lifter.
        new_current_attempt_id = change["doc"]["currentAttemptId"]
        if new_current_attempt_id:
            new_current_attempt = g_db.fetch_doc_from_db(local_db.database_url,
                                                         new_current_attempt_id)
            if is_valid_attempt_for_lifting_order(new_current_attempt):
                g_current_attempt = new_current_attempt
                update_display_data(get_current_lifter(), g_current_attempt)



    elif is_first_decision_on_current_attempt(change):
        print "Decision on current attempt"
        pp.pprint(change)
        print "\n"

        # The decision has already been made on current_attempt
        # so the current LifterAttempt in the lifting order is
        # the next LifterAttempt from the point of view of this
        # script.
        next_lifter_attempt = get_current_lifter_attempt()
        if next_lifter_attempt:
            (next_lifter, next_attempt) = next_lifter_attempt
            g_current_attempt = next_attempt
            update_display_data(next_lifter, next_attempt)
        else:
            update_display_data(None, None)

        advance_liftingcast_to_next_lifter(next_lifter_attempt)



    elif is_change_to_current_lifter(change):
        print "Change to current lifter"
        pp.pprint(change)
        print "\n"

        update_display_data(get_current_lifter(), g_current_attempt)



    elif is_doc_of_type(change.get("doc"), DocType.ATTEMPT):
        print "Other attempt"
        pp.pprint(change)
        print "\n"

        lo = get_lifting_order_to_be_done()
        if len(lo) == 0:
            g_current_attempt = None
            update_display_data(None, None)
            advance_liftingcast_to_next_lifter(None)
        else:
            current_lifter_attempt = lo[0]
            g_current_attempt = current_lifter_attempt.attempt
            update_display_data(current_lifter_attempt.lifter,
                                current_lifter_attempt.attempt)
            advance_liftingcast_to_next_lifter(current_lifter_attempt)



    else:
        print "Unhandled change"
        pp.pprint(change)
        print "\n"
