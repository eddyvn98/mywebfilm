import metadata_worker


def test_normalize_javinizer_result_keeps_source_metadata():
    raw = {
        "source": "r18dev",
        "source_url": "https://example.test/source",
        "id": "IPX-535",
        "content_id": "ipx00535",
        "title": "Example title",
        "release_date": "2020-09-13T00:00:00Z",
        "runtime": 119,
        "maker": "Idea Pocket",
        "label": "Dish",
        "series": "Example Series",
        "actresses": [
            {
                "first_name": "Momo",
                "last_name": "Sakura",
                "japanese_name": "Sample",
            }
        ],
        "genres": ["4K", "Featured Actress"],
        "poster_url": "https://example.test/poster.jpg",
        "cover_url": "https://example.test/cover.jpg",
    }

    result = metadata_worker.normalize_javinizer_result(raw, "ipx-535")

    assert result["code"] == "IPX-535"
    assert result["actors"] == ["Momo Sakura"]
    assert result["studio"] == "Idea Pocket"
    assert result["release_date"] == "2020-09-13"
    assert result["source_runtime"] == 119
    assert result["metadata_status"] == "verified"
    assert result["source"] == "r18dev"


def test_normalize_javinizer_result_rejects_wrong_code():
    raw = {"id": "IPX-999", "title": "Wrong movie"}
    assert metadata_worker.normalize_javinizer_result(raw, "IPX-535") is None
