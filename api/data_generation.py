from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import csv
import random
import json
from faker import Faker
import time
import os
from threading import Thread

fake = Faker()

app = FastAPI()

#CORS (Cross origin resource sharing) middleware to allow requests from the react app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  #react app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fake_functions = {
    'timestamp': lambda: fake.date_time_this_decade().isoformat(),
    'user_id': lambda: random.randint(1000, 9999),
    'application_type': lambda: fake.word(ext_word_list=["Browsing", "Streaming", "Gaming"]),
    'signal_strength': lambda: random.randint(-100, -50),
    'latency': lambda: random.randint(10, 100),
    'required_bandwidth': lambda: random.randint(1, 10),
    'allocated_bandwidth': lambda: random.randint(1, 10),
    'resource_allocation': lambda: random.randint(0, 100),
}

#Function used to generate data based on the JSON schema
def generate_data(schema, num_records):
    if isinstance(schema, list):
        schema = schema[0] if schema else {}
    
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary")

    data = []
    for _ in range(num_records):
        row = generate_record(schema)
        data.append(row)
    return data

def generate_record(schema):
    row = {}
    for column, field_type in schema.items():
        if field_type in fake_functions:
            row[column] = fake_functions[field_type]()
        else:
            raise ValueError(f"Unknown field type '{field_type}' in schema for column '{column}'")
    return row

def save_to_csv(data, output_file):
    if data:
        fieldnames = data[0].keys()
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    else:
        raise ValueError("No data to save.")

def continuous_generation(schema, num_records, interval, output_file):
    while True:
        data = generate_data(schema, num_records)
        save_to_csv(data, output_file)
        time.sleep(interval)

@app.post("/generate-csv")
async def generate_csv(file: UploadFile = File(...), num_records: int = Form(...), interval: float = Form(...), mode: str = Form(...), custom_filename: str = Form(default="output")):
    try:
        schema_data = await file.read()
        print("Received schema data:", schema_data)

        try:
            schema = json.loads(schema_data)
            print("Parsed schema:", schema)
        except json.JSONDecodeError as e:
            print("JSON decode error:", e)
            raise HTTPException(status_code=400, detail="Invalid JSON file.")

        # Check that directory exists
        os.makedirs('generated_files', exist_ok=True)

        # Naming convention for the generated CSV file
        output_file = f"generated_files/{custom_filename}.csv"
        print(f"Output file path: {output_file}")

        if mode == "batch":
            print("Generating data in batch mode")
            data = generate_data(schema, num_records)
            save_to_csv(data, output_file)
            print("CSV generated successfully")
            return {
                "message": "CSV generated successfully!",
                "output_file": output_file.split('/')[-1]  # Only send the filename
            }
        elif mode == "stream":
            print("Starting CSV generation in streaming mode")
            # Start continuous generation in a background thread
            # ... existing code ...
            return {
                "message": "CSV generation started in streaming mode!",
                "output_file": output_file.split('/')[-1]  # Only send the filename
            }
        else:
            print("Invalid mode:", mode)
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'batch' or 'stream'.")
    except Exception as e:
        print("Error during CSV generation:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download_csv/")
async def download_csv(filename: str):
    file_path = f"generated_files/{filename}" 
    print(f"Attempting to download file at: {file_path}")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='text/csv', filename=filename)
    print("File not found.")
    return {"error": "File not found."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


#Command to to run 'uvicorn app.main:app --reload'
