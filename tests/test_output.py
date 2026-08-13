from indoscraping_core.output import meta_sidecar_path


def test_meta_sidecar_path_json():
    assert meta_sidecar_path("data/news/detik/latest.json") == "data/news/detik/latest.meta.json"


def test_meta_sidecar_path_non_json():
    assert meta_sidecar_path("data/latest") == "data/latest.meta.json"
