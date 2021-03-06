import os
import glob
import sys
import cv2
import pandas as pd
from datetime import datetime


def get_video_folders_to_crop(video_root_folder):
    """
    find all the lowest level directories within video_root_folder, which are presumably the lowest level folders that
    contain the videos to be cropped

    :param video_root_folder: root directory from which to extract the list of folders that contain videos to crop
    :return: crop_dirs - list of lowest level directories within video_root_folder
    """

    crop_dirs = []

    # assume that any directory that does not have a subdirectory contains videos to crop
    for root, dirs, files in os.walk(video_root_folder):
        if not dirs:
            crop_dirs.append(root)

    return crop_dirs


def create_cropped_video_destination_list(cropped_vids_parent, video_folder_list, view_list):
    """
    create subdirectory trees in which to store the cropped videos. Directory structure is ratID-->[direct_view or
        mirror_views]-->ratID-->[sessionID_direct/leftmirror/rightmirror]
    :param cropped_vids_parent: parent directory in which to create directory tree
    :param video_folder_list: list of lowest level directories containing the original videos
    :return: cropped_video_directories
    """

    cropped_video_directories = [[], [], []]
    for crop_dir in video_folder_list:
        _, session_dir = os.path.split(crop_dir)
        ratID, session_name = parse_session_dir_name(session_dir)

        # create direct view directory for this raw video directory
        cropped_vid_dir = session_dir + '_direct'
        direct_view_directory = os.path.join(cropped_vids_parent, ratID, session_dir, cropped_vid_dir)

        # create left mirror view directory for this raw video directory
        cropped_vid_dir = session_dir + '_leftmirror'
        left_view_directory = os.path.join(cropped_vids_parent, ratID, session_dir, cropped_vid_dir)

        # create right mirror view directory for this raw video directory
        cropped_vid_dir = session_dir + '_rightmirror'
        right_view_directory = os.path.join(cropped_vids_parent, ratID, session_dir, cropped_vid_dir)

        cropped_video_directories[0].append(direct_view_directory)
        cropped_video_directories[1].append(left_view_directory)
        cropped_video_directories[2].append(right_view_directory)

    return cropped_video_directories


def parse_session_dir_name(session_dir):
    """

    :param session_dir - session directory name assumed to be of the form RXXXX_yyyymmddz, where XXXX is the rat number,
        yyyymmdd is the date, and z is a letter identifying distinct sessions on the same day (i.e., "a", "b", etc.)
    :return:
    """

    dir_name_parts = session_dir.split('_')
    ratID = dir_name_parts[0]
    session_name = dir_name_parts[1]

    return ratID, session_name


