# Lumentree Solar Guard Documentation

## Features
- **24/7 Real-Time Telemetry**: Connects directly to Lumentree MQTT Broker and pushes live sensor metrics (`sensor.lumentree_pv1_power`, `sensor.lumentree_pv1_voltage`, `sensor.lumentree_pv1_current`, `sensor.lumentree_grid_power`, `sensor.lumentree_home_load`) to Home Assistant REST API.
- **Fault Detection & Alerts**: Automatically alerts mobile app when PV power drops to 0W continuously.
- **IR Air Conditioner Control**: Controls IR climate devices based on solar production and EVN grid consumption.

## Configuration Options
- `device_id`: Your Lumentree Inverter serial number / device ID (e.g. `H250521206`).
- `ha_url`: Home Assistant internal API endpoint (default: `http://supervisor/core`).
- `mqtt_broker`: Lumentree cloud MQTT broker address.
- `mqtt_port`: Lumentree cloud MQTT port (8083).
