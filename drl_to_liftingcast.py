# This is not a script to be run.
# This is a library to be imported into and used by DRL.

import sys
import traceback
import json
import pprint
import datetime
import urllib2
from db_util import db

try:
    from cloudant.client import CouchDB
except:
    print traceback.format_exc()
    print "Missing depedencies. Connect to the internet and install them by running"
    print "    sudo pip install -r requirements.txt"
    print "Then run this script again."



pp = pprint.PrettyPrinter(indent=4)


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



DAY_NUMBER_FILE = "day-number"

try:
    with open(DAY_NUMBER_FILE, "r") as f:
        DAY_NUMBER = f.readline().rstrip()
except IOError:
    print "Could not find {}.".format(DAY_NUMBER_FILE)
    print "Make a file called {} at top level of the project, containing only the day number within 2018 Collegiate Nationals:\n  1 for Thursday\n  2 for Friday\n  3 for Saturday\n  4 for Sunday".format(DAY_NUMBER_FILE)
    print "2018 Collegiate Nationals, a 4-day event, is represented as 4 separate \"meets\" inliftingcast.com. The day number determines which of those \"meets\" is used."
    print "Example {}:".format(DAY_NUMBER_FILE)
    print 1
    sys.exit(1)



MEET_CREDENTIALS_FILE = "meet-credentials.json"

try:
    with open(MEET_CREDENTIALS_FILE, "r") as f:
        MEETS_BY_DAY = json.load(f)
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

# Set up global db class for fetch and put to db
g_db = db(MEET_ID, PASSWORD)



def timestamp():
    return datetime.datetime.now().replace(microsecond=0).isoformat()



# Set up liftingcast client and database

liftingcast_client = CouchDB(MEET_ID,
                             PASSWORD,
                             url="http://couchdb.liftingcast.com",
                             connect=True,
                             auto_renew=True)
liftingcast_db = liftingcast_client[MEET_ID]

print "{}  liftingcast db client set up.".format(timestamp())







# DRL light/card values are booleans.

def drl_lights_to_liftingcast_decision(white, red, blue, yellow):
    if white:
        return "good"
    else:
        return "bad"

def drl_lights_to_cards(red, blue, yellow):
    return {"red": red, "blue": blue, "yellow": yellow}

def drl_lights_to_decision_cards(white, red, blue, yellow):
    """Takes 4 booleans representing a referee's white light and red, blue, and
    yellow cards and returns a map of decision and cards.

    white, red, blue, yellow

    => {"decision": "good" | "bad",
        "cards": {"red": True | False,
                  "blue": True | False,
                  "yellow": True | False}}
    """
    return {"decision": drl_lights_to_liftingcast_decision(white, red, blue, yellow),
            "cards": drl_lights_to_cards(red, blue, yellow)}

def drl_decisions_to_liftingcast_decisions(left_white,
                                           left_red,
                                           left_blue,
                                           left_yellow,
                                           head_white,
                                           head_red,
                                           head_blue,
                                           head_yellow,
                                           right_white,
                                           right_red,
                                           right_blue,
                                           right_yellow):
    """Takes 12 booleans representing the left, head, and right referee
    lights/cards, and returns a map of referee to decision and cards.

    left_white, left_red, left_blue, left_yellow,
    head_white, head_red, head_blue, head_yellow,
    right_white, right_red, right_blue, right_yellow

    => {"head": {"decision": <decision>, "cards": <cards>},
        "left": {"decision": <decision>, "cards": <cards>},
        "right": {"decision": <decision>, "cards": <cards>}}
    """
    return {
        "left": drl_lights_to_decision_cards(left_white,
                                             left_red,
                                             left_blue,
                                             left_yellow),
        "head": drl_lights_to_decision_cards(head_white,
                                             head_red,
                                             head_blue,
                                             head_yellow),
        "right": drl_lights_to_decision_cards(right_white,
                                              right_red,
                                              right_blue,
                                              right_yellow)
    }


def liftingcast_decisions_to_result(liftingcast_decision_cards_dict):
    """Takes a map of referee to decision and cards and returns a result for the
    lift.

    {"head": {"decision": <decision>, "cards": <cards>},
     "left": {"decision": <decision>, "cards": <cards>},
     "right": {"decision": <decision>, "cards": <cards>}}

    => "good" | "bad"
    """
    num_good_decisions = len([dc["decision"] for dc in liftingcast_decision_cards_dict.values() if dc["decision"] == "good"])

    if num_good_decisions < 2:
        return "bad"
    else:
        return "good"

def are_valid_light_and_cards(white, red, blue, yellow):
    return (not (white and (red or blue or yellow)) and
            (white or red or blue or yellow))

def empty_decisions():
    return {
        "left": {
            "decision": None,
            "cards": {
                "red": None,
                "blue": None,
                "yellow": None
            }
        },
        "head": {
            "decision": None,
            "cards": {
                "red": None,
                "blue": None,
                "yellow": None
            }
        },
        "right": {
            "decision": None,
            "cards": {
                "red": None,
                "blue": None,
                "yellow": None
            }
        }
    }

# MAKE SURE decisions IS INITIALIZED IN THE CODE BEFORE ANY FUNCTIONS THAT
# USE IT ARE CALLED.
# decisions holds the decision data for an attempt:
# * To be written into the ref documents
# * After a delay to be written into the attempt document
decisions = empty_decisions()


