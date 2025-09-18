from typing import List, Tuple, Literal
import math
from ..core.logging import logger


class GridCalculator:
    """Calculate grid levels and manage grid state."""

    @staticmethod
    def calculate_fixed_grid(lower_bound: float, upper_bound: float, total_levels: int) -> List[float]:
        """Calculate grid levels with fixed spacing."""
        if total_levels < 2:
            raise ValueError("Total levels must be at least 2")
        if upper_bound <= lower_bound:
            raise ValueError("Upper bound must be greater than lower bound")

        step = (upper_bound - lower_bound) / (total_levels - 1)
        levels = []

        for i in range(total_levels):
            level = lower_bound + (i * step)
            levels.append(round(level, 8))

        logger.info(f"Calculated {total_levels} fixed grid levels from {lower_bound} to {upper_bound}")
        return levels

    @staticmethod
    def calculate_percent_grid(lower_bound: float, upper_bound: float, total_levels: int) -> List[float]:
        """Calculate grid levels with percentage spacing."""
        if total_levels < 2:
            raise ValueError("Total levels must be at least 2")
        if upper_bound <= lower_bound:
            raise ValueError("Upper bound must be greater than lower bound")

        # Calculate percentage step: r = (upper/lower)^(1/(levels-1)) - 1
        r = math.pow(upper_bound / lower_bound, 1 / (total_levels - 1)) - 1
        levels = []

        for i in range(total_levels):
            level = lower_bound * math.pow(1 + r, i)
            levels.append(round(level, 8))

        logger.info(f"Calculated {total_levels} percent grid levels from {lower_bound} to {upper_bound}")
        return levels

    @staticmethod
    def calculate_grid(
        lower_bound: float,
        upper_bound: float,
        total_levels: int,
        spacing_type: Literal["fixed", "percent"] = "fixed"
    ) -> List[float]:
        """Calculate grid levels based on spacing type."""
        if spacing_type == "fixed":
            return GridCalculator.calculate_fixed_grid(lower_bound, upper_bound, total_levels)
        elif spacing_type == "percent":
            return GridCalculator.calculate_percent_grid(lower_bound, upper_bound, total_levels)
        else:
            raise ValueError(f"Invalid spacing type: {spacing_type}")

    @staticmethod
    def determine_side(price: float, mid_price: float) -> Literal["buy", "sell", "skip"]:
        """Determine order side based on price relative to mid price."""
        tolerance = 0.00001  # Small tolerance for floating point comparison

        if price < mid_price - tolerance:
            return "buy"
        elif price > mid_price + tolerance:
            return "sell"
        else:
            return "skip"

    @staticmethod
    def calculate_position_sizes(
        levels: List[float],
        position_size_per_level: float = None,
        max_exposure: float = None
    ) -> List[float]:
        """Calculate position size for each grid level."""
        if position_size_per_level:
            return [position_size_per_level] * len(levels)

        if max_exposure:
            # Evenly distribute exposure across all levels
            size_per_level = max_exposure / len(levels)
            return [size_per_level] * len(levels)

        raise ValueError("Either position_size_per_level or max_exposure must be provided")

    @staticmethod
    def get_zone_levels(levels: List[float], zones: List[dict]) -> dict:
        """Map levels to zones."""
        zone_map = {}

        for zone in zones:
            zone_id = zone['id']
            start = zone['level_start']
            end = zone['level_end']

            for i in range(start, min(end + 1, len(levels))):
                zone_map[i] = {
                    'zone_id': zone_id,
                    'enabled': zone['enabled'],
                    'price': levels[i]
                }

        return zone_map

    @staticmethod
    def validate_grid_config(
        upper_bound: float,
        lower_bound: float,
        total_levels: int,
        spacing_value: float = 0
    ) -> Tuple[bool, str]:
        """Validate grid configuration."""
        if upper_bound <= lower_bound:
            return False, "Upper bound must be greater than lower bound"

        if total_levels < 2:
            return False, "Total levels must be at least 2"

        if spacing_value < 0:
            return False, "Spacing value cannot be negative"

        price_range = upper_bound - lower_bound
        if price_range / total_levels < 0.0001:
            return False, "Grid spacing too small"

        return True, "Valid configuration"