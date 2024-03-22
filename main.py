import uvicorn
import pandas as pd
import hashlib
from keplergl import KeplerGl
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List
import logging
import json

poly = [
    [13.534254900484356, 59.36163702557852],
    [13.553743899236425, 59.35326638347115],
    [13.545203776187767, 59.33897571908756],
    [13.523962957323153, 59.3386407095081],
    [13.529875350202992, 59.34902447016282],
    [13.523525002295015, 59.3541593503185],
    [13.534254900484356, 59.36163702557852],
]

initial_data = {
    "example_dataset_id": [{"x": point[0], "y": point[1]} for point in poly]
}

# Define a Pydantic model for the incoming data
class Point(BaseModel):
    x: float = Field(..., example=13.534254900484356)
    y: float = Field(..., example=59.36163702557852)

class Points(BaseModel):
    points: List[Point]

class DatasetManager:
    def __init__(self):
        self.datasets = {}

    def initialize_datasets(self, initial_data):
        for dataset_id, data in initial_data.items():
            self.update_dataset(dataset_id, data)

    def update_dataset(self, dataset_id, data):
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        if dataset_id not in self.datasets or self.datasets[dataset_id]['hash'] != data_hash:
            self.datasets[dataset_id] = {'hash': data_hash, 'data': data}
            return True  # Indicates that the dataset was updated
        return False  # No update needed

    def get_dataset_hash(self, dataset_id):
        return self.datasets[dataset_id]['hash'] if dataset_id in self.datasets else None

    def get_dataset(self, dataset_id):
        return self.datasets[dataset_id]['data'] if dataset_id in self.datasets else None

class ConnectionManager:
    def __init__(self,initial_data):
        self.active_connections = []
        self.dataset_manager = DatasetManager()
        self.dataset_manager.initialize_datasets(initial_data)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        logging.info(f"Disconnecting {websocket.client}")
        self.active_connections.remove(websocket)

    async def broadcast(self, dataset_id):
        server_hash = self.dataset_manager.get_dataset_hash(dataset_id)
        data = self.dataset_manager.get_dataset(dataset_id)
        message = {
            "type": "update",
            "dataset_id": dataset_id,
            "hash": server_hash,
            "data": data
        }
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                logging.info(f"Successfully sent message to {connection.client}: {message}")
            except Exception as e:
                logging.error(f"Failed to send message to {connection.client}: {e}")
                traceback.print_exc()  # This prints the stack trace to the log

    async def send_update_if_needed(self, websocket: WebSocket, dataset_id):
        client_hash = websocket.query_params.get("hash")
        server_hash = self.dataset_manager.get_dataset_hash(dataset_id)

        try:
            if client_hash != server_hash:

                logging.info(f"Update sent to {websocket.client} for dataset {dataset_id}")
        except Exception as e:
            logging.error(f"Error sending update to {websocket.client} for dataset {dataset_id}: {e}")
            traceback.print_exc()

app = FastAPI()
kepler = KeplerGl()
manager = ConnectionManager(initial_data=initial_data)

@app.websocket("/ws/{dataset_id}")
async def websocket_endpoint(websocket: WebSocket, dataset_id: str):
    await manager.connect(websocket)
    try:
        await manager.send_update_if_needed(websocket, dataset_id)
        while True:
            # Keeping the connection alive, waiting for any possible messages from the client
            data = await websocket.receive_text()
            logging.info(f"Received message from {websocket.client}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logging.info(f"WebSocket disconnected: {websocket.client}")

@app.get("/", response_class=HTMLResponse)
async def index():

    kepler_html_raw = kepler._repr_html_()
    logging.info(f"Type of kepler_html_raw: {type(kepler_html_raw)}")

    # Check if kepler_html_raw is bytes and decode if necessary
    if isinstance(kepler_html_raw, bytes):
        kepler_html_str = kepler_html_raw.decode('utf-8')
        logging.info("Decoded kepler_html_raw from bytes to str.")
    else:
        kepler_html_str = kepler_html_raw
        logging.info("kepler_html_raw is already a str.")

    datasets = [
        {"id": "example_dataset_id", "hash": "initial_hash_1"},
        {"id": "dataset2", "hash": "initial_hash_2"}
    ]

    websocket_script = """
    <script>
        var datasets = """ + str(datasets) + """;
        datasets.forEach(dataset => {
            let ws = new WebSocket(`ws://localhost:8000/ws/${dataset.id}?hash=${dataset.hash}`);

            ws.onopen = function(event) {
                console.log(`WebSocket for ${dataset.id} is open now.`);
            };
            ws.onclose = function(event) {
                console.error(`WebSocket closed for ${dataset.id} with code ${event.code}`);
            };
            ws.onmessage = function(event) {
                console.log('Received message from server:', event.data); // Debug print the entire message data
                const message = JSON.parse(event.data);
                console.log('Parsed message:', message); // Debug print the parsed message object
                if (message.type === "update" && message.dataset_id === dataset.id) {
                    console.log(`Updating map with new data for ${message.datasetId}:`, message.data);
                    dataset.hash = message.hash;  // Update the hash to the latest
                    // Call your function to update the visualization
                    updateMapWithData(dataset.id, message.data);
                }
            };

            ws.onerror = function(error) {
                console.log(`WebSocket error for ${dataset.id}: `, error);
            };
        });

        function updateMapWithData(datasetId, data) {
            console.log(`Updating map with new data for ${datasetId}:`, data);
            if (!data || data.length === 0) {
                 console.error(`Received empty or invalid data for dataset ${datasetId}`);
                 return;
            }
            console.log(`Received expected data for dataset ${datasetId}`);
        // Proceed with updating the map visualization...
        }

    </script>
    """

    combined_html = kepler_html_str + websocket_script
    return HTMLResponse(content=combined_html, status_code=200)

@app.post("/update_data/{dataset_id}")
async def update_data(dataset_id: str, points: Points):
    data = points.dict()
    if manager.dataset_manager.update_dataset(dataset_id, data):
        # Correctly passing dataset_id as a string
        await manager.broadcast(dataset_id)
    return {"message": "Data checked and updated if necessary"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
