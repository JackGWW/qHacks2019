# system imports
import threading
import os
import sys
import subprocess as sp

# local imports
import video
import audioStream

# 3rd party imports
from flask import Flask, Response, render_template
from flask_bootstrap import Bootstrap

app = Flask(__name__)
bootstrap = Bootstrap(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/init', methods=['POST'])
def init():
	# launch threads
	print("Launching threads")
	return "Launched Threads"


@app.route('/start', methods=['POST'])
def start():
    # tell threads to start sending new data
    
	print("Starting processing")
	return "Started processing"


@app.route('/stop', methods=['POST'])
def stop():
	# tell threads to stop sending data
	print("Stopping processing")
	return "Stopped processing"


@app.route('/video_stream')
def video_stream():
	# Create video stream 
	return Response(video.main(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True, threaded=False)
 