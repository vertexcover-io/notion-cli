"""Filter parsing and conversion for Notion CLI."""

from dataclasses import dataclass
from typing import Any, Union


@dataclass
class FilterCondition:
    """Represents a single filter condition."""

    column: str
    operator: str
    value: str


@dataclass
class LogicalGroup:
    """Represents a logical grouping of conditions."""

    operator: str  # "AND", "OR", "NOT"
    conditions: list[Union["FilterCondition", "LogicalGroup"]]


class FilterParser:
    """Parses filter expressions into structured conditions."""

    # Supported operators in order of precedence (longer first)
    OPERATORS = ["not in", ">=", "<=", "!=", "!~", "in", "=", "~", ">", "<"]

    def __init__(self):
        self.pos = 0
        self.text = ""

    def parse(
        self, filter_text: str
    ) -> FilterCondition | LogicalGroup | list[FilterCondition]:
        """Parse a filter expression into structured conditions."""
        self.text = filter_text.strip()
        self.pos = 0

        if not self.text:
            return []

        return self._parse_expression()

    def _parse_expression(
        self,
    ) -> FilterCondition | LogicalGroup | list[FilterCondition]:
        """Parse the main expression."""
        conditions = []

        while self.pos < len(self.text):
            self._skip_whitespace()

            if self.pos >= len(self.text):
                break

            # Check for logical functions
            if self._peek_function():
                condition = self._parse_function()
                conditions.append(condition)
            else:
                # Parse regular condition
                condition = self._parse_condition()
                conditions.append(condition)

            self._skip_whitespace()

            # Check for comma (AND)
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1
                continue
            else:
                break

        # If we have multiple conditions, wrap in AND
        if len(conditions) > 1:
            return LogicalGroup("AND", conditions)
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return []

    def _parse_function(self) -> LogicalGroup:
        """Parse logical functions like AND(), OR(), NOT()."""
        func_name = self._read_function_name()

        self._skip_whitespace()
        if self.pos >= len(self.text) or self.text[self.pos] != "(":
            raise ValueError(f"Expected '(' after {func_name}")

        self.pos += 1  # Skip '('

        conditions = []
        while self.pos < len(self.text):
            self._skip_whitespace()

            if self.pos >= len(self.text):
                raise ValueError("Unexpected end of expression")

            if self.text[self.pos] == ")":
                self.pos += 1
                break

            # Parse condition or nested function
            if self._peek_function():
                condition = self._parse_function()
            else:
                condition = self._parse_condition()

            conditions.append(condition)

            self._skip_whitespace()

            # Check for comma
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1
            elif self.pos < len(self.text) and self.text[self.pos] == ")":
                self.pos += 1
                break
            else:
                raise ValueError("Expected ',' or ')' in function")

        return LogicalGroup(func_name.upper(), conditions)

    def _parse_condition(self) -> FilterCondition:
        """Parse a single condition like 'status=Done' or 'due<2025-07-10'."""
        # Read column name
        column = self._read_column_name()

        self._skip_whitespace()

        # Read operator
        operator = self._read_operator()
        if not operator:
            operator = "="  # Default operator

        self._skip_whitespace()

        # Read value
        value = self._read_value()

        return FilterCondition(column, operator, value)

    def _read_column_name(self) -> str:
        """Read column name until operator or whitespace."""
        # Check if the column name is quoted
        if self.pos < len(self.text) and self.text[self.pos] in "\"'":
            return self._read_quoted_string()
        
        start = self.pos

        while self.pos < len(self.text):
            char = self.text[self.pos]

            # Check if we've hit an operator
            if self._check_operator_at_pos():
                break

            # Stop at comma or parentheses, but allow spaces in property names
            if char in ",()":
                break

            self.pos += 1

        column = self.text[start:self.pos].strip()
        if not column:
            raise ValueError("Empty column name")

        return column

    def _read_operator(self) -> str:
        """Read operator at current position."""
        for op in self.OPERATORS:
            if self.text[self.pos:self.pos + len(op)] == op:
                self.pos += len(op)
                return op
        return ""

    def _read_value(self) -> str:
        """Read value, handling quoted strings."""
        self._skip_whitespace()

        if self.pos >= len(self.text):
            raise ValueError("Expected value")

        # Handle quoted strings
        if self.text[self.pos] in "\"'":
            return self._read_quoted_string()

        # Read until comma, closing paren, or end
        start = self.pos
        paren_depth = 0

        while self.pos < len(self.text):
            char = self.text[self.pos]

            if char == "(":
                paren_depth += 1
            elif char == ")":
                if paren_depth == 0:
                    break
                paren_depth -= 1
            elif char == "," and paren_depth == 0:
                break

            self.pos += 1

        value = self.text[start:self.pos].strip()
        if not value:
            raise ValueError("Empty value")

        return value

    def _read_quoted_string(self) -> str:
        """Read a quoted string value."""
        quote_char = self.text[self.pos]
        self.pos += 1  # Skip opening quote

        start = self.pos

        while self.pos < len(self.text):
            if self.text[self.pos] == quote_char:
                value = self.text[start:self.pos]
                self.pos += 1  # Skip closing quote
                return value
            elif self.text[self.pos] == "\\" and self.pos + 1 < len(self.text):
                # Handle escaped characters
                self.pos += 2
            else:
                self.pos += 1

        raise ValueError("Unclosed quoted string")

    def _read_function_name(self) -> str:
        """Read function name like 'AND', 'OR', 'NOT'."""
        start = self.pos

        while self.pos < len(self.text):
            char = self.text[self.pos]
            if not (char.isalpha() or char == "_"):
                break
            self.pos += 1

        return self.text[start:self.pos]

    def _peek_function(self) -> bool:
        """Check if current position starts a function."""
        saved_pos = self.pos
        try:
            func_name = self._read_function_name()
            self._skip_whitespace()
            is_function = (func_name.upper() in ["AND", "OR", "NOT"] and
                          self.pos < len(self.text) and
                          self.text[self.pos] == "(")
            return is_function
        finally:
            self.pos = saved_pos

    def _check_operator_at_pos(self) -> bool:
        """Check if an operator starts at current position."""
        for op in self.OPERATORS:
            if self.text[self.pos:self.pos + len(op)] == op:
                # Additional check: make sure the operator is not part of a word
                # by checking that it's followed by whitespace or a value character
                end_pos = self.pos + len(op)
                if end_pos < len(self.text):
                    next_char = self.text[end_pos]
                    # Operator should be followed by space, quote, or alphanumeric
                    if next_char in " \t\"'":
                        return True
                    # For operators like = ~ < >, they should be followed by value chars or end of string
                    if op in ["=", "~", "<", ">", "!", ">=", "<=", "!=", "!~"]:
                        return True
                    # For "in" and "not in", they must be followed by space
                    if op in ["in", "not in"] and next_char in " \t":
                        return True
                else:
                    # End of string, this is an operator
                    return True
        return False

    def _skip_whitespace(self):
        """Skip whitespace characters."""
        while self.pos < len(self.text) and self.text[self.pos] in " \t":
            self.pos += 1


