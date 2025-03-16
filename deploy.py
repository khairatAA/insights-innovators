from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
import os

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")

# Load CSV file
data_path = "./ResourceAllocation.csv"
if os.path.exists(data_path):
    df = pd.read_csv(data_path)
else:
    df = pd.DataFrame()

@app.route('/')
def home():
    return render_template("index.html")

# API Endpoint: Query CSV by cell_id
@app.route('/query_csv', methods=['POST'])
def query_csv():
    try:
        cell_id = request.json.get("cell_id", "").strip().lower()
        if not cell_id:
            return jsonify({"error": "No cell_id provided"})

        if df.empty:
            return jsonify({"error": "CSV file is empty or missing"})

        if "cell_id" not in df.columns or "model_prediction" not in df.columns or "Capacity_Allocated(Mbps)" not in df.columns:
            return jsonify({"error": "CSV file does not have the required columns"})

        df["cell_id"] = df["cell_id"].astype(str).str.lower()
        filtered_df = df[df["cell_id"] == cell_id]
        
        if filtered_df.empty:
            return jsonify({"error": "No matching cell_id found"})
        
        latest_entry = filtered_df.sort_values(by="timestamp", ascending=False).iloc[0]
        network_traffic_usage = latest_entry.get("model_prediction", "N/A")
        resource_allocation = latest_entry.get("Capacity_Allocated(Mbps)", "N/A")
        timestamp_label = latest_entry.get("timestamp", "N/A")
        
        response_text = (f"For cell {cell_id}, the predicted network traffic usage is {network_traffic_usage}, "
                         f"and the needed resource allocation for this traffic is {resource_allocation} Mbps.")
        
        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"error": str(e)})

# API Endpoint: Process CSV Upload
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"})
        
        input_df = pd.read_csv(file)
        if "cell_id" not in input_df.columns:
            return jsonify({"error": "CSV must contain a 'cell_id' column"})
        
        input_df["cell_id"] = input_df["cell_id"].astype(str).str.lower()
        df["cell_id"] = df["cell_id"].astype(str).str.lower()
        
        merged_df = input_df.merge(df, on="cell_id", how="left")
        
        # Ensure required columns exist before processing
        if "model_prediction" not in merged_df.columns:
            merged_df["model_prediction"] = "N/A"
        if "Capacity_Allocated(Mbps)" not in merged_df.columns:
            merged_df["Capacity_Allocated(Mbps)"] = "N/A"
        
        # Rename columns
        merged_df.rename(columns={
            "model_prediction": "Network Traffic Usage",
            "Capacity_Allocated(Mbps)": "Resource Allocation (Mbps)",
            "timestamp": "Last Updated"
        }, inplace=True)
        
        # Keep only necessary columns
        result_df = merged_df[["cell_id", "Network Traffic Usage", "Resource Allocation (Mbps)", "Last Updated"]]
        result_df = result_df.sort_values(by="Last Updated", ascending=False).drop_duplicates(subset=["cell_id"])
        
        output_path = "static/Predicted Cells.csv"
        result_df.to_csv(output_path, index=False)
        
        return jsonify({"download_url": f"/{output_path}"})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
