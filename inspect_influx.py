from influxdb_client import InfluxDBClient
import sys

# Force stdout to flush
sys.stdout.reconfigure(encoding='utf-8')

MONITOR_URL = "http://1.94.121.255:8086"
MONITOR_TOKEN = "K-xsdqIdqS0CaEl2cj2nHqGmgXv6A6EjQ7TuZhHd6d15Ns9LqNYsVveX9lJzob7LT-Q0pfylKpiXdDbPEy87JQ=="
MONITOR_BUCKET = "energy"
MONITOR_ORG = "fengtian"

def run():
    client = InfluxDBClient(url=MONITOR_URL, token=MONITOR_TOKEN, org=MONITOR_ORG)
    query_api = client.query_api()

    print("\n=== TAG KEYS ===")
    try:
        query = f'import "influxdata/influxdb/schema"\n schema.tagKeys(bucket: "{MONITOR_BUCKET}")'
        tables = query_api.query(query)
        keys = set()
        for table in tables:
            for record in table.records:
                keys.add(record.get_value())
        
        sorted_keys = sorted(list(keys))
        print(f"Found keys: {sorted_keys}")
        
        # Check likely candidates for Device ID
        candidates = ['device', 'gatewayId', 'machine', 'host', 'client_id', 'topic', 'dev_id']
        for key in sorted_keys:
            if key in candidates or 'id' in key.lower():
                print(f"\n--- Values for tag '{key}' ---")
                q_vals = f'''
                import "influxdata/influxdb/schema"
                schema.tagValues(bucket: "{MONITOR_BUCKET}", tag: "{key}")
                '''
                val_tables = query_api.query(q_vals)
                for vt in val_tables:
                    for vr in vt.records:
                        print(f"  - {vr.get_value()}")

    except Exception as e:
        print(f"Error querying tags: {e}")

if __name__ == '__main__':
    run()
