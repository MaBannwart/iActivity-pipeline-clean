from os import listdir


class PatientDetails:
    def __init__(self, pid, fid, date_stamp):
        self.pid = pid
        self.fid = fid
        self.date_stamp = date_stamp


def get_details(filename):
    backslash_index = find_all(filename, '/')
    assert (len(backslash_index) != 0), 'There was a mistake while looking for / in the filename'
    underline_index = find_all(filename, '_')
    assert (len(underline_index) != 0), 'There was a mistake while looking for _ in the filename'
    date = (filename[(underline_index[-2] + 1):(underline_index[-2] + 9)]
            + filename[(underline_index[-1] + 1):(underline_index[-1] + 5)])
    pid = filename[(backslash_index[-5] + 5):(backslash_index[-5] + 12)]
    fid = filename[(backslash_index[-4] + 5):(backslash_index[-4] + 12)]
    return pid, fid, date


def find_csv_filenames(
        path_to_dir: str,
        suffix=".csv"
):
    """Find all files in a directory with a specific type

    Parameters
    ----------
    path_to_dir:
        Path to the directory
    suffix:
        suffix of the data type that is wanted

    Returns
    -------
    file_list:
        list of all file names with the wanted suffix
    """

    filenames = listdir(path_to_dir)
    filelist = [filename for filename in filenames if filename.endswith(suffix) or filename.endswith(suffix.upper())]
    concat_func = lambda x, y: x + "" + str(y)
    file_list = list(map(concat_func, [path_to_dir + '/']*len(filelist), filelist))
    return file_list


def find_all(a_str, sub):
    indices = [i for i, c in enumerate(a_str) if c == sub]
    return indices
    #start = 0
    #while True:
    #    start = a_str.find(sub, start)
    #    if start == -1: return
    #    yield start
    #    start += len(sub)
