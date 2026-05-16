import json
import logging
import os
from datetime import datetime
import boto3
import numpy as np

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the S3 client
s3 = boto3.client('s3')
BUCKET_NAME = 'learning-bucket-878065947172-eu-north-1-an'
THRESHOLD = float(os.environ.get('ANOMALY_THRESHOLD', 3.0))


def detect_anomalies(data_points):
    mean = np.mean(data_points)
    std_dev = np.std(data_points)
    if std_dev == 0: return []

    anomalies = []
    for val in data_points:
        z_score = abs((val - mean) / std_dev)
        if z_score > THRESHOLD:
            # Explicitly cast to standard float to avoid JSON serialization errors with NumPy types
            anomalies.append({
                "value": float(val),
                "z_score": round(float(z_score), 2)
            })
    return anomalies


def save_to_s3(data_points, anomalies):
    """Formats the data into a CSV and uploads it to the S3 bucket."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Create a quick lookup for values flagged as anomalies
    anomaly_values = {a["value"] for a in anomalies}

    # Construct CSV structure
    csv_lines = ["timestamp,sensor_reading,is_anomaly"]
    for val in data_points:
        is_anom = "True" if val in anomaly_values else "False"
        csv_lines.append(f"{timestamp},{val},{is_anom}")

    csv_content = "\n".join(csv_lines)

    # Generate a unique timestamp-based filename
    file_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    s3_key = f"readings/batch_{file_id}.csv"

    # Upload directly to the bucket
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
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'No sensor_readings provided'})
            }

        # 1. Run your existing Z-Score calculation
        results = detect_anomalies(payload)

        # 2. Write the batch data to S3 as a CSV file
        s3_path = save_to_s3(payload, results)

        message = f"Anomalies evaluated. File saved to S3: {s3_path}"

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': message,
                'anomalies': results,
                'meta': {
                    'points_processed': len(payload),
                    's3_storage_key': s3_path
                }
            })
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
