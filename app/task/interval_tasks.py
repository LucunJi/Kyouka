import datetime
import traceback
import aiohttp

from loguru import logger
from khl import Bot
from app.config.common import settings
from app.utils.channel_utils import update_channel_name_by_bot
from app.voice_utils.container_handler import create_container, stop_container
from app.music.bilibili.search import BPROXY_API


async def update_played_time_and_change_music():
    logger.debug(f"PLAYED: {settings.played}")
    logger.debug(f"Q: {settings.playqueue}")
    logger.debug(f"LOCK: {settings.lock}")

    if settings.lock:
        return None
    else:
        settings.lock = True

        try:
            if len(settings.playqueue) == 0:
                settings.played = 0
                settings.lock = False
                return None
            else:
                first_music = settings.playqueue[0]
                if settings.played == 0:
                    await stop_container(settings.container_name)
                    await create_container(settings.token, settings.channel, first_music.source, 'false',
                                           settings.container_name)

                    first_music.endtime = int(datetime.datetime.now().timestamp() * 1000) + first_music.duration

                    settings.played += 5000
                    settings.lock = False
                    return None
                else:
                    duration = first_music.duration
                    if settings.played + 5000 < duration:
                        settings.played += 5000
                        settings.lock = False
                        return None
                    else:
                        settings.playqueue.popleft()
                        if len(settings.playqueue) == 0:
                            await stop_container(settings.container_name)
                            settings.played = 0
                            settings.lock = False
                            return None
                        else:
                            next_music = settings.playqueue[0]
                            await stop_container(settings.container_name)
                            await create_container(settings.token, settings.channel, next_music.source, 'false',
                                                   settings.container_name)

                            next_music.endtime = int(datetime.datetime.now().timestamp() * 1000) + next_music.duration

                            settings.played = 5000
                            settings.lock = False
                            return None
        except Exception as e:
            settings.lock = False
            logger.error(f"error occurred in automatically changing music, error msg: {e}, traceback: {traceback.format_exc()}")

async def clear_expired_candidates_cache():
    if settings.candidates_lock:
        return None
    else:
        settings.candidates_lock = True
        try:
            now = datetime.datetime.now()

            need_to_clear = []
            for this_user in settings.candidates_map:
                if now >= settings.candidates_map.get(this_user, {}).get("expire", now):
                    need_to_clear.append(this_user)
            
            for user_need_to_clear in need_to_clear:
                settings.candidates_map.pop(user_need_to_clear, None)
                logger.info(f"cache of user: {user_need_to_clear} is removed")
            
            settings.candidates_lock = False
            return None

        except Exception as e:
            settings.candidates_lock = False
            logger.error(f"error occurred in clearing expired candidates cache, error msg: {e}, traceback: {traceback.format_exc()}")

async def keep_bproxy_alive():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BPROXY_API) as r:
                resp_json = await r.json()
                logger.debug(resp_json)
                logger.info("bproxy is alive now")
    except Exception as e:
        logger.error(f"bproxy is not available, error msg: {e}, traceback: {traceback.format_exc()}")
        logger.error("bproxy is not alive now")

async def update_kanban_info(bot: Bot):
    try:
        if settings.kanban:
            status = "空闲" if len(settings.playqueue) == 0 else "繁忙"
            kanban_info = f"{settings.bot_name}: {status}"
            await update_channel_name_by_bot(bot=bot, channel_id=settings.kanban_channel, new_name=kanban_info)
            logger.info(f"kanban info is updated to {kanban_info} successfully")
    except Exception as e:
        logger.error(f"failed to update the kanban info, error msg: {e}, traceback: {traceback.format_exc()}")
