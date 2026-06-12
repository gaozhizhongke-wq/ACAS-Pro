from acas_pro.ui.logic.video_logic import VideoLogic, VideoProject, VideoFormat, VideoQuality, RenderJob


class TestVideoFormat:
    """Test VideoFormat enum"""
    
    def test_format_values(self):
        """Test video format values"""
        assert VideoFormat.MP4.value == "mp4"
        assert VideoFormat.MOV.value == "mov"
        assert VideoFormat.AVI.value == "avi"
        assert VideoFormat.WEBM.value == "webm"


class TestVideoQuality:
    """Test VideoQuality enum"""
    
    def test_quality_values(self):
        """Test video quality values"""
        assert VideoQuality.SD_480P.value == "480p"
        assert VideoQuality.HD_720P.value == "720p"
        assert VideoQuality.FHD_1080P.value == "1080p"
        assert VideoQuality.QHD_1440P.value == "1440p"
        assert VideoQuality.UHD_4K.value == "4k"


class TestVideoProject:
    """Test VideoProject dataclass"""
    
    def test_project_creation(self):
        """Test creating video project"""
        project = VideoProject(
            id="proj_1",
            name="Test",
            duration=60,
            format=VideoFormat.MP4,
            quality=VideoQuality.FHD_1080P,
            scenes=[],
            audio_tracks=[],
            status="draft"
        )
        
        assert project.id == "proj_1"
        assert project.name == "Test"
        assert project.duration == 60
        assert project.format == VideoFormat.MP4
        assert project.quality == VideoQuality.FHD_1080P
        assert project.status == "draft"


class TestRenderJob:
    """Test RenderJob dataclass"""
    
    def test_job_creation(self):
        """Test creating render job"""
        job = RenderJob(
            id="job_1",
            project_id="proj_1",
            status="queued",
            progress=0.0,
            output_path="/tmp/output.mp4",
            estimated_time=120
        )
        
        assert job.id == "job_1"
        assert job.progress == 0.0
        assert job.estimated_time == 120


class TestVideoLogicInit:
    """Test VideoLogic initialization"""
    
    def test_init(self):
        """Test initialization"""
        logic = VideoLogic()
        
        assert logic._projects == {}
        assert logic._render_jobs == {}