class NotionFilterConverter:
    """Converts parsed filter conditions to Notion API format."""

    def convert(self,
                conditions: FilterCondition | LogicalGroup | list[FilterCondition],
                properties: dict[str, Any]) -> dict[str, Any]:
        """Convert parsed conditions to Notion API filter format."""
        if isinstance(conditions, list):
            if not conditions:
                return {}
            elif len(conditions) == 1:
                return self._convert_single(conditions[0], properties)
            else:
                # Multiple conditions = AND
                converted = [
                    self._convert_single(cond, properties) for cond in conditions
                ]
                return {"and": converted}
        elif isinstance(conditions, FilterCondition):
            return self._convert_single(conditions, properties)
        elif isinstance(conditions, LogicalGroup):
            return self._convert_group(conditions, properties)
        else:
            return {}

    def _convert_single(
        self,
        condition: FilterCondition,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert a single condition to Notion format."""
        # Find the property
        prop_data = None
        prop_name = None

        # Try exact match first
        if condition.column in properties:
            prop_name = condition.column
            prop_data = properties[condition.column]
        else:
            # Try case-insensitive match
            for name, data in properties.items():
                if name.lower() == condition.column.lower():
                    prop_name = name
                    prop_data = data
                    break

        if not prop_data:
            raise ValueError(f"Property '{condition.column}' not found")

        prop_type = prop_data.get("type", "")

        # Convert based on property type and operator
        return self._build_notion_condition(
            prop_name, prop_type, condition.operator, condition.value
        )

    def _convert_group(
        self, group: LogicalGroup, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert a logical group to Notion format."""
        converted_conditions = []

        for condition in group.conditions:
            if isinstance(condition, FilterCondition):
                converted = self._convert_single(condition, properties)
            elif isinstance(condition, LogicalGroup):
                converted = self._convert_group(condition, properties)
            else:
                continue

            converted_conditions.append(converted)

        if group.operator == "AND":
            return {"and": converted_conditions}
        elif group.operator == "OR":
            return {"or": converted_conditions}
        elif group.operator == "NOT":
            if len(converted_conditions) == 1:
                # Notion doesn't have direct NOT, so we need to invert the condition
                return self._invert_condition(converted_conditions[0])
            else:
                # NOT with multiple conditions = NOT(OR(...))
                return self._invert_condition({"or": converted_conditions})
        else:
            raise ValueError(f"Unknown logical operator: {group.operator}")

    def _build_notion_condition(
        self,
        prop_name: str,
        prop_type: str,
        operator: str,
        value: str,
    ) -> dict[str, Any]:
        """Build a Notion API condition for a specific property type."""
        base = {"property": prop_name}

        if prop_type == "title":
            return self._build_title_condition(base, operator, value)
        elif prop_type == "rich_text":
            return self._build_text_condition(base, operator, value)
        elif prop_type == "number":
            return self._build_number_condition(base, operator, value)
        elif prop_type == "select":
            return self._build_select_condition(base, operator, value)
        elif prop_type == "multi_select":
            return self._build_multiselect_condition(base, operator, value)
        elif prop_type == "date":
            return self._build_date_condition(base, operator, value)
        elif prop_type == "checkbox":
            return self._build_checkbox_condition(base, operator, value)
        elif prop_type == "status":
            return self._build_status_condition(base, operator, value)
        else:
            # Default to text-like behavior
            return self._build_text_condition(base, operator, value)

    def _build_title_condition(
        self, base: dict[str, Any], operator: str, value: str
    ) -> dict[str, Any]:
        """Build condition for title properties."""
        if operator == "=":
            return {**base, "title": {"equals": value}}
        elif operator == "!=":
            return {**base, "title": {"does_not_equal": value}}
        elif operator == "~" or operator == "in":
            return {**base, "title": {"contains": value}}
        elif operator == "!~" or operator == "not in":
            return {**base, "title": {"does_not_contain": value}}
        else:
            msg = f"Operator '{operator}' not supported for title properties"
            raise ValueError(msg)

    def _build_text_condition(
        self, base: dict[str, Any], operator: str, value: str
    ) -> dict[str, Any]:
        """Build condition for text properties."""
        if operator == "=":
            return {**base, "rich_text": {"equals": value}}
        elif operator == "!=":
            return {**base, "rich_text": {"does_not_equal": value}}
        elif operator == "~" or operator == "in":
            return {**base, "rich_text": {"contains": value}}
        elif operator == "!~" or operator == "not in":
            return {**base, "rich_text": {"does_not_contain": value}}
        else:
            msg = f"Operator '{operator}' not supported for text properties"
            raise ValueError(msg)

    def _build_number_condition(
        self, base: dict[str, Any], operator: str, value: str
    ) -> dict[str, Any]:
        """Build condition for number properties."""
        try:
            num_value = float(value)
        except ValueError:
            raise ValueError(f"Invalid number value: {value}")

        if operator == "=":
            return {**base, "number": {"equals": num_value}}
        elif operator == "!=":
            return {**base, "number": {"does_not_equal": num_value}}
        elif operator == ">":
            return {**base, "number": {"greater_than": num_value}}
        elif operator == "<":
            return {**base, "number": {"less_than": num_value}}
        elif operator == ">=":
            return {**base, "number": {"greater_than_or_equal_to": num_value}}
        elif operator == "<=":
            return {**base, "number": {"less_than_or_equal_to": num_value}}
        else:
            msg = f"Operator '{operator}' not supported for number properties"
            raise ValueError(msg)

    def _build_select_condition(
        self, base: dict[str, Any], operator: str, value: str
    ) -> dict[str, Any]:
        """Build condition for select properties."""
        if operator == "=" or operator == "~":
            return {**base, "select": {"equals": value}}
        elif operator == "!=":
            return {**base, "select": {"does_not_equal": value}}
        elif operator == "in":
            # Handle comma-separated values for 'in' operator
            values = [v.strip().strip("'\"") for v in value.split(",")]
            if len(values) == 1:
                return {**base, "select": {"equals": values[0]}}
            else:
                # Create OR condition for multiple values
                conditions = []
                for v in values:
                    conditions.append({**base, "select": {"equals": v}})
                return {"or": conditions}
        elif operator == "not in":
            # Handle comma-separated values for 'not in' operator
            values = [v.strip().strip("'\"") for v in value.split(",")]
            if len(values) == 1:
                return {**base, "select": {"does_not_equal": values[0]}}
            else:
                # Create AND condition for multiple values (not equal to any)
                conditions = []
                for v in values:
                    conditions.append({**base, "select": {"does_not_equal": v}})
                return {"and": conditions}
        else:
            msg = f"Operator '{operator}' not supported for select properties"
            raise ValueError(msg)

    def _build_multiselect_condition(
        self, base: dict[str, Any], operator: str, value: str
    ) -> dict[str, Any]:
        """Build condition for multi-select properties."""
        if operator == "=" or operator == "~":
            return {**base, "multi_select": {"contains": value}}
        elif operator == "!=" or operator == "!~":
            return {**base, "multi_select": {"does_not_contain": value}}
        elif operator == "in":
            # Handle comma-separated values for 'in' operator
            values = [v.strip().strip("'\"") for v in value.split(",")]
            if len(values) == 1:
                return {**base, "multi_select": {"contains": values[0]}}
            else:
                # Create OR condition for multiple values
                conditions = []
                for v in values:
                    conditions.append({**base, "multi_select": {"contains": v}})
                return {"or": conditions}
        elif operator == "not in":
            # Handle comma-separated values for 'not in' operator
            values = [v.strip().strip("'\"") for v in value.split(",")]
            if len(values) == 1:
                return {**base, "multi_select": {"does_not_contain": values[0]}}
            else:
                # Create AND condition for multiple values
                conditions = []
                for v in values:
                    conditions.append({**base, "multi_select": {"does_not_contain": v}})
                return {"and": conditions}
        else:
            msg = f"Operator '{operator}' not supported for multi-select properties"
            raise ValueError(msg)

    def _build_date_condition(
        self, base: dict[str, Any], operator: str, value: str
    ) -> dict[str, Any]:
        """Build condition for date properties."""
        # Notion expects ISO date format
        date_value = self._parse_date_value(value)

        if operator == "=":
            return {**base, "date": {"equals": date_value}}
        elif operator == "!=":
            return {**base, "date": {"does_not_equal": date_value}}
        elif operator == ">":
            return {**base, "date": {"after": date_value}}
        elif operator == "<":
            return {**base, "date": {"before": date_value}}
        elif operator == ">=":
            return {**base, "date": {"on_or_after": date_value}}
        elif operator == "<=":
            return {**base, "date": {"on_or_before": date_value}}
        else:
            msg = f"Operator '{operator}' not supported for date properties"
            raise ValueError(msg)

    def _build_checkbox_condition(
        self, base: dict[str, Any], operator: str, value: str
    ) -> dict[str, Any]:
        """Build condition for checkbox properties."""
        bool_value = value.lower() in ("true", "yes", "1", "✓", "checked")

        if operator == "=":
            return {**base, "checkbox": {"equals": bool_value}}
        elif operator == "!=":
            return {**base, "checkbox": {"does_not_equal": bool_value}}
        else:
            msg = f"Operator '{operator}' not supported for checkbox properties"
            raise ValueError(msg)

    def _build_status_condition(
        self, base: dict[str, Any], operator: str, value: str
    ) -> dict[str, Any]:
        """Build condition for status properties."""
        if operator == "=" or operator == "~":
            return {**base, "status": {"equals": value}}
        elif operator == "!=":
            return {**base, "status": {"does_not_equal": value}}
        elif operator == "in":
            # Handle comma-separated values for 'in' operator
            values = [v.strip().strip("'\"") for v in value.split(",")]
            if len(values) == 1:
                return {**base, "status": {"equals": values[0]}}
            else:
                # Create OR condition for multiple values
                conditions = []
                for v in values:
                    conditions.append({**base, "status": {"equals": v}})
                return {"or": conditions}
        elif operator == "not in":
            # Handle comma-separated values for 'not in' operator
            values = [v.strip().strip("'\"") for v in value.split(",")]
            if len(values) == 1:
                return {**base, "status": {"does_not_equal": values[0]}}
            else:
                # Create AND condition for multiple values
                conditions = []
                for v in values:
                    conditions.append({**base, "status": {"does_not_equal": v}})
                return {"and": conditions}
        else:
            msg = f"Operator '{operator}' not supported for status properties"
            raise ValueError(msg)

    def _parse_date_value(self, value: str) -> str:
        """Parse and normalize date value."""
        # Handle various date formats
        import datetime

        # Common date formats
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in formats:
            try:
                parsed = datetime.datetime.strptime(value, fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # If no format matches, return as-is (might be relative like "today")
        return value

    def _invert_condition(self, condition: dict[str, Any]) -> dict[str, Any]:
        """Invert a condition for NOT operations."""
        # This is a simplified inversion - Notion's API has limitations
        # For complex cases, we might need to restructure the query
        if "and" in condition:
            # NOT(A AND B) = NOT(A) OR NOT(B)
            inverted = [self._invert_condition(c) for c in condition["and"]]
            return {"or": inverted}
        elif "or" in condition:
            # NOT(A OR B) = NOT(A) AND NOT(B)
            inverted = [self._invert_condition(c) for c in condition["or"]]
            return {"and": inverted}
        else:
            # For atomic conditions, we need to map to opposite operations
            # This is complex and may not be fully supported by Notion API
            return condition  # Simplified - return original
