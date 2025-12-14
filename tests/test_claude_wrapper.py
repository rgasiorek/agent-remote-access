import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add agent-api to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agent-api"))

from claude_wrapper import ClaudeWrapper, ClaudeResponse


class TestClaudeWrapper:
    """Test Claude CLI wrapper functionality"""

    @patch('claude_wrapper.Path')
    def test_init_without_project_path(self, mock_path):
        """Test initialization without project path uses current directory"""
        mock_path.cwd.return_value = Path('/test/path')
        mock_path.home.return_value = Path('/home/user')

        # Mock .claude.json exists
        with patch.object(Path, 'exists', return_value=True):
            wrapper = ClaudeWrapper()
            assert wrapper.project_path == '/test/path'
            assert wrapper.timeout == 600  # 10 minutes
            assert wrapper.cli_command == 'claude'

    @patch('claude_wrapper.Path')
    def test_init_with_project_path(self, mock_path):
        """Test initialization with specific project path"""
        mock_path.home.return_value = Path('/home/user')

        with patch.object(Path, 'exists', return_value=True):
            wrapper = ClaudeWrapper(project_path='/custom/path', timeout=60)
            assert wrapper.project_path == '/custom/path'
            assert wrapper.timeout == 60

    @patch('claude_wrapper.Path')
    def test_check_authentication_not_authenticated(self, mock_path):
        """Test that error is raised when Claude CLI is not authenticated"""
        mock_path.home.return_value = Path('/home/user')

        with patch.object(Path, 'exists', return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                ClaudeWrapper()

            assert "not authenticated" in str(exc_info.value)
            assert "claude login" in str(exc_info.value)

    @patch('claude_wrapper.subprocess')
    @patch('claude_wrapper.Path')
    def test_execute_success(self, mock_path, mock_subprocess):
        """Test successful Claude CLI execution"""
        mock_path.home.return_value = Path('/home/user')

        # Mock authentication check
        with patch.object(Path, 'exists', return_value=True):
            wrapper = ClaudeWrapper()

        # Mock successful subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'result': 'Test response',
            'session_id': 'test-session-123',
            'total_cost_usd': 0.05,
            'num_turns': 2
        })
        mock_subprocess.run.return_value = mock_result

        response = wrapper.execute('Test message')

        assert response.success is True
        assert response.response == 'Test response'
        assert response.session_id == 'test-session-123'
        assert response.cost == 0.05
        assert response.turns == 2
        assert response.error is None

    @patch('claude_wrapper.subprocess')
    @patch('claude_wrapper.Path')
    def test_execute_with_session_id(self, mock_path, mock_subprocess):
        """Test Claude CLI execution with existing session ID"""
        mock_path.home.return_value = Path('/home/user')

        with patch.object(Path, 'exists', return_value=True):
            wrapper = ClaudeWrapper()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'result': 'Resumed response',
            'session_id': 'existing-session',
            'total_cost_usd': 0.03,
            'num_turns': 5
        })
        mock_subprocess.run.return_value = mock_result

        response = wrapper.execute('Follow-up message', session_id='existing-session')

        # Verify --resume flag was passed
        call_args = mock_subprocess.run.call_args
        assert '--resume' in call_args[0][0]
        assert 'existing-session' in call_args[0][0]
        assert response.session_id == 'existing-session'

    @patch('claude_wrapper.subprocess.run')
    @patch('claude_wrapper.Path')
    def test_execute_timeout(self, mock_path, mock_run):
        """Test timeout handling"""
        mock_path.home.return_value = Path('/home/user')

        with patch.object(Path, 'exists', return_value=True):
            wrapper = ClaudeWrapper(timeout=1)

        # Mock timeout exception - import the real exception
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired('claude', 1)

        response = wrapper.execute('Test message')

        assert response.success is False
        assert 'timed out' in response.error
        assert '1 seconds' in response.error

    @patch('claude_wrapper.subprocess.run')
    @patch('claude_wrapper.Path')
    def test_execute_json_decode_error(self, mock_path, mock_run):
        """Test handling of invalid JSON response"""
        mock_path.home.return_value = Path('/home/user')

        with patch.object(Path, 'exists', return_value=True):
            wrapper = ClaudeWrapper()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'Not valid JSON'
        mock_run.return_value = mock_result

        response = wrapper.execute('Test message')

        assert response.success is False
        assert 'Failed to parse' in response.error

    @patch('claude_wrapper.subprocess')
    @patch('claude_wrapper.Path')
    def test_execute_command_failure(self, mock_path, mock_subprocess):
        """Test handling of failed Claude CLI command"""
        mock_path.home.return_value = Path('/home/user')

        with patch.object(Path, 'exists', return_value=True):
            wrapper = ClaudeWrapper()

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = '{}'
        mock_result.stderr = 'Command failed'
        mock_subprocess.run.return_value = mock_result

        response = wrapper.execute('Test message')

        assert response.success is False
        assert 'error' in response.error.lower()

    @patch('claude_wrapper.Path')
    def test_list_sessions_no_history_file(self, mock_path):
        """Test listing sessions when history file doesn't exist"""
        mock_path.home.return_value = Path('/home/user')

        with patch.object(Path, 'exists', side_effect=[True, False]):  # .claude.json exists, history.jsonl doesn't
            wrapper = ClaudeWrapper()
            result = wrapper.list_sessions()

        assert result == {'sessions': []}
