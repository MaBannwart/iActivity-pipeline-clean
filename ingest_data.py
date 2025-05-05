import shutil
import os
import pandas as pd
import requests
import utils.constants as constants
from pathlib import Path
import re
import _version as _ver
from datetime import timezone, timedelta
from zoneinfo import ZoneInfo


def main():
    # Debug variable
    is_upload_true = True

    # Path to output files
    output_path = Path(constants.OUTPUT)
    archive_path = Path(constants.ARCHIVE).joinpath('output')

    # Check if archive exists
    if not archive_path.is_dir():
        archive_path.mkdir()  # create directory if it does not exist

    # Find output files
    for csv_file_path in output_path.rglob('*.csv'):

        # Read the CSV file
        df = pd.read_csv(csv_file_path.as_posix())
        print('File path: ' + csv_file_path.as_posix())

        # Get the fid from the filename
        fid = csv_file_path.stem.split("_")[0]
        print('FID: ' + fid)

        # Check if fid is valid (7 digits, starting with a 2)
        if not (re.match(r'^\d{7}$', fid)) and fid[0] == '2':
            raise Exception("FID not valid")

        df.dropna(axis=1, how='all', inplace=True)
        df = df.where(pd.notnull(df), None)
        df = df[:-1]

        # Find the index of rows in the last 3 rows that contain NaN
        last_rows_with_nan = df.iloc[-3:].dropna().index
        # Drop the rows in the last 3 rows that contain NaN
        df = df.drop(df.iloc[-3:].index.difference(last_rows_with_nan))

        # Clean
        if 'grouped' in df.columns:
            df = df.drop(columns='grouped')

        for column in df.columns:
            if df[column].isna().any():
                print(column)


        # Convert sensor time to correct UTC time zone
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], format="%Y-%m-%d %H:%M:%S") #convert from string to datetime
        # Use the first timestamp to determine the daylight saving time offset
        first_timestamp = df['Timestamp'].iloc[0]
        # Assign Europe/Zurich timezone temporarily
        first_ts_with_tz = first_timestamp.replace(tzinfo=ZoneInfo("Europe/Zurich"))
        # Get the offset from UTC in hours
        offset_hours = first_ts_with_tz.utcoffset().total_seconds() / 3600

        # Create a fixed offset timezone (since sensors do not use DST but continuously increase time with a fixed offset)
        fixed_offset = timezone(timedelta(hours=offset_hours))

        # Use the above fixed offset timezone to convert sensor time to UTC
        df.set_index('Timestamp', inplace=True) #set Timestamp column as index for the next operations
        df = df.tz_localize(tz=fixed_offset)  # Localize using fixed offset
        df = df.tz_convert(timezone.utc)  # Convert to UTC (server assumed time zone)
        df = df.tz_localize(None)  # Remove tz awareness (required since server requires string format)
        df.reset_index(inplace=True) #reset index to have a separate 'Timestamp' column again
        df['Timestamp'] = df['Timestamp'].apply(lambda x: x.isoformat() + 'Z')  # Format time as ISO UTC strings


        json_data = {
            "fid": fid,
            "measurements": df.to_dict(orient='records')
        }

        log_data = {
                "fid": fid,
                "session_id": csv_file_path.stem.split("_")[1], #"test",
                "start_time": df['Timestamp'].iloc[0], #"2024-05-14T20:14:57.571Z",
                "stop_time": df['Timestamp'].iloc[-1], #"2024-05-14T20:14:57.571Z",
                "pipeline_version": _ver.__version__
        }

        if is_upload_true:
            # Data endpoint URL
            data_url = 'http://172.20.11.10/med-api/iactivity/load-json-data/' #'http://192.168.19.21/med-api/iactivity/load-json-data/'
            # Log endpoint URL
            log_url = 'http://172.20.11.10/med-api/iactivity/load-log-data/'

            # Send the JSON data
            data_response = requests.post(data_url, json=json_data)
            # Check the response
            if data_response.status_code == 200:
                print('Outcome data sent successfully')

                # Send LOG data
                log_response = requests.post(log_url, json=log_data)
                # Check the response
                if log_response.status_code == 200:
                    print('Log data sent successfully')
                    # Moved code outside to still move folders even in case of failure
                else:
                    print(
                        f'Failed to send log data. Status code: {log_response.status_code}, Response: {log_response.text}')

                # Move processed raw data to archive
                cp_parents(archive_path, output_path, csv_file_path)
            else:
                print(f'Failed to send outcome data. Status code: {data_response.status_code}, Response: {data_response.text}')
    delete_empty_dirs(output_path)


def cp_parents(target_dir, parent_dir, file_path):
    relative_path = (file_path.relative_to(parent_dir)).parent
    dest_dir = target_dir.joinpath(relative_path)
    print("Creating", dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    print("Copying %s to %s" % (file_path.as_posix(), dest_dir.as_posix()))
    shutil.move(file_path, dest_dir)


def delete_empty_dirs(path):
    for root, dirs, files in os.walk(path.as_posix(), topdown=False):
        for directory in dirs:
            dir_path = os.path.join(root, directory)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
                print(f"Deleted empty directory: {dir_path}")


if __name__ == '__main__':
    main()
