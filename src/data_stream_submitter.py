import random
import time

import requests

# Replace with the actual URL from your AWS API Gateway Trigger
API_URL = "https://0yw9lvflp9.execute-api.eu-north-1.amazonaws.com/default/detect_anomalies"


def generate_sensor_stream():
    """Generates a list of 20 readings. Most are around 50, but includes random spikes."""
    stream = []
    for _ in range(20):
        # 90% chance of normal data (48-52), 10% chance of an anomaly spike (80-100)
        if random.random() > 0.90:
            stream.append(random.uniform(80.0, 100.0))
        else:
            stream.append(random.uniform(48.0, 52.0))
    return stream


def stream_data_to_cloud(iterations=5, delay_seconds=3):
    print(f"Starting data stream simulation to: {API_URL}\n")

    for i in range(iterations):
        readings = generate_sensor_stream()
        payload = {"sensor_readings": readings}

        try:
            print(f"[Batch {i + 1}] Submitting {len(readings)} data points...")
            response = requests.post(API_URL, json=payload)

            if response.status_code == 200:
                result = response.json()
                print(f" Status: Success | Message: {result['message']}")
                if result['anomalies']:
                    print(f" ⚠️ Detected Outliers: {result['anomalies']}")
            else:
                print(f" ❌ Failed with Status Code: {response.status_code}")
                print(f" Response: {response.text}")

        except Exception as e:
            print(f" ❌ Connection Error: {str(e)}")

        print("-" * 50)
        time.sleep(delay_seconds)


if __name__ == "__main__":
    # Ensure you have run 'pip install requests' locally
    stream_data_to_cloud(iterations=5, delay_seconds=2)
