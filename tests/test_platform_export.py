from app.services.platform_export import PlatformExportPresets


def test_platform_presets_include_required_platforms():
    presets = PlatformExportPresets.all()

    assert {"youtube_shorts", "instagram_reels", "tiktok", "facebook_reels"} <= set(
        presets
    )
    assert presets["youtube_shorts"].width == 1080
