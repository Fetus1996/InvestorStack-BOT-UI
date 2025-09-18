import pytest
import math
from ..engine.grid_calculator import GridCalculator


class TestGridCalculator:
    """Test suite for grid calculator."""

    def test_fixed_grid_calculation(self):
        """Test fixed spacing grid calculation."""
        lower = 60000
        upper = 65000
        levels = 11

        result = GridCalculator.calculate_fixed_grid(lower, upper, levels)

        assert len(result) == levels
        assert result[0] == lower
        assert result[-1] == upper

        # Check equal spacing
        step = (upper - lower) / (levels - 1)
        for i in range(1, levels):
            expected = lower + (i * step)
            assert abs(result[i] - expected) < 0.01

    def test_percent_grid_calculation(self):
        """Test percentage spacing grid calculation."""
        lower = 60000
        upper = 65000
        levels = 11

        result = GridCalculator.calculate_percent_grid(lower, upper, levels)

        assert len(result) == levels
        assert abs(result[0] - lower) < 0.01
        assert abs(result[-1] - upper) < 0.01

        # Check geometric progression
        r = math.pow(upper / lower, 1 / (levels - 1)) - 1
        for i in range(levels):
            expected = lower * math.pow(1 + r, i)
            assert abs(result[i] - expected) < 0.01

    def test_grid_validation(self):
        """Test grid configuration validation."""
        # Valid config
        valid, msg = GridCalculator.validate_grid_config(65000, 60000, 11, 0)
        assert valid is True

        # Invalid: upper <= lower
        valid, msg = GridCalculator.validate_grid_config(60000, 65000, 11, 0)
        assert valid is False
        assert "greater than lower" in msg

        # Invalid: levels < 2
        valid, msg = GridCalculator.validate_grid_config(65000, 60000, 1, 0)
        assert valid is False
        assert "at least 2" in msg

        # Invalid: negative spacing
        valid, msg = GridCalculator.validate_grid_config(65000, 60000, 11, -1)
        assert valid is False
        assert "cannot be negative" in msg

    def test_side_determination(self):
        """Test order side determination."""
        mid_price = 62500

        # Below mid = buy
        assert GridCalculator.determine_side(62000, mid_price) == "buy"

        # Above mid = sell
        assert GridCalculator.determine_side(63000, mid_price) == "sell"

        # At mid = skip
        assert GridCalculator.determine_side(mid_price, mid_price) == "skip"

    def test_position_sizing(self):
        """Test position size calculation."""
        levels_list = [60000, 61000, 62000, 63000, 64000]

        # Fixed size per level
        sizes = GridCalculator.calculate_position_sizes(
            levels_list,
            position_size_per_level=0.01
        )
        assert all(size == 0.01 for size in sizes)

        # Max exposure distribution
        sizes = GridCalculator.calculate_position_sizes(
            levels_list,
            max_exposure=0.1
        )
        assert all(size == 0.02 for size in sizes)  # 0.1 / 5 levels
        assert sum(sizes) == pytest.approx(0.1)

    def test_zone_mapping(self):
        """Test zone level mapping."""
        levels_list = [60000, 61000, 62000, 63000, 64000]
        zones = [
            {'id': 1, 'level_start': 0, 'level_end': 2, 'enabled': True},
            {'id': 2, 'level_start': 3, 'level_end': 4, 'enabled': False}
        ]

        zone_map = GridCalculator.get_zone_levels(levels_list, zones)

        assert zone_map[0]['zone_id'] == 1
        assert zone_map[0]['enabled'] is True
        assert zone_map[0]['price'] == 60000

        assert zone_map[3]['zone_id'] == 2
        assert zone_map[3]['enabled'] is False
        assert zone_map[3]['price'] == 63000

    def test_edge_cases(self):
        """Test edge cases."""
        # Minimum levels (2)
        result = GridCalculator.calculate_fixed_grid(60000, 65000, 2)
        assert len(result) == 2
        assert result[0] == 60000
        assert result[1] == 65000

        # Very small range
        result = GridCalculator.calculate_fixed_grid(60000, 60001, 5)
        assert len(result) == 5
        assert result[0] == 60000
        assert result[-1] == 60001

        # Large number of levels
        result = GridCalculator.calculate_fixed_grid(50000, 70000, 101)
        assert len(result) == 101
        assert result[0] == 50000
        assert result[-1] == 70000