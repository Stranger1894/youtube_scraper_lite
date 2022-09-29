from flask import Flask, render_template, request
from flask_cors import cross_origin
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import re
import json
import os
import isodate
import time
import concurrent.futures

app = Flask(__name__)


@app.route('/', methods=['GET'])  # route to display the home page
@cross_origin()
def homePage():
    return render_template("index.html")


@app.route('/review', methods=['POST', 'GET'])  # route to show the review comments in a web UI
@cross_origin()
def index():
    if request.method == 'POST':

        api_key = os.environ.get("API_KEY")

        url = request.form['content']
        count = request.form['vid_count']
        soup = BeautifulSoup(requests.get(url).content, "html.parser")
        data = re.search(r"var ytInitialData = ({.*});", str(soup.prettify())).group(1)
        json_data = json.loads(data)

        channel_id = json_data['header']['c4TabbedHeaderRenderer']['channelId']

        youtube = build('youtube', 'v3', developerKey=api_key)

        def get_playlist_id(youtube, channel_id):
            try:
                request = youtube.channels().list(
                    part='snippet,content_details',
                    id=channel_id
                )
                response = request.execute()

                playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                channelname = response['items'][0]['snippet']['title']

                return playlist_id, channelname

            except Exception as e:
                print("Unable to get playlist, Error:", e)

        playlist_id = get_playlist_id(youtube, channel_id)[0]
        channelname = get_playlist_id(youtube, channel_id)[1]

        def get_video_ids(youtube, playlist_id):
            try:
                request = youtube.playlistItems().list(
                    part='contentDetails',
                    playlistId=playlist_id,
                    maxResults=count)

                response = request.execute()

                video_ids = []

                for i in range(len(response['items'])):
                    video_ids.append(response['items'][i]['contentDetails']['videoId'])

                return video_ids

            except Exception as e:
                print("Unable to get video IDs, Error:" , e)

        video_ids = get_video_ids(youtube, playlist_id)

        def get_video_data(youtube, video_ids):
            try:
                request = youtube.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=",".join(video_ids))

                response = request.execute()

                all_video_details = []

                for video in response['items']:
                    video_details = dict(channelname=channelname,
                                         video_link='https://www.youtube.com/watch?v=' + str(video['id']),
                                         publish_date=datetime.strptime(str(video['snippet']["publishedAt"]),'%Y-%m-%dT%H:%M:%SZ'),
                                         #2022-09-25T14:00:01Z - date format from Youtube API
                                         duration=isodate.parse_duration(video['contentDetails']["duration"]).total_seconds(),
                                         view_count=video['statistics']["viewCount"],
                                         likes_count=video['statistics']["likeCount"],
                                         comments_count=video['statistics']["commentCount"],
                                         video_title=video['snippet']["title"],
                                         thumbnail_url=video['snippet']["thumbnails"]['high']['url']
                                         )

                    all_video_details.append(video_details)

                return all_video_details

            except Exception as e:
                print("Unable to process video data, Error:" , e)

        channel_video_data = get_video_data(youtube, video_ids)

        #with concurrent.futures.ThreadPoolExecutor() as executor:
            #results = executor.map(download_and_upload_videos, video_ids)

        return render_template('results.html', channel_video_data=channel_video_data[0:(len(channel_video_data))])


if __name__ == "__main__":
    app.run()