def find_folders_to_analyze(cropped_videos_parent, view_list=None):
    """
    get the full list of directories containing cropped videos in the videos_to_analyze folder
    :param cropped_videos_parent: parent directory with subfolders direct_view and mirror_views, which have subfolders
        RXXXX-->RXXXXyyyymmddz[direct/leftmirror/rightmirror] (assuming default view list)
    :param view_list:
    :return: folders_to_analyze: dictionary containing a key for each member of view_list. Each key holds a list of
        folders to run through deeplabcut
    """

    if view_list is None:
        view_list = ('direct', 'leftmirror', 'rightmirror')

    folders_to_analyze = dict(zip(view_list, ([] for _ in view_list)))

    rat_folder_list = glob.glob(os.path.join(cropped_videos_parent, 'R*'))
    for rat_folder in rat_folder_list:
        if os.path.isdir(rat_folder):
            # assume the rat_folder directory name is the same as ratID (i.e., form of RXXXX)
            _, ratID = os.path.split(rat_folder)
            session_name = ratID + '_*'
            session_dir_list = glob.glob(rat_folder + '/' + session_name)
            # make sure we only include directories (just in case there are some stray files with the right names)
            session_dir_list = [session_dir for session_dir in session_dir_list if os.path.isdir(session_dir)]
            for session_dir in session_dir_list:
                _, cur_session = os.path.split(session_dir)
                for view in view_list:
                    view_folder = os.path.join(session_dir, cur_session + '_' + view)
                    if os.path.isdir(view_folder):
                        folders_to_analyze[view].extend([view_folder])

    return folders_to_analyze

    # for view in view_list:
    #
    #     if 'direct' in view:
    #         view_folder = os.path.join(cropped_videos_parent, 'direct_view')
    #     elif 'mirror' in view:
    #         view_folder = os.path.join(cropped_videos_parent, 'mirror_views')
    #     else:
    #         print(view + ' does not contain the keyword "direct" or "mirror"')
    #         continue
    #
    #     rat_folder_list = glob.glob(os.path.join(view_folder + '/R*'))
    #
    #     for rat_folder in rat_folder_list:
    #         # make sure it's actually a folder
    #         if os.path.isdir(rat_folder):
    #             # assume the rat_folder directory name is the same as ratID (i.e., form of RXXXX)
    #             _, ratID = os.path.split(rat_folder)
    #             session_name = ratID + '_*_' + view
    #             session_dir_list = glob.glob(rat_folder + '/' + session_name)
    #
    #             # make sure we only include directories (just in case there are some stray files with the right names)
    #             session_dir_list = [session_dir for session_dir in session_dir_list if os.path.isdir(session_dir)]


def parse_cropped_video_name(cropped_video_name):
    """
    extract metadata information from the video name
    :param cropped_video_name: video name with expected format RXXXX_yyyymmdd_HH-MM-SS_ZZZ_[view]_l-r-t-b.avi
        where [view] is 'direct', 'leftmirror', or 'rightmirror', and l-r-t-b are left, right, top, and bottom of the
        cropping windows from the original video
    :return: cropped_vid_metadata: dictionary containing the following keys
        ratID - rat ID as a string RXXXX
        boxnum - box number the session was run in. useful for making sure we used the right calibration. If unknown,
            set to 99
        triggertime - datetime object with when the trigger event occurred (date and time)
        video_number - number of the video (ZZZ in the filename). This number is not necessarily unique within a session
            if it had to be restarted partway through
        video_type - video type (e.g., '.avi', '.mp4', etc)
        crop_window - 4-element list [left, right, top, bottom] in pixels
    """

    cropped_vid_metadata = {
        'ratID': '',
        'rat_num': 0,
        'boxnum': 99,
        'triggertime': datetime(1,1,1),
        'video_number': 0,
        'view': '',
        'video_type': '',
        'crop_window': [],
        'cropped_video_name': ''
    }
    _, vid_name = os.path.split(cropped_video_name)
    cropped_vid_metadata['cropped_video_name'] = vid_name
    vid_name, vid_type = os.path.splitext(vid_name)

    metadata_list = vid_name.split('_')

    cropped_vid_metadata['ratID'] = metadata_list[0]
    num_string = ''.join(filter(lambda i: i.isdigit(), cropped_vid_metadata['ratID']))
    cropped_vid_metadata['rat_num'] = int(num_string)

    # if box number is stored in file name, then extract it
    if 'box' in metadata_list[1]:
        cropped_vid_metadata['boxnum'] = int(metadata_list[1][3:])
        next_metadata_idx = 2
    else:
        next_metadata_idx = 1

    datetime_str = metadata_list[next_metadata_idx] + '_' + metadata_list[1+next_metadata_idx]
    cropped_vid_metadata['triggertime'] = datetime.strptime(datetime_str, '%Y%m%d_%H-%M-%S')

    cropped_vid_metadata['video_number'] = int(metadata_list[next_metadata_idx + 2])
    cropped_vid_metadata['video_type'] = vid_type
    cropped_vid_metadata['view'] = metadata_list[next_metadata_idx + 3]

    left, right, top, bottom = list(map(int, metadata_list[next_metadata_idx + 4].split('-')))
    cropped_vid_metadata['crop_window'].extend(left, right, top, bottom)

    return cropped_vid_metadata


