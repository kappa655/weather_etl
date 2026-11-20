import requests
import json
from datetime import datetime
import boto3
from botocore.client import Config
from dotenv import load_dotenv
import os



# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API = os.getenv("API")
endpoint = os.getenv("endpoint")
username = os.getenv("username")
password = os.getenv("password")


# ============================================================
# API
# ============================================================

def get_weather(url):
    response = requests.get(url=url, timeout=10)
    response.raise_for_status()

    return response.json()


# ============================================================
# MINIO
# ============================================================

s3_client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=username,
    aws_secret_access_key=password,
    config=Config(signature_version="s3v4")
)


def save_raw_data(data, object_key, bucket_name):
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=json.dumps(
                data,
                ensure_ascii=False,
                indent=4
            ),
            ContentType="application/json"
        )

        print(
            f"Successfully uploaded raw data to "
            f"MinIO: s3://{bucket_name}/{object_key}"
        )

    except Exception as e:
        print(f"Error uploading to MinIO: {e}")


# ============================================================
# MAIN
# ============================================================

bucket_name = "weather-data"

cities = [
    "Katerini",
    "Thessaloniki",
    "Athens"
]


now = datetime.now()

year = now.strftime("%Y")
month = now.strftime("%m")
day = now.strftime("%d")
timestamp = now.strftime("%H%M%S")


for city in cities:

    object_key = (
        f"bronze/current_weather/"
        f"city={city}/"
        f"year={year}/"
        f"month={month}/"
        f"day={day}/"
        f"{timestamp}.json"
    )

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}"
        f"&appid={API}"
        f"&units=metric"
        f"&lang=el"
    )

    print(f"Getting weather data for {city}...")

    data = get_weather(url)

    save_raw_data(
        data=data,
        object_key=object_key,
        bucket_name=bucket_name
    )
