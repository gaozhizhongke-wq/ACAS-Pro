# -*- coding: utf-8 -*-

class TestPlatformStubs:
    def test_bilibili(self):
        import sys
        sys.path.insert(0, r"C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro")
        from acas_pro.platforms.bilibili import BilibiliAPI
        api = BilibiliAPI(api_key="k1")
        assert api.api_key == "k1"
        assert api.get_video_info("BV1")["id"] == "BV1"
        assert isinstance(api.search_videos("kw"), list)
        assert isinstance(api.get_trending(), list)

    def test_douyin(self):
        from acas_pro.platforms.douyin import DouyinAPI
        api = DouyinAPI(api_key="k2")
        assert api.api_key == "k2"

    def test_kuaishou(self):
        from acas_pro.platforms.kuaishou import KuaishouAPI
        api = KuaishouAPI(api_key="k3")
        assert api.api_key == "k3"

    def test_xiaohongshu(self):
        from acas_pro.platforms.xiaohongshu import XiaohongshuAPI
        api = XiaohongshuAPI(api_key="k4")
        assert api.api_key == "k4"
