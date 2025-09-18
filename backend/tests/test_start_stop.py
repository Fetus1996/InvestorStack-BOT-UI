import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ..engine.services import BotService
from ..core.config_models import GridConfig
from ..core.state import state_manager


class TestStartStop:
    """Test suite for bot start/stop flow."""

    @pytest.fixture
    async def bot_service(self):
        """Create bot service instance."""
        service = BotService()
        config = GridConfig(
            upper_bound=65000,
            lower_bound=60000,
            total_levels=11,
            spacing_type="fixed",
            spacing_value=0,
            position_size=0.001,
            max_exposure=0.05,
            zones=[],
            enabled=False,
            mode="sim",
            exchange="okx",
            symbol="BTC/USDT"
        )
        await service.initialize(config)
        return service

    @pytest.mark.asyncio
    async def test_start_flow(self, bot_service):
        """Test bot start flow."""
        # Initial state should be STOPPED
        state = await state_manager.get_state()
        assert state.state == "STOPPED"

        # Start without confirmation should fail
        result = await bot_service.start_bot(confirm=False)
        assert result["success"] is False
        assert "Confirmation required" in result["message"]

        # Start with confirmation
        with patch('backend.engine.services.get_db'):
            with patch('backend.engine.services.save_action_log'):
                result = await bot_service.start_bot(confirm=True)
                assert result["success"] is True

                # Check state changed to RUNNING or SIM_RUNNING
                state = await state_manager.get_state()
                assert state.state in ["RUNNING", "SIM_RUNNING"]

                # Check enabled flag
                config = state_manager.get_config()
                assert config.enabled is True

    @pytest.mark.asyncio
    async def test_stop_flow(self, bot_service):
        """Test bot stop flow."""
        # Start the bot first
        with patch('backend.engine.services.get_db'):
            with patch('backend.engine.services.save_action_log'):
                await bot_service.start_bot(confirm=True)

                # Stop without confirmation should fail
                result = await bot_service.stop_bot(confirm=False)
                assert result["success"] is False
                assert "Confirmation required" in result["message"]

                # Stop with confirmation
                result = await bot_service.stop_bot(confirm=True)
                assert result["success"] is True

                # Check state changed to STOPPED
                state = await state_manager.get_state()
                assert state.state == "STOPPED"

                # Check enabled flag
                config = state_manager.get_config()
                assert config.enabled is False

    @pytest.mark.asyncio
    async def test_toggle_enabled(self, bot_service):
        """Test toggling enabled flag."""
        config = state_manager.get_config()
        assert config.enabled is False

        # Enable via config update
        config.enabled = True
        with patch('backend.engine.services.get_db'):
            with patch('backend.engine.services.save_action_log'):
                result = await bot_service.update_config(config)
                assert result["success"] is True

                # Check enabled flag
                updated_config = state_manager.get_config()
                assert updated_config.enabled is True

    @pytest.mark.asyncio
    async def test_reset_flow(self, bot_service):
        """Test bot reset flow."""
        # Start the bot
        with patch('backend.engine.services.get_db'):
            with patch('backend.engine.services.save_action_log'):
                await bot_service.start_bot(confirm=True)

                # Reset without confirmation should fail
                result = await bot_service.reset_bot(confirm=False)
                assert result["success"] is False
                assert "Confirmation required" in result["message"]

                # Reset with confirmation (cancel only)
                result = await bot_service.reset_bot(confirm=True, clear_positions=False)
                assert result["success"] is True

                # Reset with clear positions
                result = await bot_service.reset_bot(confirm=True, clear_positions=True)
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_zone_toggle(self, bot_service):
        """Test zone enable/disable."""
        # Create config with zones
        config = GridConfig(
            upper_bound=65000,
            lower_bound=60000,
            total_levels=11,
            spacing_type="fixed",
            spacing_value=0,
            position_size=0.001,
            max_exposure=0.05,
            zones=[
                {"id": 1, "level_start": 0, "level_end": 5, "enabled": True},
                {"id": 2, "level_start": 6, "level_end": 10, "enabled": True}
            ],
            enabled=False,
            mode="sim",
            exchange="okx",
            symbol="BTC/USDT"
        )

        with patch('backend.engine.services.get_db'):
            with patch('backend.engine.services.save_action_log'):
                await bot_service.update_config(config)
                await bot_service.initialize(config)

                # Disable zone 1
                result = await bot_service.toggle_zone(1, enabled=False)
                assert result["success"] is True
                assert "disabled" in result["message"]

                # Enable zone 1
                result = await bot_service.toggle_zone(1, enabled=True)
                assert result["success"] is True
                assert "enabled" in result["message"]

    @pytest.mark.asyncio
    async def test_action_logging(self, bot_service):
        """Test that actions are logged correctly."""
        with patch('backend.engine.services.save_action_log') as mock_log:
            with patch('backend.engine.services.get_db'):
                # Start action
                await bot_service.start_bot(confirm=True)
                mock_log.assert_called()
                call_args = mock_log.call_args[1]
                assert call_args['action'] == 'START'

                mock_log.reset_mock()

                # Stop action
                await bot_service.stop_bot(confirm=True)
                mock_log.assert_called()
                call_args = mock_log.call_args[1]
                assert call_args['action'] == 'STOP'

                mock_log.reset_mock()

                # Reset action
                await bot_service.reset_bot(confirm=True)
                mock_log.assert_called()
                call_args = mock_log.call_args[1]
                assert call_args['action'] == 'RESET'

    @pytest.mark.asyncio
    async def test_state_transitions(self, bot_service):
        """Test state machine transitions."""
        # STOPPED -> STARTING -> RUNNING
        state = await state_manager.get_state()
        assert state.state == "STOPPED"

        with patch('backend.engine.services.get_db'):
            with patch('backend.engine.services.save_action_log'):
                # Start will transition through STARTING
                await bot_service.start_bot(confirm=True)
                state = await state_manager.get_state()
                assert state.state in ["RUNNING", "SIM_RUNNING"]

                # RUNNING -> STOPPING -> STOPPED
                await bot_service.stop_bot(confirm=True)
                state = await state_manager.get_state()
                assert state.state == "STOPPED"

    @pytest.mark.asyncio
    async def test_error_handling(self, bot_service):
        """Test error state handling."""
        # Simulate error during start
        with patch('backend.engine.grid_engine.GridEngine.start', side_effect=Exception("Test error")):
            with patch('backend.engine.services.get_db'):
                with patch('backend.engine.services.save_action_log'):
                    result = await bot_service.start_bot(confirm=True)
                    assert result["success"] is False
                    assert "Test error" in result["message"]