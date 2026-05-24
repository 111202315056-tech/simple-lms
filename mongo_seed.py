import os
import random
from datetime import datetime, timedelta

from pymongo import MongoClient

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://127.0.0.1:27017/')
MONGODB_NAME = os.getenv('MONGODB_NAME', 'simple_lms')

client = MongoClient(MONGODB_URI)
db = client[MONGODB_NAME]
collection = db.activity_logs

collection.drop()

courses = [
    'Django Basics',
    'Python Advanced',
    'Docker Fundamentals',
    'REST API Design',
    'Database Optimization',
    'Redis Caching',
    'Authentication & Security',
    'Automated Testing',
]
actions = ['view_course', 'enroll', 'post_comment', 'view_content', 'submit_quiz', 'download_material']
browsers = ['Chrome', 'Firefox', 'Safari', 'Edge']

logs = []
for i in range(250):
    user_id = random.randint(1, 40)
    course_name = random.choice(courses)
    action = random.choice(actions)
    days_ago = random.randint(0, 30)
    timestamp = datetime.utcnow() - timedelta(
        days=days_ago,
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    metadata = {
        'ip': f'192.168.1.{random.randint(1, 255)}',
        'browser': random.choice(browsers),
        'duration_seconds': random.randint(10, 1800),
    }
    if action == 'post_comment':
        metadata['comment_length'] = random.randint(20, 300)
    if action == 'submit_quiz':
        metadata['score'] = random.randint(50, 100)

    logs.append({
        'user_id': user_id,
        'action': action,
        'course_name': course_name,
        'timestamp': timestamp,
        'metadata': metadata,
    })

result = collection.insert_many(logs)
print(f'Inserted {len(result.inserted_ids)} activity logs into {MONGODB_NAME}.activity_logs')
print(f'Total documents: {collection.count_documents({})}')
