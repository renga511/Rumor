"""
AI Rumor Propagation Simulator - Flask Backend
Main application entry point
"""
from flask import Flask, render_template, request, jsonify, send_file
import json, random, time, io, os
from modules.fact_checker import analyze_rumor
from modules.news_feed import get_india_news, get_world_news
from modules.network_sim import generate_network_data, simulate_step_data
from modules.pdf_export import generate_pdf_report

app = Flask(__name__)

# ─── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/fact-check", methods=["POST"])
def fact_check():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    result = analyze_rumor(text)
    return jsonify(result)

@app.route("/api/news/india")
def india_news():
    return jsonify(get_india_news())

@app.route("/api/news/world")
def world_news():
    return jsonify(get_world_news())

@app.route("/api/network/generate", methods=["POST"])
def generate_network():
    data = request.get_json()
    n_nodes = int(data.get("n_nodes", 500))
    net_type = data.get("net_type", "Scale-Free (BA)")
    return jsonify(generate_network_data(net_type, n_nodes))

@app.route("/api/network/simulate", methods=["POST"])
def simulate_network():
    data = request.get_json()
    step = data.get("step", 0)
    beta = float(data.get("beta", 0.15))
    gamma = float(data.get("gamma", 0.05))
    beta_truth = float(data.get("beta_truth", 0.20))
    states = data.get("states", [])
    edges = data.get("edges", [])
    strategy = data.get("strategy", "None")
    intervene_step = int(data.get("intervene_step", 15))
    is_true_news = data.get("is_true_news", False)
    return jsonify(simulate_step_data(states, edges, beta, gamma, beta_truth, step, strategy, intervene_step, is_true_news))

@app.route("/api/export/pdf", methods=["POST"])
def export_pdf():
    data = request.get_json()
    pdf_bytes = generate_pdf_report(data)
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name="rumor_analysis_report.pdf")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
