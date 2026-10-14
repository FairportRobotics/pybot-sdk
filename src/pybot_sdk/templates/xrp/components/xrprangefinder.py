"""XRP Rangefinder component."""

import magicbot
import wpimath.units as units
import xrp


class XRPRangefinder:
    """Rangefinder component for the XRP robot."""

    # Injected variables
    ## Check if they want raw or filtered distance values
    distance_mode: str = "filtered"  # "raw" or "filtered"
    sensor: xrp.XRPRangefinder

    def setup(self) -> None:
        """Set up the rangefinder component."""
        self._raw_distance = 0.0
        self._unit = "in"
        if self.distance_mode not in ["raw", "filtered"]:
            raise ValueError("Invalid distance mode. Must be 'raw' or 'filtered'.")

    def execute(self) -> None:
        """Run the component's periodic behavior."""
        self._raw_distance = self.sensor.getDistance()

    @property
    def distance(self):
        """Get the distance in the specified unit."""
        if self.unit == "m":
            if self.distance_mode == "raw":
                return self._raw_distance
            else:
                return round(self._raw_distance, 2)
        elif self.unit == "cm":
            if self.distance_mode == "raw":
                return self._raw_distance * 100
            else:
                return round(self._raw_distance * 100, 2)
        elif self.unit == "in":
            if self.distance_mode == "raw":
                return units.metersToInches(self._raw_distance)
            else:
                return round(units.metersToInches(self._raw_distance), 2)
        elif self.unit == "ft":
            if self.distance_mode == "raw":
                return units.metersToFeet(self._raw_distance)
            else:
                return round(units.metersToFeet(self._raw_distance), 2)
        elif self.unit == "yd":
            if self.distance_mode == "raw":
                return units.metersToFeet(self._raw_distance) / 3
            else:
                return round(units.metersToFeet(self._raw_distance) / 3, 2)

    @magicbot.feedback(key="distance")
    def _get_distance(self) -> float | None:
        """Return the distance in the specified unit."""
        return self.distance

    @property
    def unit(self) -> str:
        """Get the unit of measurement for the distance."""
        return self._unit

    @magicbot.feedback(key="unit")
    def _get_unit(self) -> str:
        """Return the unit of measurement for the distance."""
        return self.unit

    @unit.setter
    def unit(self, value) -> None:
        """Set the unit of measurement for the distance."""
        # Normalize the input
        value = value.lower()
        # Handle common variations of units
        if value in ["inches", "inch", '"']:
            value = "in"
        elif value in ["feet", "foot", "'"]:
            value = "ft"
        elif value in ["yards", "yard", "yrd"]:
            value = "yd"
        elif value in ["centimeters", "centimeter"]:
            value = "cm"
        elif value in ["meters", "meter"]:
            value = "m"
        # Check for valid unit
        if value not in ["in", "ft", "yd", "cm", "m"]:
            raise ValueError("Invalid unit. Must be 'in', 'ft', 'yd', 'cm', or 'm'.")
        self._unit = value
