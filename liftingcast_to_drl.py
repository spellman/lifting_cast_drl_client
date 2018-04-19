#!/usr/bin/env python2

import sys
import argparse
import pprint
import traceback
import json
from collections import namedtuple, OrderedDict
from numbers import Number
import datetime
from time import sleep

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
except IOError:
    print "Could not find {}.".format(OUTPUT_FILE_FILE)
    print "Make a file called {} at top level of the project, containing only file path of the file to which this script will write current lifter data and which DRL will read in.".format(OUTPUT_FILE_FILE)
    print "Example {}:".format(OUTPUT_FILE_FILE)
    print "drl-input.json"
    sys.exit(1)



MEET_CREDENTIALS_FILE = "meet-credentials.json"

try:
    with open(MEET_CREDENTIALS_FILE, "r") as f:
        MEETS_BY_DAY = json.load(f)
        print "\n\nMEETS_BY_DAY"
        pp.pprint(MEETS_BY_DAY)
        print "\n\n"
        MEET = MEETS_BY_DAY.get(DAY_NUMBER)
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
print "Day {day_number} of the meet:\n    Meet ID: {meet_id}\n    Password: {password}\nPlatform ID: {platform_id}\nOutput file: {output_file}\n".format(day_number=DAY_NUMBER,
                                                               meet_id=MEET_ID,
                                                               password=PASSWORD,
                                                               platform_id=PLATFORM_ID,
                                                               output_file=OUTPUT_FILE)







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
    return (replication_doc.get("source").get("url") == liftingcast_db.database_url and
            replication_doc.get("target").get("url") == local_db.database_url)

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








current_attempt = {}

while True:
    try:
        initial_platform = local_db[PLATFORM_ID]

        if initial_platform["currentAttemptId"]:
            current_attempt = local_db[initial_platform["currentAttemptId"]]

        break
    except KeyError:
        print "{}  Waiting for platform and current attempt docs to sync to local database...".format(timestamp())
        sleep(5)

print "{}  Initialized platform and current attempt.\n\n".format(timestamp())



def current_attempt_id():
    return current_attempt.get("_id")

def current_lifter_id():
    return current_attempt.get("lifterId")

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
    return doc.get("_id")

def is_doc_of_type(doc, doc_type):
    return doc_id(doc)[:1] == doc_type.value


# React to items in local db _changes feed.

def get_all_docs():
    rows = local_db.all_docs(include_docs=True).get("rows")
    return [row.get("doc") for row in rows if row.get("doc")]

def get_lifters_on_platform():
    all_docs = get_all_docs()
    return [doc for doc in all_docs if is_doc_of_type(doc, DocType.LIFTER) and doc.get("platformId") == PLATFORM_ID]

def get_all_attempts():
    all_docs = get_all_docs()
    return [doc for doc in all_docs if is_doc_of_type(doc, DocType.ATTEMPT)]

LifterAttempt = namedtuple("LifterAttempt", ["lifter", "attempt"])

def is_valid_attempt_for_lifting_order(attempt):
    return ("weight" in attempt and
            isinstance(attempt.get("weight"), Number) and
            attempt.get("weight") > 0)

def get_lifter_attempts_for_platform_lifting_order():
    lifters_on_platform = get_lifters_on_platform()
    lifters_by_id = {doc_id(l): l for l in lifters_on_platform}

    attempts = get_all_attempts()
    lifter_attempts = [LifterAttempt(lifters_by_id.get(a.get("lifterId")), a) for a in attempts]
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
    return [l.get("session"),
            lift_order(a.get("liftName")),
            l.get("flight"),
            a.get("attemptNumber"),
            a.get("endOfRound", 0),
            a.get("weight"),
            l.get("lot")]

def sort_lifter_attempts(lifter_attempts):
    return sorted(lifter_attempts, key=lifting_order)

def get_lifting_order():
    return sort_lifter_attempts(get_lifter_attempts_for_platform_lifting_order())

def get_attempts_to_be_done(lifter_attempts):
    return [la for la in lifter_attempts if not la.attempt.get("result")]

def get_lifting_order_to_be_done():
    return get_attempts_to_be_done(get_lifting_order())



def get_all_attempts_for_lifter(lifter_id):
    return [a for a in get_all_attempts() if a.get("lifterId") == lifter_id]

def get_current_lifter():
    return local_db.get(current_lifter_id())

def get_next_lifter():
    lifting_order_to_be_done = get_lifting_order_to_be_done()
    if len(lifting_order_to_be_done) > 0:
        return lifting_order_to_be_done[0]
    else:
        return None



def is_heartbeat(change):
    return change is None


def is_different_attempt(change):
    doc = change.get("doc")
    return (is_doc_of_type(doc, DocType.PLATFORM) and
            doc_id(doc) == PLATFORM_ID and
            doc.get("currentAttemptId") != current_attempt_id())

def is_change_to_current_attempt(doc):
    return (is_doc_of_type(doc, DocType.ATTEMPT) and
            doc_id(doc) == current_attempt_id())

possible_lift_results = ["good", "bad"]

def is_first_decision_on_attempt(doc):
    decisions = [c for c in doc.get("changes", []) if c.get("attribute") == "result" and c.get("value") in possible_lift_results]
    return (len(decisions) == 1 and
            decisions[0].get("value") == doc.get("result"))

