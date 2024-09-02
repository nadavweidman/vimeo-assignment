from flask import Flask, request, jsonify, g
import mysql.connector
import os
import time
from mysql.connector import Error


DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']


app = Flask(__name__)


def get_db():
    if 'db' not in g:
        retries = 5
        while retries > 0:
            try:
                g.db = mysql.connector.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME
                )
                return g.db
            except Error as e:
                print(f"Error connecting to MySQL: {e}")
                time.sleep(5)  # Wait before retrying
                retries -= 1
        raise RuntimeError("Unable to connect to the MySQL server after multiple attempts")

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS videos (
                            id VARCHAR(255) PRIMARY KEY, 
                            title VARCHAR(255) NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS views (
                            video_id VARCHAR(255), 
                            view_count INT,
                            FOREIGN KEY(video_id) REFERENCES videos(id))''')
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/upload', methods=['POST'])
def upload_video():
    video_id = request.form.get('video_id')
    video_title = request.form.get('title')
    
    if not video_id or not video_title:
        return jsonify({"error": "Video ID and title are required"}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO videos (id, title) VALUES (%s, %s)", (video_id, video_title))
    cursor.execute("INSERT INTO views (video_id, view_count) VALUES (%s, %s)", (video_id, 0))
    db.commit()
    
    return jsonify({"message": "Video uploaded successfully", "video_id": video_id}), 201

@app.route('/view/<video_id>', methods=['POST'])
def view_video(video_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT title FROM videos WHERE id = %s", (video_id,))
    video = cursor.fetchone()
    
    if video is None:
        return jsonify({"error": "Video not found"}), 404
    
    cursor.execute("UPDATE views SET view_count = view_count + 1 WHERE video_id = %s", (video_id,))
    db.commit()
    
    cursor.execute("SELECT view_count FROM views WHERE video_id = %s", (video_id,))
    view_count = cursor.fetchone()[0]
    
    return jsonify({"message": f"Video '{video[0]}' viewed", "views": view_count}), 200

@app.route('/videos', methods=['GET'])
def list_videos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM videos")
    videos = cursor.fetchall()
    return jsonify(videos), 200

@app.route('/views/<video_id>', methods=['GET'])
def get_views(video_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT view_count FROM views WHERE video_id = %s", (video_id,))
    view = cursor.fetchone()
    
    if view is None:
        return jsonify({"error": "Video not found"}), 404
    
    return jsonify({"video_id": video_id, "views": view[0]}), 200

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5005)