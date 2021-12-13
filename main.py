"""pycluon microserice for a ARS-300 radar"""
import time
import logging
import warnings
from pathlib import Path
import json

from environs import Env
from streamz import Stream
from pycluon import Envelope, OD4Session
from pycluon.importer import import_odvd

import cantools
import can
from canlib import canlib


# Reading config from environment variables
env = Env()

CLUON_CID = env.int("CLUON_CID", 111)
CLUON_SENDER_ID = env.int("CLUON_SENDER_ID", 1)
LOG_LEVEL = env.log_level("LOG_LEVEL", logging.WARNING)
CANBUS_CHANNEL = env.int("CANBUS_CHANNEL",0)
CANBUSTYPE = env("CANBUSTYPE",'kvaser')

# Setup logger
logging.basicConfig(level=LOG_LEVEL)
logging.captureWarnings(True)
warnings.filterwarnings("once")
LOGGER = logging.getLogger("cluon-ARS300")

## Import and generate code for the opendlv standard message set
THIS_DIR = Path(__file__).parent
opendlv = import_odvd(THIS_DIR / "opendlv.standard.message-set" / "opendlv.odvd") #todo import memo file instead


session = OD4Session(CLUON_CID)


def can_message_handler_1(frame):
    """Handle a single can message"""
    sample_time = frame.get('timestamp')
    # Process can_message according to you needs
    payload = json.dumps(frame)
    
    # Insert into a opendlv message (just an example)
    msg_id = 10000  # Acording to odvd-file
    msg = memo.memo_raw_Raw()
    msg.data = payload
    
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
    
    ## open can bus. Make sure it is the right channel
    bus = can.interface.Bus(bustype=CANBUSTYPE, channel=CANBUS_CHANNEL, bitrate=500000)
    ## load databases
    db = cantools.database.Database()
    db.add_dbc_file(THIS_DIR+'can_database_ch0.dbc') # does this work?
    # db.add_dbc_file(os.getcwd()+'\Configs for ARS 308-2C and 308-21\\can_database_ch0.dbc')
   
    CAN1_Target_Status = db.get_message_by_name('CAN1_Target_Status')
    CAN1_Target_1 = db.get_message_by_name('CAN1_Target_1')
    CAN1_Target_2 = db.get_message_by_name('CAN1_Target_2')
    stateOutput = db.get_message_by_name('RadarState')
    
    maxTargets = 96
    maxNear = 32
    maxFar = 64
    NNear = 0
    NFar = 0
    timeStamp = 0
    frame = list()
    
    while True:
        try:
            message = bus.recv()
            if message.arbitration_id == CAN1_Target_Status.frame_id: # 0x600:
                # send all targets in previous frame
                source.emit({'timestamp': timeStamp, 'targets': frame})
                targetStatus = db.decode_message(message.arbitration_id, message.data)
                timeStamp = message.timestamp #-timeStamp0 # should we pass on epoch time or something else?
                NNear = targetStatus.get('NoOfTargetsNear')
                NFar = targetStatus.get('NoOfTargetsFar')
                frame = list() # empty frame
            if message.arbitration_id == CAN1_Target_1.frame_id:
                target1 = db.decode_message(message.arbitration_id, message.data)
                message = bus.recv()
                if message.arbitration_id == CAN1_Target_2.frame_id:
                    target2 = db.decode_message(message.arbitration_id, message.data)
                    target = {**target1,**target2} # use timestamp of first message in frame for all.
                    if not target.get('NoOfTarget_1') == target.get('NoOfTarget_2'):
                        print('warning! message mismatch')
                    if target.get('NoOfTarget_1')<=NNear or maxNear<target.get('NoOfTarget_1')<=maxNear+NFar:
                        frame.append(target)
                        
    # Inject new can messages in pipeline like:
    # source.emit(message)

