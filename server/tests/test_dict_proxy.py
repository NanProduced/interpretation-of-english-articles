"""
Dictionary Proxy API 测试
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestDictProxy:
    """词典代理 API 测试"""

    def test_dict_lookup_word(self):
        """查询单词释义"""
        response = client.get("/dict?q=hello&type=word")
        assert response.status_code == 200
        data = response.json()
        assert data["word"] == "hello"
        assert "phonetic" in data
        assert "meanings" in data
        assert len(data["meanings"]) > 0

    def test_dict_lookup_with_phonetic(self):
        """查询有音标的单词"""
        response = client.get("/dict?q=fundamental&type=word")
        assert response.status_code == 200
        data = response.json()
        assert data["word"] == "fundamental"
        # Free Dictionary API 通常返回音标
        assert isinstance(data["meanings"], list)
        assert len(data["meanings"]) > 0

    def test_dict_lookup_not_found(self):
        """查询不存在的单词"""
        response = client.get("/dict?q=xyzabc123nonexistent&type=word")
        assert response.status_code == 404

    def test_dict_lookup_missing_param(self):
        """缺少查询参数"""
        response = client.get("/dict")
        assert response.status_code == 422

    def test_dict_lookup_empty_param(self):
        """空查询参数"""
        response = client.get("/dict?q=&type=word")
        assert response.status_code == 422

    def test_dict_lookup_phrase_type(self):
        """短语类型查询（暂用单词查询）"""
        response = client.get("/dict?q=hello&type=phrase")
        assert response.status_code == 200
        data = response.json()
        assert data["word"] == "hello"

    def test_dict_meanings_have_structure(self):
        """释义具有正确的结构"""
        response = client.get("/dict?q=run&type=word")
        assert response.status_code == 200
        data = response.json()

        for meaning in data["meanings"]:
            assert "part_of_speech" in meaning
            assert "definitions" in meaning
            assert isinstance(meaning["definitions"], list)

            for defn in meaning["definitions"]:
                assert "meaning" in defn
                assert isinstance(defn["meaning"], str)
