from django.core.cache import cache
import json


CACHE_TTL = 300  # 5 menit
COURSE_LIST_KEY = "course_list:{page}:{per_page}:{search}:{ordering}"
COURSE_DETAIL_KEY = "course_detail:{id}"


def get_course_list_cache(page, per_page, search, ordering):
    key = COURSE_LIST_KEY.format(
        page=page, per_page=per_page,
        search=search or "none", ordering=ordering
    )
    return cache.get(key)


def set_course_list_cache(page, per_page, search, ordering, data):
    key = COURSE_LIST_KEY.format(
        page=page, per_page=per_page,
        search=search or "none", ordering=ordering
    )
    cache.set(key, data, CACHE_TTL)


def get_course_detail_cache(course_id):
    key = COURSE_DETAIL_KEY.format(id=course_id)
    return cache.get(key)


def set_course_detail_cache(course_id, data):
    key = COURSE_DETAIL_KEY.format(id=course_id)
    cache.set(key, data, CACHE_TTL)


def invalidate_course_cache(course_id=None):
    """Invalidate cache saat course diupdate/dihapus"""
    if course_id:
        key = COURSE_DETAIL_KEY.format(id=course_id)
        cache.delete(key)
    # Hapus semua course list cache
    cache.delete_pattern("course_list:*")
