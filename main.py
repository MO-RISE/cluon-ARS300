"""pycluon microservice for a ARS-300 radar"""
import json
import logging
import warnings
from pathlib import Path
from typing import Callable, Dict
from datetime import datetime

from environs import Env
from streamz import Stream
from pycluon import Envelope, OD4Session
from pycluon.importer import import_odvd

import cantools
import can


# Reading config from environment variables
env = Env()

CLUON_CID = env.int("CLUON_CID", 111)
CLUON_SENDER_ID = env.int("CLUON_SENDER_ID", 1)
LOG_LEVEL = env.log_level("LOG_LEVEL", logging.WARNING)
CANBUS_CHANNEL = env.int("CANBUS_CHANNEL", 0)
CANBUSTYPE = env("CANBUSTYPE", "kvaser")

# Setup logger
logging.basicConfig(level=LOG_LEVEL)
logging.captureWarnings(True)
LOGGER = logging.getLogger("cluon-ARS300")

## Import and generate code for memo
THIS_DIR = Path(__file__).parent
memo = import_odvd(THIS_DIR / "memo" / "memo.odvd")

# OD4 session setup
session = OD4Session(CLUON_CID)

# Load can message database
db = cantools.database.Database()
db.add_dbc_file(THIS_DIR / "can_database_ch0.dbc")

# And fetch specifications
CAN1_Target_Status = db.get_message_by_name("CAN1_Target_Status")
CAN1_Target_1 = db.get_message_by_name("CAN1_Target_1")
CAN1_Target_2 = db.get_message_by_name("CAN1_Target_2")
stateOutput = db.get_message_by_name("RadarState")


def receive_from_canbus(bus: can.interface.Bus, injector: Callable):
    """Blocking function which receives from a can bus infinetly and
    injects into an injector callable"""
    # maxTargets = 96  ## Not used?
    max_near = 32
    # maxFar = 64   ## Not used?
    n_near = 0
    n_far = 0
    time_stamp = 0
    frame = []

    while True:
        try:
            # Receive from bus
            message = bus.recv()
            LOGGER.debug("CANBUS received: %s", message)

            # If this is a target status message
            if message.arbitration_id == CAN1_Target_Status.frame_id:  # 0x600:

                # Send all targets in previous frame (if any)
                if frame:
                    injector({"timestamp": time_stamp, "targets": frame})
                    frame.clear()  # Clear data from previous frame

                # Decode this message
                target_status = db.decode_message(message.arbitration_id, message.data)

                # Fetch timestamp for the whole frame
                time_stamp = message.timestamp

                # Fetch info about number of valid targets
                n_near = target_status.get("NoOfTargetsNear")
                n_far = target_status.get("NoOfTargetsFar")

            # If this is a target 1 message
            if message.arbitration_id == CAN1_Target_1.frame_id:
                # Decode
                target1 = db.decode_message(message.arbitration_id, message.data)

                # Try to fetch the subsequent target 2 message
                message = bus.recv()
                LOGGER.debug("CANBUS received: %s", message)
                if message.arbitration_id == CAN1_Target_2.frame_id:

                    # Decode
                    target2 = db.decode_message(message.arbitration_id, message.data)

                    # Merge the messages
                    target = {
                        **target1,
                        **target2,
                    }

                    # Check for mismatch (enough with a warning?)
                    if not target.get("NoOfTarget_1") == target.get("NoOfTarget_2"):
                        warnings.warn("Message mismatch!")

                    # Only append to frame if this is a valid target
                    if (target.get("NoOfTarget_1") <= n_near) or (
                        max_near < target.get("NoOfTarget_1") <= (max_near + n_far)
                    ):
                        frame.append(target)

        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Something went wrong in the reception from the CAN bus!")


def frame_handler(frame: Dict):
    """Handle a single frame"""
    LOGGER.debug("Frame handler received frame to handle: %s", frame)
    sample_time = datetime.fromtimestamp(frame.get("timestamp"))

    # Insert into a memo.raw.Brefv message
    msg_id = 10004  # Acording to odvd-file
    msg = memo.memo_raw_Brefv()
    msg.data = json.dumps(frame)

    return [(msg_id, sample_time, msg)]


def cluon_send(message_requests):
    """Send opendlv messages according to requests"""
    for request in message_requests:
        msg_id, sample_time, msg = request

        envelope = Envelope()
        envelope.sampled_at = sample_time
        envelope.sent_at = datetime.now()
        envelope.serialized_data = msg.SerializeToString()
        envelope.data_type = msg_id
        envelope.sender_stamp = CLUON_SENDER_ID

        session.send(envelope)


if __name__ == "__main__":

    # Building processing pipeline
    source = Stream()
    source.map(frame_handler).sink(cluon_send)

    # Open can bus. Make sure it is the right channel!
    can_bus = can.interface.Bus(
        bustype=CANBUSTYPE, channel=CANBUS_CHANNEL, bitrate=500000
    )

    # Start processing messages
    receive_from_canbus(can_bus, source.emit)
