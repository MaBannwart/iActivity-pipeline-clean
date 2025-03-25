
"""----------------------Merging------------------------------"""
ROOT = "C:/Users/bannw/Documents/iActivity/iActivity_Pipeline/data/Input" #"/mnt/sdb/data/iactivity_raw_data" #
ARCHIVE = "C:/Users/bannw/Documents/iActivity/iActivity_Pipeline/data/Archive" #"/mnt/sdb/data/iactivity_raw_data/archive" #
OUTPUT = "C:/Users/bannw/Documents/iActivity/iActivity_Pipeline/data/Output" #"/mnt/sdb/data/iactivity_output"
#OUTPUT_FOLDER_HL7 = "C:/Users/bannw/Documents/Axivity/pipeline-test/hl7" #r"/home/lli_admin/data/hl7_export"
#HOME = "C:/Users/bannw/Documents/Axivity/pipeline-test/data/" #r"/home/lli_admin/data/"
ERROR = "C:/Users/bannw/Documents/iActivity/iActivity_Pipeline/data/Error" #"/mnt/sdb/data/iactivity_raw_data/error" #

SENSOR_LOCATION = {
    'WR': 'wrist_r',
    'WL': 'wrist_l',
    'AR': 'ankle_r',
    'AL': 'ankle_l',
    'Chest': 'chest'
}

'''PacketCounter and SmapleTime have to stay the same, otherwise changes need to be done in MergingSensors.py
If you change the parameters, changes need to be done in MergingSensors->delete_false_rows'''
PARAMETER_IMU = ['PacketCounter', 'SampleTimeFine', 'Acc_X', 'Acc_Y', 'Acc_Z', 'Gyr_X', 'Gyr_Y', 'Gyr_Z']

FREQ_IMU = 50
FREQ_HR = 1

'''----------------------ActivityCounts------------------------------'''
EPOCH_LENGTH = 1

PRED_TO_STRING = {
    'activity':{
        0:'lying',
        1:'sit',
        2:'stand',
        3:'walk',
        4:'stairs',
    },
    'gait':{
        0:'gait',
        1:'no-gait',
    },
    'functional':{
        0: 'non-functional',
        1: 'functional',
    }
}

VALID_SENSOR_POS_ACTIVITY = [
        'wrists',
        'ankles',
        'all',
        'no_chest',
        'left',
        'right',
    ]


