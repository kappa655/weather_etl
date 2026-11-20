import pandas as pd
import json
from io import BytesIO
from datetime import datetime, timedelta, timezone
import boto3
from botocore.client import Config
from dotenv import load_dotenv
import os


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

endpoint = os.getenv("endpoint")
username = os.getenv("username")
password = os.getenv("password")


# ============================================================
# MINIO CLIENT
# ============================================================

s3_client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=username,
    aws_secret_access_key=password,
    config=Config(signature_version="s3v4")
)


bucket_name = "weather-data"


# ============================================================
# READ JSON FROM MINIO
# ============================================================

def read_json_from_minio(object_key, bucket_name):

    response = s3_client.get_object(
        Bucket=bucket_name,
        Key=object_key
    )

    data = json.loads(
        response["Body"].read().decode("utf-8")
    )

    return data


# ============================================================
# RENAME COLUMNS
# ============================================================

def rename_cols(df):

    df = df.rename(
        columns={
            "wind.speed": "wind_speed",
            "wind.deg": "wind_deg",
            "wind.gust": "wind_gust",
            "clouds.all": "cloud_pct",
            "rain.1h": "hourly_rain"
        }
    )

    return df


# ============================================================
# TRANSFORM JSON → DATAFRAME
# ============================================================

def json_to_csv(data):

    # Main weather data
    data_main = pd.json_normalize(data)

    # Weather array
    data_weather = pd.json_normalize(
        data,
        record_path=["weather"]
    )

    # Join
    data_final = data_weather.join(
        data_main,
        how="left",
        lsuffix="_weather"
    )

    # Remove unnecessary column
    if "weather" in data_final.columns:
        data_final = data_final.drop(
            columns=["weather"]
        )

    # Rename columns
    data_final = rename_cols(data_final)

    # Remove dots from column names
    data_final.columns = [
        col.split(".")[-1]
        for col in data_final.columns
    ]

    return data_final


# ============================================================
# DATETIME TRANSFORMATION
# ============================================================

def add_readable_time(data):

    local_tz = timezone(
        timedelta(seconds=data["timezone"])
    )

    data["datetime"] = datetime.fromtimestamp(
        data["dt"],
        tz=local_tz
    )

    data["sunrise"] = datetime.fromtimestamp(
        data["sunrise"],
        tz=local_tz
    )

    data["sunset"] = datetime.fromtimestamp(
        data["sunset"],
        tz=local_tz
    )

    return data

def save_csv(df, object_key, bucket_name):
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=df.encode("utf-8"),
            ContentType="text/csv"
        )

        print(
            f"Successfully uploaded CSV to "
            f"MinIO: s3://{bucket_name}/{object_key}"
        )

    except Exception as e:
        print(f"Error uploading CSV to MinIO: {e}")

now = datetime.now()

year = now.strftime("%Y")
month = now.strftime("%m")
day = now.strftime("%d")
timestamp = now.strftime("%H%M%S")


response = s3_client.list_objects_v2(Bucket = "weather-data", Prefix = "bronze/current_weather/")
for file in response["Contents"]:
    object_key = file["Key"]
    splits = object_key.split("/")
    splits = splits[2].split("=")
    city = splits[-1]
    data = read_json_from_minio(object_key=object_key, bucket_name=bucket_name)
    data = json_to_csv(data)
    data = add_readable_time(data)
    object_key = (
        f"silver/current_weather/"
        f"city={city}/"
        f"year={year}/"
        f"month={month}/"
        f"day={day}/"
        f"{timestamp}.json"
    )
    save_csv(data, object_key, bucket_name)