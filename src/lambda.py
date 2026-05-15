import json
import logging
import os

import numpy as np

logger = logging.getLogger()
logger.setLevel(logging.INFO)

THRESHOLD = float(os.environ.get('ANOMALY_THRESHOLD', 3.0))


def detect_anomalies(data_points):
    mean = np.mean(data_points)
    std_dev = np.std(data_points)
    if std_dev == 0: return []

    anomalies = []
    for val in data_points:
        z_score = abs((val - mean) / std_dev)
        if z_score > THRESHOLD:
            anomalies.append({"value": val, "z_score": round(float(z_score), 2)})
    return anomalies


def lambda_handler(event, context):
    try:
        # API Gateway passes payload as a JSON string inside the 'body' key
        body = json.loads(event.get('body', '{}'))
        payload = body.get('sensor_readings', [])

        if not payload:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'No sensor_readings provided'})
            }

        results = detect_anomalies(payload)
        message = "Anomalies detected" if len(results) > 0 else "All data normal"

        # API Gateway requires this exact output format
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # Enables CORS for testing
            },
            'body': json.dumps({
                'message': message,
                'anomalies': results,
                'meta': {'points_processed': len(payload)}
            })
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }
