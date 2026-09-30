import json

from storage_utils import atomic_write_json


def test_atomic_write_json_replaces_complete_document(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{"old": true}', encoding='utf-8')

    atomic_write_json(str(path), {'new': ['safe', 1]})

    assert json.loads(path.read_text(encoding='utf-8')) == {'new': ['safe', 1]}
    assert not list(tmp_path.glob('.tmp-*.json'))