def parse_video_name(video_name):
    """
    extract metadata information from the video name
    :param video_name: video name with expected format RXXXX_yyyymmdd_HH-MM-SS_ZZZ_[view]_l-r-t-b.avi
        where [view] is 'direct', 'leftmirror', or 'rightmirror', and l-r-t-b are left, right, top, and bottom of the
        cropping windows from the original video
    :return: video_metadata: dictionary containing the following keys
        ratID - rat ID as a string RXXXX
        boxnum - box number the session was run in. useful for making sure we used the right calibration. If unknown,
            set to 99
        triggertime - datetime object with when the trigger event occurred (date and time)
        video_number - number of the video (ZZZ in the filename). This number is not necessarily unique within a session
            if it had to be restarted partway through
        video_type - video type (e.g., '.avi', '.mp4', etc)
    """

    video_metadata = {
        'ratID': '',
        'rat_num': 0,
        'session_name': '',
        'boxnum': 99,
        'triggertime': datetime(1,1,1),
        'video_number': 0,
        'video_type': '',
        'video_name': '',
        'im_size': (1024, 2040)
    }

    if os.path.exists(video_name):
        video_object = cv2.VideoCapture(video_name)
        video_metadata['im_size'] = (int(video_object.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                   int(video_object.get(cv2.CAP_PROP_FRAME_WIDTH)))

    vid_path, vid_name = os.path.split(video_name)
    video_metadata['video_name'] = vid_name
    # the last folder in the tree should have the session name
    _, video_metadata['session_name'] = os.path.split(vid_path)
    vid_name, vid_type = os.path.splitext(vid_name)

    metadata_list = vid_name.split('_')

    video_metadata['ratID'] = metadata_list[0]
    num_string = ''.join(filter(lambda i: i.isdigit(), video_metadata['ratID']))
    video_metadata['rat_num'] = int(num_string)

    # if box number is stored in file name, then extract it
    if 'box' in metadata_list[1]:
        video_metadata['boxnum'] = int(metadata_list[1][3:])
        next_metadata_idx = 2
    else:
        next_metadata_idx = 1

    datetime_str = metadata_list[next_metadata_idx] + '_' + metadata_list[1+next_metadata_idx]
    video_metadata['triggertime'] = datetime.strptime(datetime_str, '%Y%m%d_%H-%M-%S')

    video_metadata['video_number'] = int(metadata_list[next_metadata_idx + 2])
    video_metadata['video_type'] = vid_type

    return video_metadata


def build_video_name(video_metadata, videos_parent):

    video_name = '{}_box{:02d}_{}_{:03d}.avi'.format(video_metadata['ratID'],
                                                  video_metadata['boxnum'],
                                                  video_metadata['triggertime'].strftime('%Y%m%d_%H-%M-%S'),
                                                  video_metadata['video_number'])
    video_name = os.path.join(videos_parent, 'videos_to_crop', video_metadata['ratID'], video_metadata['session_name'], video_name)
    return video_name


def parse_dlc_output_pickle_name(dlc_output_pickle_name):
    """
    extract metadata information from the pickle file name
    :param dlc_output_pickle_name: video name with expected format RXXXX_yyyymmdd_HH-MM-SS_ZZZ_[view]_l-r-t-b.avi
        where [view] is 'direct', 'leftmirror', or 'rightmirror', and l-r-t-b are left, right, top, and bottom of the
        cropping windows from the original video
    :return: cropped_vid_metadata: dictionary containing the following keys
        ratID - rat ID as a string RXXXX
        boxnum - box number the session was run in. useful for making sure we used the right calibration. If unknown,
            set to 99
        triggertime - datetime object with when the trigger event occurred (date and time)
        video_number - number of the video (ZZZ in the filename). This number is not necessarily unique within a session
            if it had to be restarted partway through
        video_type - video type (e.g., '.avi', '.mp4', etc)
        crop_window - 4-element list [left, right, top, bottom] in pixels
    """

    pickle_metadata = {
        'ratID': '',
        'rat_num': 0,
        'boxnum': 99,
        'triggertime': datetime(1,1,1),
        'video_number': 0,
        'view': '',
        'crop_window': [],
        'scorername': '',
        'pickle_name': ''
    }
    _, pickle_name = os.path.split(dlc_output_pickle_name)
    pickle_metadata['pickle_name'] = pickle_name
    pickle_name, vid_type = os.path.splitext(pickle_name)

    metadata_list = pickle_name.split('_')

    pickle_metadata['ratID'] = metadata_list[0]
    num_string = ''.join(filter(lambda i: i.isdigit(), pickle_metadata['ratID']))
    pickle_metadata['rat_num'] = int(num_string)

    # if box number is stored in file name, then extract it
    if 'box' in metadata_list[1]:
        pickle_metadata['boxnum'] = int(metadata_list[1][3:])
        next_metadata_idx = 2
    else:
        next_metadata_idx = 1

    datetime_str = metadata_list[next_metadata_idx] + '_' + metadata_list[1+next_metadata_idx]
    pickle_metadata['triggertime'] = datetime.strptime(datetime_str, '%Y%m%d_%H-%M-%S')

    pickle_metadata['video_number'] = int(metadata_list[next_metadata_idx + 2])
    pickle_metadata['view'] = metadata_list[next_metadata_idx + 3]

    # 'DLC' gets appended to the last cropping parameter in the filename by deeplabcut
    crop_window_strings = metadata_list[next_metadata_idx + 4].split('-')
    left, right, top = list(map(int, crop_window_strings[:-1]))

    # find where 'DLC' starts in the last crop_window_string
    dlc_location = crop_window_strings[-1].find('DLC')
    bottom = int(crop_window_strings[-1][:dlc_location])

    pickle_metadata['crop_window'].extend((left, right, top, bottom))

    #todo: write the scorername into the pickle metadata dictionary. It's also in the metadata pickle file
    pickle_metadata['scorername']

    return pickle_metadata


def create_marked_vids_folder(cropped_vid_folder, cropped_videos_parent, marked_videos_parent):
    """
    :param cropped_vid_folder:
    :param cropped_videos_parent:
    :param marked_videos_parent:
    :return:
    """

    # find the string 'cropped_videos' in cropped_vid_folder; everything after that is the relative path to create the marked_vids_folder
    cropped_vid_relpath = os.path.relpath(cropped_vid_folder, start=cropped_videos_parent)
    marked_vid_relpath = cropped_vid_relpath + '_marked'
    marked_vids_folder = os.path.join(marked_videos_parent, marked_vid_relpath)

    if not os.path.isdir(marked_vids_folder):
        os.makedirs(marked_vids_folder)

    return marked_vids_folder


def create_calibration_file_tree(calibration_parent, vid_metadata):
    """

    :param calibration_parent:
    :param vid_metadata: dictionary containing the following keys
        ratID - rat ID as a string RXXXX
        boxnum - box number the session was run in. useful for making sure we used the right calibration. If unknown,
            set to 99
        triggertime - datetime object with when the trigger event occurred (date and time)
        video_number - number of the video (ZZZ in the filename). This number is not necessarily unique within a session
            if it had to be restarted partway through
        video_type - video type (e.g., '.avi', '.mp4', etc)
        crop_window - 4-element list [left, right, top, bottom] in pixels
    :return:
    """

    year_folder = 'calibration_files_' + datetime.strftime(vid_metadata['triggertime'], '%Y')
    month_folder = 'calibration_files_' + datetime.strftime(vid_metadata['triggertime'], '%Y%m')
    day_folder = 'calibration_files_' + datetime.strftime(vid_metadata['triggertime'], '%Y%m%d')
    box_folder = day_folder + '_box{:2d}'.format(vid_metadata['boxnum'])

    calibration_file_tree = os.path.join(calibration_parent, year_folder, month_folder, day_folder, box_folder)

    return calibration_file_tree


def find_dlc_output_pickles(video_metadata, marked_videos_parent, view_list=None):
    """

    :param video_metadata:
    :param marked_videos_parent:
    :param view_list:
    :return:
    """
    if view_list is None:
        view_list = ('direct', 'leftmirror', 'rightmirror')

    session_name = video_metadata['session_name']
    rat_pickle_folder = os.path.join(marked_videos_parent, video_metadata['ratID'])
    session_pickle_folder = os.path.join(rat_pickle_folder, session_name)

    dlc_output_pickle_names = {view: None for view in view_list}
    dlc_metadata_pickle_names = {view: None for view in view_list}
    for view in view_list:
        pickle_folder = os.path.join(session_pickle_folder, session_name + '_' + view + '_marked')
        test_string_full, test_string_meta = construct_dlc_output_pickle_names(video_metadata, view)
        test_string_full = os.path.join(pickle_folder, test_string_full)
        test_string_meta = os.path.join(pickle_folder, test_string_meta)

        pickle_full_list = glob.glob(test_string_full)
        pickle_meta_list = glob.glob(test_string_meta)

        if len(pickle_full_list) > 1:
            # ambiguity in which pickle file goes with this video
            sys.exit('Ambiguous dlc output file name for {}'.format(video_metadata['video_name']))

        if len(pickle_meta_list) > 1:
            # ambiguity in which pickle file goes with this video
            sys.exit('Ambiguous dlc output metadata file name for {}'.format(video_metadata['video_name']))

        if len(pickle_full_list) == 0:
            # no pickle file for this view
            print('No dlc output file found for {}, {} view'.format(video_metadata['video_name'], view))
            continue

        if len(pickle_meta_list) == 0:
            # no pickle file for this view
            print('No dlc output metadata file found for {}, {} view'.format(video_metadata['video_name'], view))
            continue

        dlc_output_pickle_names[view] = pickle_full_list[0]
        dlc_metadata_pickle_names[view] = pickle_meta_list[0]

    return dlc_output_pickle_names, dlc_metadata_pickle_names


def construct_dlc_output_pickle_names(video_metadata, view):
    """

    :param video_metadata:
    :param view: string containing 'direct', 'leftmirror', or 'rightmirror'
    :return:
    """
    if video_metadata['boxnum'] == 99:
        pickle_name_full = video_metadata['ratID'] + '_' + \
                           video_metadata['triggertime'].strftime('%Y%m%d_%H-%M-%S') + '_' + \
                           '{:03d}'.format(video_metadata['video_number']) + '_' + \
                           view + '_*_full.pickle'

        pickle_name_meta = video_metadata['ratID'] + '_' + \
                           video_metadata['triggertime'].strftime('%Y%m%d_%H-%M-%S') + '_' + \
                           '{:03d}'.format(video_metadata['video_number']) + '_' + \
                           view + '_*_meta.pickle'
    else:
        pickle_name_full = video_metadata['ratID'] + '_' + \
                      'box{:02d}'.format(video_metadata['boxnum']) + '_' + \
                      video_metadata['triggertime'].strftime('%Y%m%d_%H-%M-%S') + '_' + \
                      '{:03d}'.format(video_metadata['video_number']) + '_' + \
                      view + '_*_full.pickle'

        pickle_name_meta = video_metadata['ratID'] + '_' + \
                           'box{:02d}'.format(video_metadata['boxnum']) + '_' + \
                           video_metadata['triggertime'].strftime('%Y%m%d_%H-%M-%S') + '_' + \
                           '{:03d}'.format(video_metadata['video_number']) + '_' + \
                           view + '_*_meta.pickle'

    return pickle_name_full, pickle_name_meta


def find_calibration_file(video_metadata, calibration_parent):
    """

    :param video_metadata:
    :param calibration_parent:
    :return:
    """
    date_string = video_metadata['triggertime'].strftime('%Y%m%d')
    year_folder = os.path.join(calibration_parent, date_string[0:4])
    month_folder = os.path.join(year_folder, date_string[0:6] + '_calibration')
    calibration_folder = os.path.join(month_folder, date_string[0:6] + '_calibration_files')

    test_name = 'SR_boxCalibration_box{:02d}_{}.mat'.format(video_metadata['boxnum'], date_string)
    test_name = os.path.join(calibration_folder, test_name)

    if os.path.exists(test_name):
        return test_name
    else:
        return ''
        # sys.exit('No calibration file found for ' + video_metadata['video_name'])


def create_trajectory_filename(video_metadata):

    trajectory_name = video_metadata['ratID'] + '_' + \
        'box{:02d}'.format(video_metadata['boxnum']) + '_' + \
        video_metadata['triggertime'].strftime('%Y%m%d_%H-%M-%S') + '_' + \
        '{:03d}'.format(video_metadata['video_number']) + '_3dtrajectory'

    return trajectory_name


def find_camera_calibration_video(video_metadata, calibration_parent):
    """

    :param video_metadata:
    :param calibration_parent:
    :return:
    """
    date_string = video_metadata['triggertime'].strftime('%Y%m%d')
    year_folder = os.path.join(calibration_parent, date_string[0:4])
    month_folder = os.path.join(year_folder, date_string[0:6] + '_calibration')
    calibration_video_folder = os.path.join(month_folder, 'camera_calibration_videos_' + date_string[0:6])

    test_name = 'CameraCalibration_box{:02d}_{}_*.mat'.format(video_metadata['boxnum'], date_string)
    test_name = os.path.join(calibration_video_folder, test_name)

    calibration_video_list = glob.glob(test_name)

    if len(calibration_video_list) == 0:
        sys.exit('No camera calibration video found for ' + video_metadata['video_name'])

    if len(calibration_video_list) == 1:
        return calibration_video_list[0]

    # more than one potential video was found
    # find the last relevant calibration video collected before the current reaching video
    vid_times = []
    for cal_vid in calibration_video_list:
        cam_cal_md = parse_camera_calibration_video_name(cal_vid)
        vid_times.append(cam_cal_md['time'])

    last_time_prior_to_video = max(d for d in vid_times if d < video_metadata['triggertime'])

    calibration_video_name = calibration_video_list[vid_times.index(last_time_prior_to_video)]

    return calibration_video_name


def parse_camera_calibration_video_name(calibration_video_name):
    """

    :param calibration_video_name: form of CameraCalibration_boxXX_YYYYMMDD_HH-mm-ss.avi
    :return:
    """
    camera_calibration_metadata = {
        'boxnum': 99,
        'time': datetime(1, 1, 1)
    }
    _, cal_vid_name = os.path.split(calibration_video_name)
    cal_vid_name, _ = os.path.splitext(cal_vid_name)

    cal_vid_name_parts = cal_vid_name.split('_')

    camera_calibration_metadata['boxnum'] = int(cal_vid_name_parts[1][3:])

    datetime_str = cal_vid_name_parts[2] + '_' + cal_vid_name_parts[3]
    camera_calibration_metadata['time'] = datetime.strptime(datetime_str, '%Y%m%d_%H-%M-%S')

    return camera_calibration_metadata


def create_calibration_filename(calibration_metadata, calibration_parent):

    date_string = calibration_metadata['time'].strftime('%Y%m%d')
    datetime_string = calibration_metadata['time'].strftime('%Y%m%d_%H-%M-%S')
    year_folder = os.path.join(calibration_parent, date_string[0:4])
    month_folder = os.path.join(year_folder, date_string[0:6] + '_calibration')
    calibration_folder = os.path.join(month_folder, date_string[0:6] + '_calibration_files')

    if not os.path.isdir(calibration_folder):
        os.makedirs(calibration_folder)

    calibration_name = 'calibration_box{:02d}_{}.pickle'.format(calibration_metadata['boxnum'], datetime_string)
    calibration_name = os.path.join(calibration_folder, calibration_name)

    return calibration_name


def create_mat_fname_dlc_output(video_metadata, dlc_mat_output_parent):

    mat_path = os.path.join(dlc_mat_output_parent,
                            video_metadata['ratID'],
                            video_metadata['session_name'])

    if not os.path.isdir(mat_path):
        os.makedirs(mat_path)

    mat_name = '{}_box{:02d}_{}_{:03d}_dlc-out.mat'.format(video_metadata['ratID'],
                                                           video_metadata['boxnum'],
                                                           video_metadata['triggertime'].strftime('%Y%m%d_%H-%M-%S'),
                                                           video_metadata['video_number']
                                                           )
    mat_name = os.path.join(mat_path, mat_name)

    return mat_name


def find_marked_vids_for_3d_reconstruction(marked_vids_parent, dlc_mat_output_parent, rat_df):

    # find marked vids for which we have both relevant views (eventually, need all 3 views)
    marked_rat_folders = glob.glob(os.path.join(marked_vids_parent, 'R*'))

    # return a list of video_metadata dictionaries
    metadata_list = []
    for rat_folder in marked_rat_folders:
        if os.path.isdir(rat_folder):
            _, ratID = os.path.split(rat_folder)
            rat_num = int(ratID[1:])
            paw_pref = rat_df[rat_df['ratID'] == rat_num]['pawPref'].values[0]
            if paw_pref == 'right':
                mirrorview = 'leftmirror'
            else:
                mirrorview = 'rightmirror'
            # find the paw preference for this rat

            session_folders = glob.glob(os.path.join(rat_folder, ratID + '_*'))

            for session_folder in session_folders:
                if os.path.isdir(session_folder):
                    _, session_name = os.path.split(session_folder)

                    # check that there is a direct_marked folder for this session
                    direct_marked_folder = os.path.join(session_folder, session_name + '_direct_marked')
                    mirror_marked_folder = os.path.join(session_folder, session_name + '_' + mirrorview + '_marked')

                    if not os.path.isdir(mirror_marked_folder):
                        continue

                    if os.path.isdir(direct_marked_folder):
                        # find all the full_pickle and metadata_pickle files in the folder, and look to see if there are
                        # matching files in the appropriate mirror view folder
                        test_name = ratID + '_*_full.pickle'
                        full_pickle_list = glob.glob(os.path.join(direct_marked_folder, test_name))

                        for full_pickle_file in full_pickle_list:
                            # is there a matching metadata file, as well as matching metadata files in the mirror folder?
                            _, pickle_name = os.path.split(full_pickle_file)
                            pickle_metadata = parse_dlc_output_pickle_name(pickle_name)
                            # crop_window_string = '{:d}-{:d}-{:d}-{:d}'.format(pickle_metadata['crop_window'][0],
                            #                                                   pickle_metadata['crop_window'][1],
                            #                                                   pickle_metadata['crop_window'][2],
                            #                                                   pickle_metadata['crop_window'][3]
                            #                                                   )
                            meta_direct_file = os.path.join(direct_marked_folder, pickle_name.replace('full', 'meta'))
                            vid_prefix = pickle_name[:pickle_name.find('direct')]
                            test_mirror_name = vid_prefix + '*_full.pickle'
                            full_mirror_name_list = glob.glob(os.path.join(mirror_marked_folder, test_mirror_name))
                            if len(full_mirror_name_list) == 1:
                                full_mirror_file = full_mirror_name_list[0]
                                _, full_mirror_name = os.path.split(full_mirror_file)
                                meta_mirror_file = os.path.join(mirror_marked_folder, full_mirror_name.replace('full', 'meta'))
                                if os.path.exists(meta_direct_file) and os.path.exists(meta_mirror_file):

                                    video_name = '{}_box{:02d}_{}_{:03d}.avi'.format(ratID,
                                                                                     pickle_metadata['boxnum'],
                                                                                     pickle_metadata['triggertime'].strftime('%Y%m%d_%H-%M-%S'),
                                                                                     pickle_metadata['video_number'])
                                    video_metadata = {
                                        'ratID': ratID,
                                        'rat_num': rat_num,
                                        'session_name': session_name,
                                        'boxnum': pickle_metadata['boxnum'],
                                        'triggertime': pickle_metadata['triggertime'],
                                        'video_number': pickle_metadata['video_number'],
                                        'video_type': '.avi',
                                        'video_name': video_name,
                                        'im_size': (1024, 2040)
                                    }
                                    mat_output_name = create_mat_fname_dlc_output(video_metadata, dlc_mat_output_parent)
                                    # check if these files have already been processed
                                    if not os.path.exists(mat_output_name):
                                        # .mat file doesn't already exist
                                        metadata_list.append(video_metadata)

    return metadata_list



def find_Burgess_calibration_folder(calibration_parent, session_datetime):

    session_year = session_datetime.strftime('%Y')
    session_month = session_datetime.strftime('%m')

    year_folder = 'calibration_vids_' + session_year
    month_folder = year_folder + session_month

    calibration_folder = os.path.join(calibration_parent, year_folder, month_folder)

    if os.path.exists(calibration_folder):
        return calibration_folder
    else:
        return none


def find_Burgess_calibration_vids(cal_vid_parent, session_datetime, cam_list=(1, 2)):

    cal_vid_folder = find_Burgess_calibration_folder(cal_vid_parent, session_datetime)

    basename = 'calibration_cam'
    full_paths = []

    for i_cam in cam_list:
        vid_name = basename + '{:02d}_{date_string}.avi'.format(i_cam, date_string=datetime_to_string_for_fname(session_datetime))
        full_paths.append(os.path.join(cal_vid_folder, vid_name))

    return full_paths


def parse_Burgess_calibration_vid_name(cal_vid_name):

    _, cal_vid_name = os.path.split(cal_vid_name)
    bare_name, _ = os.path.splitext(cal_vid_name)

    name_parts_list = bare_name.split('_')

    cal_name_parts = {
        'cam_num': int(name_parts_list[1][3:]),
        'session_datetime': fname_string_to_datetime(name_parts_list[2] + '_' + name_parts_list[3])
    }

    return cal_name_parts


def create_calibration_data_name(cal_data_parent, session_datetime):

    basename = 'calibration_data'
    cal_data_name = basename + '_' + datetime_to_string_for_fname(session_datetime) + '.pickle'

    cal_data_folder = create_calibration_data_folder(cal_data_parent, session_datetime)
    cal_data_name = os.path.join(cal_data_folder, cal_data_name)

    return cal_data_name


def create_calibration_data_folder(cal_data_parent, session_datetime):

    year_folder = 'calibration_data_' + session_datetime.strftime('%Y')
    month_folder = year_folder + session_datetime.strftime('%m')

    cal_data_folder = os.path.join(cal_data_parent, year_folder, month_folder)

    if not os.path.exists(cal_data_folder):
        os.makedirs(cal_data_folder)

    return cal_data_folder


def datetime_to_string_for_fname(date_to_convert):

    format_string = '%Y%m%d_%H-%M-%S'

    datetime_string = date_to_convert.strftime('%Y%m%d_%H-%M-%S')

    return datetime_string


def fname_string_to_datetime(string_to_convert):
    format_string = '%Y%m%d_%H-%M-%S'

    datetime_from_fname = datetime.strptime(string_to_convert, format_string)

    return datetime_from_fname