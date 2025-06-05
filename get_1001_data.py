import requests
import os
import logging

logging.basicConfig(level=logging.INFO, filename='spotify_requests.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

project_id = os.getenv('PROJECT_ID')


def get_project_stats(project_id):
    # i used the project_id for the user that rated all albums (found on reddit) to get info about spotify_id
    url = f"https://1001albumsgenerator.com/api/v1/projects/{project_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {'error': 'Failed to fetch data', 'status_code': response.status_code}


def get_albums(project_id):
    project_stats = get_project_stats(project_id)
    albums_data = []
    for alb_dict in project_stats['history']:
        album = alb_dict['album']
        try:
            album_info = {
                'spotify_id': album['spotifyId'],
                'artist': album['artist'],
                'name': album['name'],
                'artist_origin': album['artistOrigin'] if 'artistOrigin' in album.keys() else 'Not_Found',
                'genres': album['genres'],
                'sub_genres': album['subGenres'],
                'releaseDate': int(album['releaseDate']),
                'global_rating': alb_dict['globalRating']
            }
            albums_data.append(album_info)
        except Exception as e:
            logging.error(f"Failed to get album info for {album}: {e}")
    return albums_data