class TestCreateProject:
    """Test creating projects"""
    
    def test_create_default(self):
        """Test creating project with defaults"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        
        assert project.name == "Test"
        assert project.duration == 60
        assert project.format == VideoFormat.MP4
        assert project.quality == VideoQuality.FHD_1080P
        assert project.status == "draft"
        assert len(project.scenes) == 0
        assert len(project.audio_tracks) == 0
        assert project.id in logic._projects

    def test_create_custom_format(self):
        """Test creating project with custom format"""
        logic = VideoLogic()
        project = logic.create_project("Test", 30, format=VideoFormat.MOV)
        
        assert project.format == VideoFormat.MOV

    def test_create_custom_quality(self):
        """Test creating project with custom quality"""
        logic = VideoLogic()
        project = logic.create_project("Test", 30, quality=VideoQuality.UHD_4K)
        
        assert project.quality == VideoQuality.UHD_4K

    def test_unique_ids(self):
        """Test projects have unique IDs"""
        logic = VideoLogic()
        p1 = logic.create_project("A", 60)
        p2 = logic.create_project("B", 60)
        
        assert p1.id != p2.id


class TestAddScene:
    """Test adding scenes"""
    
    def test_add_scene(self):
        """Test adding scene to project"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        
        result = logic.add_scene(project.id, {"duration": 10, "content": "intro"})
        
        assert result is True
        assert len(project.scenes) == 1
        assert project.scenes[0]["content"] == "intro"
        assert project.scenes[0]["id"] == 0

    def test_add_multiple_scenes(self):
        """Test adding multiple scenes"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        
        logic.add_scene(project.id, {"duration": 10})
        logic.add_scene(project.id, {"duration": 20})
        logic.add_scene(project.id, {"duration": 30})
        
        assert len(project.scenes) == 3
        assert project.scenes[0]["id"] == 0
        assert project.scenes[1]["id"] == 1
        assert project.scenes[2]["id"] == 2

    def test_add_scene_invalid_project(self):
        """Test adding scene to invalid project"""
        logic = VideoLogic()
        
        result = logic.add_scene("invalid", {"duration": 10})
        
        assert result is False


class TestAddAudioTrack:
    """Test adding audio tracks"""
    
    def test_add_audio(self):
        """Test adding audio track"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        
        result = logic.add_audio_track(project.id, {"type": "music", "path": "/music.mp3"})
        
        assert result is True
        assert len(project.audio_tracks) == 1

    def test_add_multiple_audio(self):
        """Test adding multiple audio tracks"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        
        logic.add_audio_track(project.id, {"type": "music"})
        logic.add_audio_track(project.id, {"type": "voice"})
        
        assert len(project.audio_tracks) == 2

    def test_add_audio_invalid_project(self):
        """Test adding audio to invalid project"""
        logic = VideoLogic()
        
        result = logic.add_audio_track("invalid", {"type": "music"})
        
        assert result is False


class TestEstimateRenderTime:
    """Test render time estimation"""
    
    def test_empty_project(self):
        """Test empty project estimation"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        
        time = logic.estimate_render_time(project.id)
        
        # Base time + 0 scenes * 10 * 1.0 multiplier
        assert time == 30

    def test_with_scenes(self):
        """Test estimation with scenes"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        logic.add_scene(project.id, {"duration": 10})
        logic.add_scene(project.id, {"duration": 20})
        
        time = logic.estimate_render_time(project.id)
        
        # 30 + 2 * 10 * 1.0 = 50
        assert time == 50

    def test_different_qualities(self):
        """Test estimation with different qualities"""
        logic = VideoLogic()
        
        p480 = logic.create_project("480p", 60, quality=VideoQuality.SD_480P)
        p720 = logic.create_project("720p", 60, quality=VideoQuality.HD_720P)
        p1080 = logic.create_project("1080p", 60, quality=VideoQuality.FHD_1080P)
        p1440 = logic.create_project("1440p", 60, quality=VideoQuality.QHD_1440P)
        p4k = logic.create_project("4k", 60, quality=VideoQuality.UHD_4K)
        
        assert logic.estimate_render_time(p480.id) == 15  # 30 * 0.5
        assert logic.estimate_render_time(p720.id) == 24  # 30 * 0.8
        assert logic.estimate_render_time(p1080.id) == 30  # 30 * 1.0
        assert logic.estimate_render_time(p1440.id) == 54  # 30 * 1.8
        assert logic.estimate_render_time(p4k.id) == 105  # 30 * 3.5

    def test_invalid_project(self):
        """Test estimation for invalid project"""
        logic = VideoLogic()
        
        time = logic.estimate_render_time("invalid")
        
        assert time == 0


class TestGetQualitySettings:
    """Test quality settings"""
    
    def test_480p_settings(self):
        """Test 480p settings"""
        logic = VideoLogic()
        settings = logic.get_quality_settings(VideoQuality.SD_480P)
        
        assert settings["width"] == 854
        assert settings["height"] == 480
        assert settings["bitrate"] == "2M"

    def test_1080p_settings(self):
        """Test 1080p settings"""
        logic = VideoLogic()
        settings = logic.get_quality_settings(VideoQuality.FHD_1080P)
        
        assert settings["width"] == 1920
        assert settings["height"] == 1080
        assert settings["bitrate"] == "8M"

    def test_4k_settings(self):
        """Test 4K settings"""
        logic = VideoLogic()
        settings = logic.get_quality_settings(VideoQuality.UHD_4K)
        
        assert settings["width"] == 3840
        assert settings["height"] == 2160
        assert settings["bitrate"] == "35M"

    def test_invalid_quality(self):
        """Test invalid quality defaults to 1080p"""
        logic = VideoLogic()
        settings = logic.get_quality_settings(None)
        
        assert settings["width"] == 1920
        assert settings["height"] == 1080


class TestValidateProject:
    """Test project validation"""
    
    def test_valid_project(self):
        """Test valid project"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        logic.add_scene(project.id, {"duration": 60})
        
        issues = logic.validate_project(project.id)
        
        assert issues == []

    def test_no_scenes(self):
        """Test project with no scenes"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        
        issues = logic.validate_project(project.id)
        
        assert "No scenes added" in issues

    def test_duration_mismatch(self):
        """Test duration mismatch"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        logic.add_scene(project.id, {"duration": 30})  # Only 30s, but project is 60s
        
        issues = logic.validate_project(project.id)
        
        assert any("don't match" in issue for issue in issues)

    def test_invalid_project(self):
        """Test invalid project"""
        logic = VideoLogic()
        
        issues = logic.validate_project("invalid")
        
        assert "Project not found" in issues

    def test_matching_duration(self):
        """Test matching durations"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        logic.add_scene(project.id, {"duration": 30})
        logic.add_scene(project.id, {"duration": 30})
        
        issues = logic.validate_project(project.id)
        
        assert issues == []


class TestExportProjectConfig:
    """Test exporting project config"""
    
    def test_export(self):
        """Test exporting project"""
        logic = VideoLogic()
        project = logic.create_project("Test", 60)
        logic.add_scene(project.id, {"duration": 60})
        logic.add_audio_track(project.id, {"type": "music"})
        
        config = logic.export_project_config(project.id)
        
        assert config["id"] == project.id
        assert config["name"] == "Test"
        assert config["duration"] == 60
        assert config["format"] == "mp4"
        assert config["quality"] == "1080p"
        assert config["scene_count"] == 1
        assert config["audio_track_count"] == 1
        assert "settings" in config
        assert config["settings"]["width"] == 1920

    def test_export_invalid_project(self):
        """Test exporting invalid project"""
        logic = VideoLogic()
        
        config = logic.export_project_config("invalid")
        
        assert config == {}

    def test_export_empty_project(self):
        """Test exporting empty project"""
        logic = VideoLogic()
        project = logic.create_project("Empty", 0)
        
        config = logic.export_project_config(project.id)
        
        assert config["scene_count"] == 0
        assert config["audio_track_count"] == 0


class TestQualitySettings:
    """Test quality settings dictionary"""
    
    def test_all_qualities_present(self):
        """Test all qualities have settings"""
        logic = VideoLogic()
        
        for quality in VideoQuality:
            settings = logic.get_quality_settings(quality)
            assert "width" in settings
            assert "height" in settings
            assert "bitrate" in settings
            assert settings["width"] > 0
            assert settings["height"] > 0

    def test_quality_progression(self):
        """Test quality settings increase with quality"""
        logic = VideoLogic()
        
        s480 = logic.get_quality_settings(VideoQuality.SD_480P)
        s720 = logic.get_quality_settings(VideoQuality.HD_720P)
        s1080 = logic.get_quality_settings(VideoQuality.FHD_1080P)
        s1440 = logic.get_quality_settings(VideoQuality.QHD_1440P)
        s4k = logic.get_quality_settings(VideoQuality.UHD_4K)
        
        assert s480["width"] < s720["width"] < s1080["width"] < s1440["width"] < s4k["width"]
        assert s480["height"] < s720["height"] < s1080["height"] < s1440["height"] < s4k["height"]
