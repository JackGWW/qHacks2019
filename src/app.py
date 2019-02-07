# system imports
import os
import sys
import subprocess as sp
import threading
import random
import queue
import time

# local imports
import video
import audioStream

# 3rd party imports
from flask import Flask, Response, render_template, request, jsonify
from flask_bootstrap import Bootstrap

# Disable flask logs
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
bootstrap = Bootstrap(app)

WPM = 0
TRANSCRIPT = ''
CRUTCH_WORDS = ['like', ' so', ' you know', 'basically', ' cuz', 'things', 'stuff', 'yeah']
crutch = {}
for word in CRUTCH_WORDS:
    CRUTCH[word] = 0
movement = 0

def audio_thread():
	# Poll audio generator every 0.2 seconds for updated values
    time.sleep(5)
    print("Starting Processing Audio")
    ag = audioStream.AudioGenerator()  # slow background task Thread
    ag.start_stream()
    global WPM
    global TRANSCRIPT
    global CRUTCH
    while ag.is_alive():  # While the thread is running
        WPM = ag.get_wpm()
        CRUTCH = ag.get_crutch()
        TRANSCRIPT = ag.get_transcript()
        print("WPM:{}  Transcript:{}".format(WPM, TRANSCRIPT))
        time.sleep(0.2)


@app.route('/api/wpm')
def get_wpm():
    global WPM
    return jsonify({'wpm':WPM})


@app.route('/api/transcript')
def get_transcript():
    global TRANSCRIPT
    return jsonify({'transcript': TRANSCRIPT})


@app.route('/api/crutch')
def get_crutch():
    global CRUTCH
    return jsonify({'crutch': CRUTCH})


@app.route('/api/movement')
def get_movement():
    movement = random.randint(0, 100)
    return jsonify({'movement':movement})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/init', methods=['POST'])
def init():
    # launch threads
    at = threading.Thread(target=audio_thread)
    if not at.isAlive():
        at.start()
        print("Startng Audio Thread")

    return "Launched Threads"


@app.route('/current')
def current():
    return 'Done'


# @app.route('/video_stream')
# def video_stream():
#     # Create video stream 
#     return Response(video.main(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    init()
    app.run(debug=False)