def is_first_decision_on_current_attempt(change):
    doc = change.get("doc")
    return (is_change_to_current_attempt(doc) and
            is_first_decision_on_attempt(doc))

def is_change_to_current_lifter(change):
    doc = change.get("doc")
    return (is_doc_of_type(doc, DocType.LIFTER) and
            doc_id(doc) == current_lifter_id())

def is_change_to_some_attempt_of_current_lifter(change):
    doc = change.get("doc")
    return (is_doc_of_type(doc, DocType.ATTEMPT) and
            doc.get("lifterId") == current_lifter_id())



def lifter_to_display_lifter(lifter):
    if lifter is None:
        l = {}
    else:
        l = lifter

    return OrderedDict([
        ("name", l.get("name")),
        ("team_name", l.get("team"))
    ])

lift_names_to_display_lift_names = {"squat": "squat",
                                    "bench": "bench",
                                    "dead": "deadlift"}

def display_lift_name(attempt):
    return lift_names_to_display_lift_names.get(attempt.get("liftName"));

def current_attempt_to_display_current_attempt(current_attempt):
    if current_attempt is None:
        a = {}
    else:
        a = current_attempt

    return OrderedDict([
        ("current_lift", display_lift_name(a)),
        ("current_attempt_number", a.get("attemptNumber"))
    ])

def make_attempt_weight_key(attempt):
    return "{lift_name}_{attempt_number}_weight".format(lift_name=display_lift_name(attempt),
                                                        attempt_number=attempt.get("attemptNumber"))

def make_attempt_result_key(attempt):
    return "{lift_name}_{attempt_number}_result".format(lift_name=display_lift_name(attempt),
                                                        attempt_number=attempt.get("attemptNumber"))

def attempts_to_display_attempts(attempts):
    attempt_weights = {make_attempt_weight_key(attempt): attempt.get("weight", "") for attempt in attempts}
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



def update_display_data(lifter, current_attempt, attempts_for_lifter):
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
    new_display_data = OrderedDict()
    new_display_data.update(lifter_to_display_lifter(lifter))
    new_display_data.update(current_attempt_to_display_current_attempt(current_attempt))
    new_display_data.update(attempts_to_display_attempts(attempts_for_lifter))

    # w+ open mode should open the file for overwriting its contents, creating
    # the file if it doesn't exist.
    with open(OUTPUT_FILE, "w+") as f:
        f.seek(0)
        json.dump(new_display_data, f, indent=4)



# Init output file with current attempt if there is one.
if is_valid_attempt_for_lifting_order(current_attempt):
    update_display_data(get_current_lifter(),
                        current_attempt,
                        get_all_attempts_for_lifter(current_lifter_id()))



# style="main_only" => Only "winning" revisions are selected from the _changes
#   feed; no conflicts or deleted former-conflicts.
changes = local_db.infinite_changes(since="now",
                                    heartbeat=10000,
                                    include_docs=True,
                                    style="main_only")

print "{timestamp}  {output_file} will be continually updated with display data for DRL to read in:\n".format(timestamp=timestamp(),
                                                                                                              output_file=OUTPUT_FILE)

for change in changes:
    if is_heartbeat(change):
        print "{}  heartbeat -- still connected to db _changes feed".format(timestamp())
        print "current attempt"
        pp.pprint(current_attempt)
        print "\n"



    elif is_different_attempt(change):
        print "\"Current attempt\" set to different attempt"
        pp.pprint(change)
        print "\n"

        # Is this hitting the db or just a cache? We need it up-to-date.
        new_current_attempt_id = change.get("doc").get("currentAttemptId")
        if new_current_attempt_id:
            new_current_attempt = local_db.get(new_current_attempt_id)
            if (is_valid_attempt_for_lifting_order(new_current_attempt)):
                current_attempt = new_current_attempt
                update_display_data(get_current_lifter(),
                                    current_attempt,
                                    get_all_attempts_for_lifter(current_lifter_id()))



    elif is_first_decision_on_current_attempt(change):
        print "Decision on current attempt"
        pp.pprint(change)
        print "\n"

        next_lifter_attempt = get_next_lifter()
        if next_lifter_attempt:
            (next_lifter, next_attempt) = next_lifter_attempt
            current_attempt = next_attempt
            update_display_data(next_lifter,
                                next_attempt,
                                get_all_attempts_for_lifter(next_lifter.get("_id")))
        else:
            update_display_data(get_current_lifter(),
                                change.get("doc"),
                                get_all_attempts_for_lifter(current_lifter_id()))



    elif is_change_to_current_lifter(change):
        print "Change to current lifter"
        pp.pprint(change)
        print "\n"

        update_display_data(get_current_lifter(),
                            current_attempt,
                            get_all_attempts_for_lifter(current_lifter_id()))



    elif is_change_to_some_attempt_of_current_lifter(change):
        print "Change to some attempt of current lifter"
        pp.pprint(change)
        print "\n"

        if is_valid_attempt_for_lifting_order(change.get("doc")):
            update_display_data(get_current_lifter(),
                                current_attempt,
                                get_all_attempts_for_lifter(current_lifter_id()))



    else:
        print "Unhandled change"
        pp.pprint(change)
        print "\n"

