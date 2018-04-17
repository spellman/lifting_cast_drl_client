# THIS IS *NOT* A SCRIPT TO BE RUN. This is a collection of functions to be used
# by drl or copied into drl.

# If the functions are copied, then be sure to add the imports to any files in
# which the modules are used.

import traceback
import datetime

try:
    from cloudant.client import CouchDB
except:
    print traceback.format_exc()
    print "Missing depedencies. Connect to the internet and install them by running"
    print "    sudo pip install -r requirements.txt"
    print "Then run this script again."







def timestamp():
    return datetime.datetime.now().replace(microsecond=0).isoformat()



# TODO: Platform ID and display-data file are shared between the two scripts so
# they should read in from a single file.
PLATFORM_ID = "pjspmhobe9kh"

# Set up meet ID and password for CouchDB database.

# TODO: There should be a function from the day the script is run to the meet ID and password for the meet (i.e., the database) for that day.
MEET_ID = "myvrzp8l3bty"
PASSWORD = "xm4sj4ms"




# Set up liftingcast client and database

liftingcast_client = CouchDB(MEET_ID,
                             PASSWORD,
                             url="http://couchdb.liftingcast.com",
                             connect=True,
                             auto_renew=True)
liftingcast_db = liftingcast_client[MEET_ID]







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
    return {"left": liftingcast_db["rleft-{}".format(PLATFORM_ID)],
            "head": liftingcast_db["rhead-{}".format(PLATFORM_ID)],
            "right": liftingcast_db["rright-{}".format(PLATFORM_ID)]}

def common_change_data(doc):
    return {"rev": doc["_rev"],
            "timeStamp": datetime.datetime.now().replace(microsecond=0).isoformat()}

def liftingcast_attribute_to_changes_attribute(attribute_name, attribute_value, doc):
    return common_change_data(doc).update({
        "attribute": attribute_name,
        "value": attribute_value
    })


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
    assert are_valid_light_and_cards(left_white, left_red, left_blue, left_yellow)
    assert are_valid_light_and_cards(head_white, head_red, head_blue, head_yellow)
    assert are_valid_light_and_cards(right_white, right_red, right_blue, right_yellow)

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
    for position, referee in get_referee_docs():
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
        referee.save()

def record_decisions_and_advance_lifter_in_liftingcast(next_attempt_id,
                                                       drl_clock_value_in_milliseconds):
    platform = liftingcast_db[PLATFORM_ID]
    attempt = liftingcast_db[platform["currentAttemptId"]]

    result = liftingcast_decisions_to_result(decisions)

    attempt["decisions"] = decisions
    attempt["result"] = result
    changes = [
        liftingcast_attribute_to_changes_attribute("result", result, attempt),
        liftingcast_attribute_to_changes_attribute("decisions", decisions, attempt)
    ] + attempt["changes"]
    attempt["changes"] = truncate_changes(changes)
    attempt.save()

    decisions = empty_decisions()
    update_decisions_in_liftingcast()

    platform["currentAttemptId"] = next_attempt_id
    platform["clockState"] = "initial"
    platform["clockTimerLength"] = drl_clock_value_in_milliseconds
    platform.save()

def set_liftingcast_clock(drl_clock_value_in_milliseconds):
    platform = liftingcast_db[PLATFORM_ID]
    platform["clockState"] = "initial"
    platform["clockTimerLength"] = drl_clock_value_in_milliseconds
    platform.save()

def start_liftingcast_clock():
    platform = liftingcast_db[PLATFORM_ID]
    platform["clockState"] = "started"
    platform.save()

