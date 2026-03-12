from pathlib import Path

"""-----------------------Paths-------------------------------"""
# Get the absolute path to the main directory (parent folder of the this script's parent folder)
BASE_DIR = Path(__file__).resolve().parent.parent

# Define subfolders relative to the base directory
INPUT_DIR = BASE_DIR / "data/Input"
ARCHIVE_DIR = BASE_DIR / "data/Archive"
OUTPUT_DIR = BASE_DIR / "data/Output"
LOGS_DIR = BASE_DIR / "Logs"

# Create folders if they do not exist
for folder in [INPUT_DIR, ARCHIVE_DIR, OUTPUT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

"""----------------------Merging------------------------------"""
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


