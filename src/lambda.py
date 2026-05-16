import json
import logging
import os
from datetime import datetime
import boto3
import numpy as np

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
BUCKET_NAME = 'learning-bucket-878065947172-eu-north-1-an'
THRESHOLD = float(os.environ.get('ANOMALY_THRESHOLD', 3.0))


def detect_anomalies(data_points):
    # 1. Force the input points into a standard numpy array, but strictly cast results to Python native floats
    np_points = np.array(data_points, dtype=float)
    mean = float(np.mean(np_points))
    std_dev = float(np.std(np_points))

    if std_dev == 0: return []

    anomalies = []
    for val in data_points:
        # Convert val explicitly to a standard Python float
        native_val = float(val)
        z_score = abs((native_val - mean) / std_dev)
        if z_score > THRESHOLD:
            anomalies.append({
                "value": native_val,
                "z_score": round(float(z_score), 2)
            })
    return anomalies


def save_to_s3(data_points, anomalies):
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    anomaly_values = {a["value"] for a in anomalies}

    csv_lines = ["timestamp,sensor_reading,is_anomaly"]
    for val in data_points:
        native_val = float(val)  # Force native conversion for the CSV string string format
        is_anom = "True" if native_val in anomaly_values else "False"
        csv_lines.append(f"{timestamp},{native_val},{is_anom}")

    csv_content = "\n".join(csv_lines)
    file_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    s3_key = f"readings/batch_{file_id}.csv"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=csv_content,
        ContentType='text/csv'
    )
    return s3_key


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        payload = body.get('sensor_readings', [])

        if not payload:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'No sensor_readings provided'})
            }

        # Clean any nested numpy types inside raw payload data items immediately
        clean_payload = [float(x) for x in payload]

        results = detect_anomalies(clean_payload)
        s3_path = save_to_s3(clean_payload, results)
        message = f"Anomalies evaluated. File saved to S3: {s3_path}"

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            },
            'body': json.dumps({
                'message': message,
                'anomalies': results,
                'meta': {
                    'points_processed': len(clean_payload),
                    's3_storage_key': s3_path
                }
            })
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
