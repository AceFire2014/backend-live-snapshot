# -*- coding: utf-8 -*-
import logging
import os
import subprocess as sp
import shlex
import json
import time
from datetime import datetime
from typing import List

from celery.exceptions import SoftTimeLimitExceeded
from requests.exceptions import RequestException

from common.cams.api import CamsAPI
from common.cams.objects import StreamSession, ChatTypeEnum
from common.cams.requesters.syn import CamsAPISyncRequester
from common.config import config
from tasks import celery_app

log = logging.getLogger(__name__)

cams_api = CamsAPI(CamsAPISyncRequester(config.CAMS_URL))

if config.MODE == 'dev':
    from celery.signals import worker_ready

    @worker_ready.connect
    def at_start(sender, **k):
        with sender.app.connection() as conn:
            sender.app.send_task('tasks.tasks.make_all_preview_videos', connection=conn)


def ensure_exists(path):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


def cleanup_files(directory: str, file_filter):
    try:
        with os.scandir(directory) as it:
            files_to_delete = [entry.name for entry in it
                               if entry.is_file()
                               and file_filter(entry.name, entry.stat())]
    except FileNotFoundError:
        log.info(f'{directory} does not exist, no need to delete files.')
        return

    for file in files_to_delete:
        log.info('Removing file: %s', file)
        try:
            os.unlink(os.path.join(directory, file))
        except FileNotFoundError:
            pass
        except PermissionError as e:
            log.warning('Can not cleanup file: %s', exc_info=e)


@celery_app.task(soft_time_limit=config.PREVIEW_VIDEO_UPDATE_PERIOD,
                 expires=config.PREVIEW_VIDEO_UPDATE_PERIOD, ignore_result=True)
def make_all_preview_videos() -> None:
    ensure_exists(config.PREVIEW_VIDEO_STORAGE_PATH)

    won = cams_api.get_won()

    log.info(f'make_all_preview_videos: {won}')
    for i in range(len(won.won_stream_names)):
        make_preview_video.apply_async(
            kwargs={
                'stream_name': won.won_stream_names[i],
            },
            ignore_result=True,
            countdown=(int(i/config.PREVIEW_VIDEO_TASK_CHUNK_SIZE))*config.PREVIEW_VIDEO_TASK_COUNTDOWN_MULTIPLIER,
        )


def _get_stream(stream_name: str) -> StreamSession:
    try:
        return cams_api.get_stream(stream_name)
    except RequestException as e:
        if e.response is not None and e.response.status_code == 404:
            log.info(f'{stream_name}: No active stream')
        else:
            log.error(f'{stream_name}: Cams raised error: {e}')
        return None


def _get_rtmp_url(stream: dict) -> str:
    subdomain = stream.subdomain
    stream_name = stream.stream_name.lower()
    '''
    Per Murat's comment:
    we got 3 outputs now,
    (1) modelname_720p is raw video, no transcoding.
    (2) modelname__720p is 720p transcode at fixed video bitrate of 1300 kbps.
    (3) modelname__360p is 360p transcode at 550 kbps.
    we should use modelname__720p to grab video.
    '''

    rtmp_url = f'rtmp://{subdomain}/cams/{stream_name}/{stream_name}__720p'
    return rtmp_url


def _get_preview_video_name(stream_name: str) -> str:
    now = datetime.now()
    return f'preview_video_{now:%Y.%m.%d.%H.%M.%S.%f}_{stream_name}.mp4'


def _capture_preview_video(preview_video_file_path: str, rtmp_url: str, stream_name: str) -> None:
    ffmpeg_cmd = f'timeout 30s ffmpeg -y -hide_banner -loglevel error -re -i "{rtmp_url}" '\
                 f'-t 10 -movflags +faststart -c copy "{preview_video_file_path}"'
    log.info(f'{stream_name}: ffmpeg_cmd: {ffmpeg_cmd}')

    try:
        os.system(ffmpeg_cmd)
    except Exception as e:
        log.error(f'{stream_name}: _capture_preview_video: {e}')
        raise


def _is_curtain_dropped():
    # TODO
    return False


def _is_valid_stream(chat_type: ChatTypeEnum) -> bool:
    if (chat_type not in (ChatTypeEnum.FREE, ChatTypeEnum.TIPPING)):
        return False
    elif (chat_type is ChatTypeEnum.TIPPING and _is_curtain_dropped()):
        return False
    else:
        return True


def _is_preview_video_size_valid(preview_video_file_path: str) -> bool:
    file_size = os.path.getsize(preview_video_file_path)
    return file_size > config.PREVIEW_VIDEO_FILE_SIZE_THRESHOLD


