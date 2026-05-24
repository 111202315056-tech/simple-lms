from pymongo import MongoClient
from django.conf import settings
from datetime import datetime


_client = None
_db = None


def get_mongo_client():
    global _client
    if _client is None:
        try:
            _client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
            _client.server_info()
        except Exception as e:
            print(f"[MongoDB] Connection failed: {e}")
            _client = None
    return _client


def get_mongo_db():
    global _db
    client = get_mongo_client()
    if client is None:
        return None
    if _db is None:
        _db = client[settings.MONGO_DB]
    return _db


def log_activity(user_id, action, details=None):
    """Log user activity ke MongoDB"""
    db = get_mongo_db()
    if db is None:
        print(f"[MongoDB] Skipping log: {action}")
        return None
    try:
        doc = {
            "user_id": user_id,
            "action": action,
            "details": details or {},
            "timestamp": datetime.utcnow(),
        }
        result = db.activity_logs.insert_one(doc)
        return str(result.inserted_id)
    except Exception as e:
        print(f"[MongoDB] Log failed: {e}")
        return None


def log_course_view(user_id, course_id, course_name):
    """Log course view untuk analytics"""
    return log_activity(
        user_id=user_id,
        action="course_view",
        details={"course_id": course_id, "course_name": course_name}
    )


def get_activity_logs(user_id=None, limit=50):
    """Ambil activity logs dari MongoDB"""
    db = get_mongo_db()
    if db is None:
        return []
    try:
        query = {}
        if user_id:
            query["user_id"] = user_id
        logs = list(db.activity_logs.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit))
        return logs
    except Exception as e:
        print(f"[MongoDB] Query failed: {e}")
        return []


def get_popular_courses(limit=10):
    """Get popular courses berdasarkan views"""
    db = get_mongo_db()
    if db is None:
        return []
    try:
        pipeline = [
            {"$match": {"action": "course_view"}},
            {"$group": {
                "_id": "$details.course_id",
                "course_name": {"$first": "$details.course_name"},
                "view_count": {"$sum": 1}
            }},
            {"$sort": {"view_count": -1}},
            {"$limit": limit}
        ]
        return list(db.activity_logs.aggregate(pipeline))
    except Exception as e:
        print(f"[MongoDB] Aggregation failed: {e}")
        return []