def get_referee_docs():
    return {"left": g_db.fetch_doc_from_db(liftingcast_db.database_url,
                                           "rleft-{}".format(PLATFORM_ID)),
            "head": g_db.fetch_doc_from_db(liftingcast_db.database_url,
                                           "rhead-{}".format(PLATFORM_ID)),
            "right": g_db.fetch_doc_from_db(liftingcast_db.database_url,
                                            "rright-{}".format(PLATFORM_ID))}

def common_change_data(doc):
    return {"rev": doc["_rev"], "timeStamp": timestamp()}

def liftingcast_attribute_to_changes_attribute(attribute_name, attribute_value, doc):
    common = common_change_data(doc)
    common.update({
        "attribute": attribute_name,
        "value": attribute_value
    })
    return common

def truncate_changes(changes_list):
    return changes_list[:100]

def set_decisions(left_white,
                  left_red,
                  left_blue,
                  left_yellow,
                  head_white,
                  head_red,
                  head_blue,
                  head_yellow,
                  right_white,
                  right_red,
                  right_blue,
                  right_yellow):
    print "left white: {}".format(left_white)
    print "left red: {}".format(left_red)
    print "left blue: {}".format(left_blue)
    print "left yellow: {}".format(left_yellow)
    print "head white: {}".format(head_white)
    print "head red: {}".format(head_red)
    print "head blue: {}".format(head_blue)
    print "head yellow: {}".format(head_yellow)
    print "right white: {}".format(right_white)
    print "right red: {}".format(right_red)
    print "right blue: {}".format(right_blue)
    print "right yellow: {}".format(right_yellow)
    assert are_valid_light_and_cards(left_white, left_red, left_blue, left_yellow)
    assert are_valid_light_and_cards(head_white, head_red, head_blue, head_yellow)
    assert are_valid_light_and_cards(right_white, right_red, right_blue, right_yellow)

    global decisions
    decisions = drl_decisions_to_liftingcast_decisions(left_white,
                                                       left_red,
                                                       left_blue,
                                                       left_yellow,
                                                       head_white,
                                                       head_red,
                                                       head_blue,
                                                       head_yellow,
                                                       right_white,
                                                       right_red,
                                                       right_blue,
                                                       right_yellow)

def update_decisions_in_liftingcast():
    for position, referee in get_referee_docs().iteritems():
        d = decisions[position]
        cards = d["cards"]
        decision = d["decision"]

        referee["cards"] = cards
        referee["decision"] = decision
        changes = [
            liftingcast_attribute_to_changes_attribute("decision", decision, referee),
            liftingcast_attribute_to_changes_attribute("cards", cards, referee)
        ] + referee["changes"]
        referee["changes"] = truncate_changes(changes)
        g_db.put_doc_to_db(liftingcast_db.database_url, referee)

def set_decisions_and_update_in_liftingcast(left_white,
                                            left_red,
                                            left_blue,
                                            left_yellow,
                                            head_white,
                                            head_red,
                                            head_blue,
                                            head_yellow,
                                            right_white,
                                            right_red,
                                            right_blue,
                                            right_yellow):
    set_decisions(left_white,
                  left_red,
                  left_blue,
                  left_yellow,
                  head_white,
                  head_red,
                  head_blue,
                  head_yellow,
                  right_white,
                  right_red,
                  right_blue,
                  right_yellow)
    update_decisions_in_liftingcast()

def record_decisions_in_liftingcast():
    platform = g_db.fetch_doc_from_db(liftingcast_db.database_url,
                                      PLATFORM_ID)
    attempt = g_db.fetch_doc_from_db(liftingcast_db.database_url,
                                     platform["currentAttemptId"])

    result = liftingcast_decisions_to_result(decisions)

    attempt["decisions"] = decisions
    attempt["result"] = result
    changes = [
        liftingcast_attribute_to_changes_attribute("result", result, attempt),
        liftingcast_attribute_to_changes_attribute("decisions", decisions, attempt)
    ] + attempt["changes"]
    attempt["changes"] = truncate_changes(changes)
    try:
        g_db.put_doc_to_db(liftingcast_db.database_url, attempt)
    except urllib2.HTTPError as err:
        if err.code == 409:
            pass
        else:
            print "HTTP error while trying to write to liftingcast database. Try restarting DRL and make sure liftingcast has all data it should -- enter it manually from the scorekeeper's station as necessary."
            sys.exit(1)

    global decisions
    decisions = empty_decisions()
    update_decisions_in_liftingcast()

def set_liftingcast_clock(drl_clock_value_in_milliseconds):
    platform = g_db.fetch_doc_from_db(liftingcast_db.database_url,
                                      PLATFORM_ID)
    platform["clockState"] = "initial"
    platform["clockTimerLength"] = drl_clock_value_in_milliseconds
    g_db.put_doc_to_db(liftingcast_db.database_url, platform)

def start_liftingcast_clock():
    platform = g_db.fetch_doc_from_db(liftingcast_db.database_url,
                                      PLATFORM_ID)
    platform = liftingcast_db[PLATFORM_ID]
    platform["clockState"] = "started"
    g_db.put_doc_to_db(liftingcast_db.database_url, platform)

def pause_liftingcast_clock(drl_clock_value_in_milliseconds):
    """liftingcast doesn't have the ability to pause the clock so we simulate
    it by reseting the liftingcast clock to the current time on the DRL clock.
    """
    set_liftingcast_clock(drl_clock_value_in_milliseconds)
