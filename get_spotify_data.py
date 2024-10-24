import requests
import os
import base64
import json
import logging
from collections import Counter
import numpy as np
import pandas as pd
from get_1001_data import get_albums
from ratelimit import limits, sleep_and_retry
from datetime import timedelta

logging.basicConfig(level=logging.INFO, filename='spotify_requests.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
project_id = os.getenv('PROJECT_ID')


@sleep_and_retry
@limits(calls=100, period=timedelta(seconds=31).total_seconds())
def spotify_request(url):
    result = requests.get(url, headers=headers)
    if result.status_code == 200:
        json_result = json.loads(result.content)
        return json_result
    logging.error(f"Failed request to {url}: {result.status_code} - {result.text}")
    return None


def get_token():
    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    token_headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = requests.post(url, headers=token_headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token


def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def safe_divide(numerator, denominator):
    if denominator == 0 or np.isnan(denominator):
        return np.nan
    else:
        return numerator / denominator


def get_track_ids(album_id):
    try:
        url = f'https://api.spotify.com/v1/albums/{album_id}/tracks?market=US&limit=50'
        json_result = spotify_request(url)
        if json_result:
            json_result = json_result['items']
            track_ids = [track['id'] for track in json_result]
            return track_ids
        else:
            return None
    except Exception as e:
        logging.error(f"Failed to get track IDs for album {album_id}: {e}")
        return []


def get_album_info(album_id):
    try:
        url = f'https://api.spotify.com/v1/albums/{album_id}?market=US'
        json_result = spotify_request(url)
        if json_result:
            gen_info = {'release_date': json_result['release_date'],
                        'release_date_precision': json_result['release_date_precision'],
                        'popularity': json_result['popularity']}
            return gen_info
        return None
    except Exception as e:
        logging.error(f"Failed to get album info for album {album_id}: {e}")
        return None


def get_album_features(album_id, gen_info):
    try:
        track_ids = get_track_ids(album_id)
        track_ids_str = '%2C'.join(track_ids)
        url = f'https://api.spotify.com/v1/audio-features?ids={track_ids_str}'
        json_result = spotify_request(url)
        if json_result:
            return get_res(json_result['audio_features'], gen_info)
        return gen_info
    except Exception as e:
        logging.error(f"Failed to get album features for album {album_id}: {e}")
        return gen_info


def get_res(data, gen_info):
    track_amount = len(data)
    if any(item is None for item in data):
        data = [item for item in data if item is not None]
    features_float = ['danceability', 'energy', 'loudness', 'speechiness', 'acousticness', 'instrumentalness',
                      'liveness', 'valence', 'tempo']
    features_int = ['key', 'time_signature']
    weighted_avgs = {}
    total_duration = sum(track['duration_ms'] for track in data)

    for feature in features_float:
        weighted_avgs[f'{feature}_weighted_avg'] = sum(
            track[feature] * track['duration_ms'] for track in data) / total_duration

    difference_coefficients = {
        f'{feature}_difference': safe_divide(
            np.std([track[feature] for track in data if feature in track]),
            weighted_avgs[f'{feature}_weighted_avg']
        )
        for feature in features_float
    }

    res = {**gen_info, **weighted_avgs, **difference_coefficients,
           'mode_0': sum(track['duration_ms'] for track in data if track['mode'] == 0) / total_duration,
           'mode_1': sum(track['duration_ms'] for track in data if track['mode'] == 1) / total_duration}

    for feature in features_int:
        most_common = Counter(track[feature] for track in data).most_common(1)[0]
        res[f'pop_{feature}'] = most_common[0]
        res[f'pop_{feature}_used'] = most_common[1] / track_amount

    res['duration'] = total_duration
    res['track_amount'] = track_amount
    return res


def get_spotify_data(albums):
    res = []

    for i, album in enumerate(albums):
        if i % 50 == 0:
            logging.info(f"parsed {i}/{len(albums)}")
        album_id = album['spotify_id']
        album_info = get_album_info(album_id)
        if album_info:
            album_features = get_album_features(album_id, album_info)
            album_dict = {**album, **album_features}
            res.append(album_dict)
    df = pd.DataFrame(res)
    return df


token = get_token()
headers = get_auth_header(token)
albums = get_albums(project_id)
df = get_spotify_data(albums)
df.to_csv('data\\spotify_data_1001.csv')