def _is_blurry(preview_video_file_path: str) -> bool:
    bash_cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=bit_rate,r_frame_rate,avg_frame_rate '\
               f'-print_format json "{preview_video_file_path}"'
    data = sp.run(shlex.split(bash_cmd), stdout=sp.PIPE).stdout
    dict_data = json.loads(data)
    try:
        bit_rate = int(dict_data['streams'][0]['bit_rate'])
        r_frame_rate1, r_frame_rate2 = dict_data['streams'][0]['r_frame_rate'].split('/')
        r_frame_rate = int(r_frame_rate1) / int(r_frame_rate2)
        avg_frame_rate1, avg_frame_rate2 = dict_data['streams'][0]['avg_frame_rate'].split('/')
        avg_frame_rate = int(avg_frame_rate1) / int(avg_frame_rate2)
        if (r_frame_rate <= 11 or avg_frame_rate <= 11 or bit_rate < 450000):
            return True
        else:
            return False
    except Exception as e:
        log.error(f'{bash_cmd}: _is_blurry() : {e}')
        raise


def _get_preview_video_symlink_file_name(stream_name: str) -> str:
    return f'{stream_name.lower()}.mp4'


def _get_preview_video_symlink_file_path(stream_name: str) -> str:
    file_name = _get_preview_video_symlink_file_name(stream_name)
    return os.path.join(config.PREVIEW_VIDEO_STORAGE_PATH, file_name)


def _update_preview_video_symlink(stream_name: str, preview_video_file_path: str) -> None:
    try:
        symlink_file_path = _get_preview_video_symlink_file_path(stream_name)
        update_symlink_cmd = f'ln -sfn {preview_video_file_path} {symlink_file_path}'
        os.system(update_symlink_cmd)
    except Exception as e:
        log.error(f'{stream_name}: _update_preview_video_symlink: {e}')
        raise


def _is_old_preview_videos(stream_name: str, filename: str, exclusive_file_names: List[str]) -> bool:
    return ((stream_name in filename) and (filename not in exclusive_file_names))


def _cleanup_preview_videos(stream_name: str, exclusive_file_names: List[str]) -> None:
    log.info(f'{stream_name}: _cleanup_preview_videos start')
    cleanup_files(directory=config.PREVIEW_VIDEO_STORAGE_PATH,
                  file_filter=(lambda filename, file_stat:
                               _is_old_preview_videos(stream_name, filename, exclusive_file_names)))
    log.info(f'{stream_name}: _cleanup_preview_videos end')


def _get_preview_video_file_path(preview_video_name: str) -> str:
    return os.path.join(config.PREVIEW_VIDEO_STORAGE_PATH, preview_video_name)


@celery_app.task(soft_time_limit=config.PREVIEW_VIDEO_UPDATE_PERIOD,
                 expires=config.PREVIEW_VIDEO_UPDATE_PERIOD, ignore_result=True)
def make_preview_video(stream_name: str) -> None:
    try:
        log.info(f'{stream_name}: make_preview_video start')

        stream = _get_stream(stream_name)
        if not _is_valid_stream(stream.chat_type):
            return

        ensure_exists(config.PREVIEW_VIDEO_STORAGE_PATH)
        new_preview_video_name = _get_preview_video_name(stream_name)
        new_preview_video_file_path = _get_preview_video_file_path(new_preview_video_name)

        rtmp_url = _get_rtmp_url(stream)
        _capture_preview_video(new_preview_video_file_path, rtmp_url, stream_name)

        symlink_file_name = _get_preview_video_symlink_file_name(stream_name)
        exclusive_file_names = [symlink_file_name]
        if _is_preview_video_size_valid(new_preview_video_file_path) and not _is_blurry(new_preview_video_file_path):
            _update_preview_video_symlink(stream_name, new_preview_video_file_path)
            exclusive_file_names.append(new_preview_video_name)
            log.info('keep new video: {new_preview_video_name}')
        else:
            symlink_file_path = _get_preview_video_symlink_file_path(stream_name)
            existing_preview_video_name = os.path.realpath(symlink_file_path).split('/')[-1]
            exclusive_file_names.append(existing_preview_video_name)
            log.info('keep old video: {existing_preview_video_name}')
        _cleanup_preview_videos(stream_name, exclusive_file_names)
    except SoftTimeLimitExceeded:
        log.error(f'{stream_name}: Failed to create preview video within the time specified.')
    except Exception as e:
        log.error(f'{stream_name}: make_preview_video error: {e}')
    finally:
        log.info(f'{stream_name}: make_preview_video end')


def _is_preview_video_expired(current_time: int, modified_time: int):
    return (current_time - modified_time) > config.PREVIEW_VIDEO_EXPIRE_PERIOD


@celery_app.task(expires=config.PREVIEW_VIDEO_CLEAN_PERIOD, ignore_result=True)
def cleanup_preview_videos():
    log.info('cleanup_preview_videos start')
    ensure_exists(config.PREVIEW_VIDEO_STORAGE_PATH)
    current_time = time.time()
    cleanup_files(directory=config.PREVIEW_VIDEO_STORAGE_PATH,
                  file_filter=(lambda filename, file_stat:
                               _is_preview_video_expired(current_time, file_stat.st_mtime)))
    log.info('cleanup_preview_videos end')
