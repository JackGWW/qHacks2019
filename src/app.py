from flask import Flask, Response, render_template
from flask_bootstrap import Bootstrap
import video

app = Flask(__name__)
bootstrap = Bootstrap(app)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_stream')
def video_stream():
	return Response(video.main(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True)
 