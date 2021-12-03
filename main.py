"""pycluon microserice for a ARS-300 radar"""
import time
import logging
import warnings
from pathlib import Path

from environs import Env
from streamz import Stream
from pycluon import Envelope, OD4Session
from pycluon.importer import import_odvd

# Reading config from environment variables
env = Env()

CLUON_CID = env.int("CLUON_CID", 111)
CLUON_SENDER_ID = env.int("CLUON_SENDER_ID", 1)
LOG_LEVEL = env.log_level("LOG_LEVEL", logging.WARNING)

# Setup logger
logging.basicConfig(level=LOG_LEVEL)
logging.captureWarnings(True)
warnings.filterwarnings("once")
LOGGER = logging.getLogger("cluon-ARS300")

## Import and generate code for the opendlv standard message set
THIS_DIR = Path(__file__).parent
opendlv = import_odvd(THIS_DIR / "opendlv.standard.message-set" / "opendlv.odvd")


session = OD4Session(CLUON_CID)


def can_message_handler_1(_):
    """Handle a single can message"""
    sample_time = time.time()  # Or if you get something from the CAN bus

    # Process can_message according to you needs

    # Insert into a opendlv message (just an example)
    msg_id = 1134  # Acording to odvd-file
    msg = opendlv.opendlv_logic_perception_ObjectDistance()
    msg.objectId = 42
    msg.distance = 78.5

    return [(msg_id, sample_time, msg)]  # Add tuples here for sending multiple messages


def cluon_send(message_requests):
    """Send opendlv messages according to requests"""
    for request in message_requests:
        msg_id, sample_time, msg = request

        envelope = Envelope()
        envelope.sent = envelope.sampled = sample_time
        envelope.serialized_data = msg.SerializeToString()
        envelope.data_type = msg_id
        envelope.sender_stamp = CLUON_SENDER_ID

        session.send(envelope)


if __name__ == "__main__":

    # Building processing pipeline
    source = Stream()
    source.map(can_message_handler_1).sink(cluon_send)

    # Setup canbus listener here

    # Inject new can messages in pipeline like:
    # source.emit(message)