def pause_liftingcast_clock(drl_clock_value_in_milliseconds):
    """liftingcast doesn't have the ability to pause the clock so we simulate
    it by reseting the liftingcast clock to the current time on the DRL clock.
    """
    set_liftingcast_clock(drl_clock_value_in_milliseconds)




    # We need

    # On each ref doc, for that ref's cards
    # "cards": null,                             SET CARDS
    # "decision": null,                          SET DECISION
    # "changes": [                               PREPEND DECISION AND CARDS ONTO CHANGES
    #   {
    #     "rev": "2-fb538d08290a40719ca659a5cdc8e4c2",
    #     "attribute": "decision",
    #     "value": "good",
    #     "timeStamp": "2018-03-20T17:38:22.575Z"
    #   },
    #   {
    #     "rev": "2-fb538d08290a40719ca659a5cdc8e4c2",
    #     "attribute": "cards",
    #     "value": {
    #       "red": false,
    #       "blue": false,
    #       "yellow": false
    #     },
    #     "timeStamp": "2018-03-20T17:38:22.576Z"
    #   }
    # ]

    # On the attempt doc
    # "decisions": {                             SET DECISIONS
    #   "left": {
    #     "decision": "good",
    #     "cards": {
    #       "red": false,
    #       "blue": false,
    #       "yellow": false
    #     }
    #   },
    #   "head": {
    #     "decision": "good",
    #     "cards": {
    #       "red": false,
    #       "blue": false,
    #       "yellow": false
    #     }
    #   },
    #   "right": {
    #     "decision": "bad",
    #     "cards": {
    #       "red": false,
    #       "blue": true,
    #       "yellow": false
    #     }
    #   }
    # },
    # "result": "good",                          SET RESULT
    # "changes": [                               PREPEND DECISIONS AND RESULT ONTO CHANGES
    #   {
    #     "rev": "5-aa203e8946ec4106af25fbae0009de56",
    #     "attribute": "result",
    #     "value": "good",
    #     "timeStamp": "2018-03-23T18:29:46.103Z"
    #   },
    #   {
    #     "rev": "5-aa203e8946ec4106af25fbae0009de56",
    #     "attribute": "decisions",
    #     "value": {
    #       "left": {
    #         "decision": "good",
    #         "cards": {
    #           "red": false,
    #           "blue": false,
    #           "yellow": false
    #         }
    #       },
    #       "head": {
    #         "decision": "good",
    #         "cards": {
    #           "red": false,
    #           "blue": false,
    #           "yellow": false
    #         }
    #       },
    #       "right": {
    #         "decision": "bad",
    #         "cards": {
    #           "red": false,
    #           "blue": true,
    #           "yellow": false
    #         }
    #       }
    #     },
    #     "timeStamp": "2018-03-23T18:29:46.103Z"
    #   }
    # ]


    # Clock
    # start, pause, reset(duration in minutes)
    # On the platform doc
    #   "clockState": "initial",                 SET CLOCKSTATE
    #   "clockTimerLength": 60000                SET CLOCKTIMERLENGTH
    # * We need to be able to set the timer for x minutes (like 5 minutes for a
    #   break or 1/2/3 minutes for a redo)
    # * liftingcast.com does not have a pause. Can I simulate one by overwriting
    #   the start time?
    #     => YEP!
    # * Can I start the liftingcast time at 1 minute minus the delay (3 seconds)?
    #     => YEP!



    # drl_decision_to_liftingcast_decisions: 12 bools => {"head": {"decision": <decision>, "cards": <cards>},
    #                                                     "left": {"decision": <decision>, "cards": <cards>},
    #                                                     "right": {"decision": <decision>, "cards": <cards>}}
    # liftingcast_decisions_to_result: {"head": {"decision": <decision>, "cards": <cards>},
    #                                   "left": {"decision": <decision>, "cards": <cards>},
    #                                   "right": {"decision": <decision>, "cards": <cards>}} => <result>

    # input_ref_decisions: update referee docs with respective decisions and cards - this will show the lights and cards
    #
    # record_decisions_and_advance_lifter:
    #     * update attempt doc with decisions and result
    #     * clear referee docs respective decisions and cards - this will hide the lights and cards
    #     * update the platform doc with:
    #         * the next attempt ID as currentAttemptId
    #         * "initial" as clockState
    #         * DRL clock value as clockTimerLength
    #
    # set_clock: update platform doc with "initial" as clockState and DRL clock value as clockTimerLength
    #
    # start_clock: update platform doc with "started" as clockState
    #
    # pause_clock: update platform doc with "initial" as clockState and DRL clock value as clockTimerLength
