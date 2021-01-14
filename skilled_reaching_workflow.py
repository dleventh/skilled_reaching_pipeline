from crop_videos import preprocess_videos
import navigation_utilities
import glob
import os
import shutil
import deeplabcut


def analyze_cropped_videos(folders_to_analyze, view_config_paths, cropped_vid_type='.avi', gputouse=0):
    '''

    :param folders_to_analyze:
    :param view_config_paths:
    :param cropped_vid_type:
    :param gputouse:
    :return: scorernames - dictionary with keys 'direct' and 'mirror' containing the scorername strings returned by
        deeplabcut.analyze_videos
    '''

    view_list = folders_to_analyze.keys()
    scorernames = {'direct': '', 'mirror': ''}
    for view in view_list:
        if 'direct' in view:
            dlc_network = 'direct'
        elif 'mirror' in view:
            dlc_network = 'mirror'
        else:
            print(view + ' does not contain the keyword "direct" or "mirror"')
            continue

        config_path = view_config_paths[dlc_network]
        current_view_folders = folders_to_analyze[view]

        for current_folder in current_view_folders:
            cropped_video_list = glob.glob(current_folder + '/*' + cropped_vid_type)
            #todo: skip if analysis already done and stored in the _marked folder
            scorername = deeplabcut.analyze_videos(config_path,
                                      cropped_video_list,
                                      videotype=cropped_vid_type,
                                      gputouse=gputouse)
            scorernames[dlc_network] = scorername

    return scorernames


def create_labeled_videos(folders_to_analyze, view_config_paths, scorernames, cropped_vid_type='.avi', move_to_new_folder=True):
    '''
    
    :param folders_to_analyze: 
    :param view_config_paths: 
    :param scorernames: dictionary with keys 'direct' and 'mirror'
    :param cropped_vid_type:
    :param move_to_new_folder: if True, create a new folder in which the marked videos and analysis files are stored
        to make it easier to move them to another computer without taking the original videos with them
    :return: 
    '''
    view_list = folders_to_analyze.keys()

    for view in view_list:
        if 'direct' in view:
            dlc_network = 'direct'
        elif 'mirror' in view:
            dlc_network = 'mirror'
        else:
            print(view + ' does not contain the keyword "direct" or "mirror"')
            continue
        config_path = view_config_paths[dlc_network]
        scorername = scorernames[dlc_network]
        current_view_folders = folders_to_analyze[view]

        for current_folder in current_view_folders:
            cropped_video_list = glob.glob(current_folder + '/*' + cropped_vid_type)
            deeplabcut.create_video_with_all_detections(config_path, cropped_video_list, scorername)

            if move_to_new_folder:
                new_dir = current_folder + '_marked'
                if not os.path.isdir(new_dir):
                    os.mkdir(new_dir)
                test_name = os.path.join(current_folder, '*' + scorername + '*.mp4')
                marked_vid_list = glob.glob(test_name)
                pickle_list = glob.glob(os.path.join(current_folder, '*.pickle'))

                for marked_vid in marked_vid_list:
                    # if the file already exists in the marked_vid directory, don't move it
                    _, marked_vid_name = os.path.split(marked_vid)
                    if not os.path.isfile(os.path.join(new_dir, marked_vid_name)):
                        shutil.move(marked_vid, new_dir)
                for pickle_file in pickle_list:
                    # if the file already exists in the marked_vid directory, don't move it
                    _, pickle_name = os.path.split(pickle_file)
                    if not os.path.isfile(os.path.join(new_dir, pickle_name)):
                        shutil.move(pickle_file, new_dir)


if __name__ == '__main__':

    label_videos = True

    gputouse = 2
    # step 1: preprocess videos to extract left mirror, right mirror, and direct views

    view_list = ('direct', 'leftmirror', 'rightmirror')
    # parameters for cropping
    crop_params_dict = {
        view_list[0]: [700, 1350, 270, 935],
        view_list[1]: [1, 470, 270, 920],
        view_list[2]: [1570, 2040, 270, 920]
    }
    cropped_vid_type = '.avi'

    video_root_folder = '/home/levlab/Public/DLC_DKL/videos_to_analyze/videos_to_crop'
    # vid_folder_list = ['/Users/dan/Documents/deeplabcut/R0382_20200909c','/Users/dan/Documents/deeplabcut/R0230_20181114a']
    video_folder_list = navigation_utilities.get_video_folders_to_crop(video_root_folder)

    cropped_vids_parent = '/home/levlab/Public/DLC_DKL/videos_to_analyze'

    cropped_video_directories = preprocess_videos(video_folder_list, cropped_vids_parent, crop_params_dict, view_list, vidtype='avi')

    # step 2: run the vids through DLC
    # parameters for running DLC
    # need to update these paths when moved to the lambda machine
    view_config_paths = {
        'direct': '/home/levlab/Public/DLC_DKL/skilled_reaching_direct-Dan_Leventhal-2020-10-19/config.yaml',
        'mirror': '/home/levlab/Public/DLC_DKL/skilled_reaching_mirror-Dan_Leventhal-2020-10-19/config.yaml'
    }

    # in case there are some previously cropped videos that need to be analyzed
    folders_to_analyze = navigation_utilities.find_folders_to_analyze(cropped_vids_parent, view_list=view_list)

    scorernames = analyze_cropped_videos(folders_to_analyze, view_config_paths, cropped_vid_type=cropped_vid_type, gputouse=gputouse)

    if label_videos:
        create_labeled_videos(folders_to_analyze, view_config_paths, scorernames, cropped_vid_type=cropped_vid_type, move_to_new_folder=True)

    # step 3: make sure calibration has been run for these sessions