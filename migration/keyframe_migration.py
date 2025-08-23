import sys
import os
ROOT_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')
)
sys.path.insert(0, ROOT_FOLDER)



from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
import json
from collections import Counter
import asyncio
from tqdm import tqdm
import argparse
import string


from app.core.settings import MongoDBSettings
from app.models.keyframe import Keyframe, ObjectCount
from app.models.speech_caption import SpeechCaption

SETTING = MongoDBSettings()

async def init_db():
    client = AsyncIOMotorClient(
        host=SETTING.MONGO_HOST,
        port=SETTING.MONGO_PORT,
        username=SETTING.MONGO_USER,
        password=SETTING.MONGO_PASSWORD,
    )
    await init_beanie(database=client[SETTING.MONGO_DB], document_models=[Keyframe, SpeechCaption])


def load_json_data(file_path):
    return json.load(open(file_path, 'r', encoding='utf-8'))

def load_jsonl_data(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))    
    return data

def get_object_counts(obj_fp: str) -> list[ObjectCount]:
    with open(obj_fp, 'r') as f:
        data = json.loads(f.read())['detection_class_entities']
    object_list = []
    counts = Counter(data).items()
    for obj, count in counts:
        object_list.append(ObjectCount(name=obj, count=count))
    return object_list

def transform_data(data: dict[str,str], object_folder: str) -> list[Keyframe]:
    """
    Convert the data from the old format to the new Keyframe model.
    """
    keyframes = []  
    for key, value in tqdm(data.items(), desc='Inserting keyframes'):
        group, video, keyframe = value.split('_')
        keyframe_obj = Keyframe(
            key=int(key),
            video_num=int(video[1:]),
            group_num=int(group[1:]),
            keyframe_num=int(keyframe),
            objects=get_object_counts(os.path.join(object_folder, f'{group}_{video}', f'{keyframe}.json'))
        )
        keyframes.append(keyframe_obj)
    return keyframes

async def migrate_keyframes(file_path, object_folder):
    data = load_json_data(file_path)
    keyframes = transform_data(data, object_folder)

    await Keyframe.delete_all()
    
    await Keyframe.insert_many(keyframes)
    print(f"Inserted {len(keyframes)} keyframes into the database.")

def preprocess_text(text: str) -> str:
    # return text.translate(str.maketrans('', '', string.punctuation)).lower()
    return text.lower()


async def migrate_speech_captions(caption_folder: str):
    captions = []
    print('Inserting captions ...')
    for root, _, files in os.walk(caption_folder):
        for file in files:
            if file.endswith('.jsonl'):
                group_id, video_id = file.split('.')[0].split('_')
                group_id = int(group_id[1:])
                video_id = int(video_id[1:])
                path = os.path.join(root, file)
                data = load_jsonl_data(path)
                for caption in data:
                    captions.append(SpeechCaption(
                        group_num=group_id,
                        video_num=video_id,
                        start=caption['start'],
                        end=caption['end'],
                        text=preprocess_text(caption['text'])
                    ))
    await SpeechCaption.delete_all()
    await SpeechCaption.insert_many(captions)
    print(f"Inserted {len(captions)} captions into the database.")

async def main(args):
    await init_db()
    await migrate_keyframes(args.file_path, args.object_folder)
    await migrate_speech_captions(args.caption_folder)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate keyframes to MongoDB.")
    parser.add_argument(
        "--file_path", type=str, help="Path to the JSON file containing keyframe data."
    )
    parser.add_argument(
        "--object_folder", type=str, help="Path to the object detection folder."
    )
    
    parser.add_argument(
        "--caption_folder", type=str, help="Path to ASR folder"
    )
    
    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        print(f"File {args.file_path} does not exist.")
        sys.exit(1)
    
    asyncio.run(main(args))

