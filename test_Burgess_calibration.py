import glob
import skilled_reaching_calibration
import navigation_utilities
from datetime import datetime





if __name__ == '__main__':
    cal_vids = ['/Users/dan/Documents/Burgess_sr_videos/calibation_videos/calibration_vids_2021/calibration_vids_202107/calibration_cam01_20210701_15-30-33.avi']
    cal_vids.append('/Users/dan/Documents/Burgess_sr_videos/calibation_videos/calibration_vids_2021/calibration_vids_202107/calibration_cam02_20210701_15-30-33.avi')

    cal_vid_parent = '/Users/dan/Documents/Burgess_sr_videos/calibation_videos'
    cal_data_parent = '/Users/dan/Documents/Burgess_sr_videos/calibration_data'

    session_datetime = datetime.strptime('20210701_15-30-33', '%Y%m%d_%H-%M-%S')

    cb_size = (10,7)

    cal_vids = navigation_utilities.find_Burgess_calibration_vids(cal_vid_parent, session_datetime)
    skilled_reaching_calibration.multi_camera_calibration(cal_vids, cal_data_parent, cb_size=cb_size)