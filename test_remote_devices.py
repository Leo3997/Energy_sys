from influxdb_client import InfluxDBClient

MONITOR_URL = "http://1.94.121.255:8086"
MONITOR_TOKEN = "K-xsdqIdqS0CaEl2cj2nHqGmgXv6A6EjQ7TuZhHd6d15Ns9LqNYsVveX9lJzob7LT-Q0pfylKpiXdDbPEy87JQ=="
MONITOR_BUCKET = "energy"
MONITOR_ORG = "fengtian"

print("Testing remote InfluxDB connection...")
print(f"URL: {MONITOR_URL}")
print(f"ORG: {MONITOR_ORG}")
print(f"BUCKET: {MONITOR_BUCKET}")
print()

try:
    client = InfluxDBClient(url=MONITOR_URL, token=MONITOR_TOKEN, org=MONITOR_ORG)
    query_api = client.query_api()
    
    # Test query for 'device' tag
    print("Querying tag values for 'device'...")
    query = f'import "influxdata/influxdb/schema"\n schema.tagValues(bucket: "{MONITOR_BUCKET}", tag: "device")'
    
    print(f"Query: {query}")
    print()
    
    tables = query_api.query(query)
    devices = []
    for table in tables:
        for record in table.records:
            val = record.get_value()
            if val:
                devices.append(val)
                print(f"  Found: {val}")
    
    print()
    print(f"Total devices found: {len(devices)}")
    
    if len(devices) == 0:
        print("\nNo devices found. Let's check available tags...")
        tag_query = f'import "influxdata/influxdb/schema"\n schema.tagKeys(bucket: "{MONITOR_BUCKET}")'
        tag_tables = query_api.query(tag_query)
        
        print("Available tags in bucket:")
        for table in tag_tables:
            for record in table.records:
                print(f"  - {record.get_value()}")
    
    client.close()
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
