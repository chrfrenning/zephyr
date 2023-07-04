from flask import Flask, jsonify, request, abort, send_file, render_template

import os
import json
import copy
import uuid
import subprocess
import numpy as np
from datetime import datetime

app = Flask(__name__)

@app.route("/api")
def api():
    json = {
        "application": "zephyr/1.0",
        "version": "1.0",
        "api": {
            "matrix": {
                "endpoint": "/api/matrix",
                "method": "GET",
                "format": "json",
                "help": "Returns a random matrix."
            }
        }
    }
    return jsonify(json)

@app.route("/api/matrix", methods=["GET", "POST"])
def matrix():
   # create a random matrix with numpy and return in json format
    matrix = np.random.rand(30,30).tolist()
    return jsonify(matrix)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug = True, host = "0.0.0.0", port = 3000)