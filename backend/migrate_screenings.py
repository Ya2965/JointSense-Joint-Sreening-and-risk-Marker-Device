import asyncio
import os
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

async def fix():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    screening = await db.screenings.find_one({'patient_id': 'JS-E428C0'})
    if not screening:
        return
    acts = {
        'two-minute-walk': {
            'id': 'two-minute-walk',
            'title': 'Two-minute walk',
            'detail': 'Walking endurance & gait symmetry',
            'duration': 120,
            'movement_score': 73.1,
            'features': {'gait_speed': 0.82, 'cadence': 92.0, 'total_rom': 54.0, 'peak_loading': 118.0, 'movement_smoothness': 0.74, 'left_right_weight_asymmetry': 0.11},
            'completed_at': screening.get('created_at'),
            'status': 'completed'
        },
        'sit-to-stand': {
            'id': 'sit-to-stand',
            'title': '30-second sit-to-stand',
            'detail': 'Functional strength & stability',
            'duration': 30,
            'movement_score': 73.1,
            'features': {'sit_to_stand_time': 2.4, 'peak_loading': 143.0, 'movement_smoothness': 0.72},
            'completed_at': screening.get('created_at'),
            'status': 'completed'
        },
        'leg-abduction': {
            'id': 'leg-abduction',
            'title': '30-second leg abduction',
            'detail': 'Hip range & lateral control (open / close leg)',
            'duration': 30,
            'movement_score': 71.1,
            'features': {'total_rom': 64.0, 'left_right_weight_asymmetry': 0.16, 'acoustic_rms': 0.18},
            'completed_at': screening.get('created_at'),
            'status': 'completed'
        }
    }
    await db.screenings.update_one(
        {'id': screening['id']},
        {'$set': {
            'activities': acts,
            'completed_activity_ids': list(acts.keys()),
            'activities_completed': 3,
            'total_activities': 3,
            'is_complete': True,
            'test': '3-activity-battery'
        }}
    )
    await db.patients.update_one({'id': 'JS-E428C0'}, {'$set': {'screenings': 1}})
    print('Updated screening with all 3 activities successfully!')

if __name__ == '__main__':
    asyncio.run(fix())
