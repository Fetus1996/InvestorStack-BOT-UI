import pytest
from pydantic import ValidationError
from ..core.config_models import GridConfig, ZoneDef


class TestConfigValidation:
    """Test suite for configuration validation."""

    def test_valid_config(self):
        """Test valid configuration."""
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
            network="live",
            symbol="BTC/USDT"
        )
        assert config.upper_bound == 65000
        assert config.lower_bound == 60000
        assert config.total_levels == 11

    def test_bounds_validation(self):
        """Test upper/lower bounds validation."""
        # Invalid: upper <= lower
        with pytest.raises(ValidationError) as exc_info:
            GridConfig(
                upper_bound=60000,
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
        assert "upper_bound must be > lower_bound" in str(exc_info.value)

        # Invalid: negative bounds
        with pytest.raises(ValidationError):
            GridConfig(
                upper_bound=-65000,
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

    def test_levels_validation(self):
        """Test total levels validation."""
        # Invalid: levels < 2
        with pytest.raises(ValidationError):
            GridConfig(
                upper_bound=65000,
                lower_bound=60000,
                total_levels=1,
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

    def test_spacing_validation(self):
        """Test spacing type and value validation."""
        # Valid spacing types
        for spacing_type in ["fixed", "percent"]:
            config = GridConfig(
                upper_bound=65000,
                lower_bound=60000,
                total_levels=11,
                spacing_type=spacing_type,
                spacing_value=0,
                position_size=0.001,
                max_exposure=0.05,
                zones=[],
                enabled=False,
                mode="sim",
                exchange="okx",
                symbol="BTC/USDT"
            )
            assert config.spacing_type == spacing_type

        # Invalid spacing type
        with pytest.raises(ValidationError):
            GridConfig(
                upper_bound=65000,
                lower_bound=60000,
                total_levels=11,
                spacing_type="invalid",
                spacing_value=0,
                position_size=0.001,
                max_exposure=0.05,
                zones=[],
                enabled=False,
                mode="sim",
                exchange="okx",
                symbol="BTC/USDT"
            )

        # Invalid: negative spacing value
        with pytest.raises(ValidationError):
            GridConfig(
                upper_bound=65000,
                lower_bound=60000,
                total_levels=11,
                spacing_type="fixed",
                spacing_value=-1,
                position_size=0.001,
                max_exposure=0.05,
                zones=[],
                enabled=False,
                mode="sim",
                exchange="okx",
                symbol="BTC/USDT"
            )

    def test_position_sizing_validation(self):
        """Test position size and max exposure validation."""
        # Invalid: negative position size
        with pytest.raises(ValidationError):
            GridConfig(
                upper_bound=65000,
                lower_bound=60000,
                total_levels=11,
                spacing_type="fixed",
                spacing_value=0,
                position_size=-0.001,
                max_exposure=0.05,
                zones=[],
                enabled=False,
                mode="sim",
                exchange="okx",
                symbol="BTC/USDT"
            )

        # Invalid: negative max exposure
        with pytest.raises(ValidationError):
            GridConfig(
                upper_bound=65000,
                lower_bound=60000,
                total_levels=11,
                spacing_type="fixed",
                spacing_value=0,
                position_size=0.001,
                max_exposure=-0.05,
                zones=[],
                enabled=False,
                mode="sim",
                exchange="okx",
                symbol="BTC/USDT"
            )

    def test_exchange_network_validation(self):
        """Test exchange and network validation."""
        # Valid: OKX with demo network
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
            network="demo",
            symbol="BTC/USDT"
        )
        assert config.network == "demo"

        # Invalid: Bitkub with demo network
        with pytest.raises(ValidationError) as exc_info:
            GridConfig(
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
                exchange="bitkub",
                network="demo",
                symbol="THB_BTC"
            )
        assert "Bitkub does not support demo network" in str(exc_info.value)

    def test_zone_validation(self):
        """Test zone configuration validation."""
        # Valid zones
        zones = [
            ZoneDef(id=1, level_start=0, level_end=5, enabled=True),
            ZoneDef(id=2, level_start=6, level_end=10, enabled=False)
        ]

        config = GridConfig(
            upper_bound=65000,
            lower_bound=60000,
            total_levels=11,
            spacing_type="fixed",
            spacing_value=0,
            position_size=0.001,
            max_exposure=0.05,
            zones=zones,
            enabled=False,
            mode="sim",
            exchange="okx",
            symbol="BTC/USDT"
        )
        assert len(config.zones) == 2

        # Invalid: level_end < level_start
        with pytest.raises(ValidationError):
            ZoneDef(id=1, level_start=5, level_end=2, enabled=True)

    def test_symbol_patterns(self):
        """Test symbol validation for different exchanges."""
        # OKX symbols
        okx_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        for symbol in okx_symbols:
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
                symbol=symbol
            )
            assert config.symbol == symbol

        # Bitkub symbols
        bitkub_symbols = ["THB_BTC", "THB_ETH", "THB_SOL"]
        for symbol in bitkub_symbols:
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
                exchange="bitkub",
                symbol=symbol
            )
            assert config.symbol == symbol