import os
import sys
import types

# Provide a minimal stub for the requests module used by get_1001_data
sys.modules.setdefault('requests', types.ModuleType('requests'))

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import get_1001_data


def test_get_albums_handles_missing_keys(monkeypatch):
    sample_history = [
        {"album": {
            "spotifyId": "id1",
            "artist": "Test Artist",
            "name": "Test Name",
            "genres": [],
            "subGenres": [],
            # missing 'releaseDate' key will cause exception
        },
         "globalRating": 4}
    ]

    def fake_get_project_stats(project_id):
        return {"history": sample_history}

    monkeypatch.setattr(get_1001_data, "get_project_stats", fake_get_project_stats)

    albums = get_1001_data.get_albums("dummy")
    # Because parsing failed, no albums should be returned
    assert albums == []
