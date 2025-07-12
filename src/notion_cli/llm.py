"""LLM service for natural language processing and structured data generation."""

import json
import os
from typing import Any

import litellm
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()


class LLMConfig(BaseModel):
    """Configuration for LLM service."""

    model: str = "gpt-4.1"
    temperature: float = 0.1
    max_tokens: int = 2000


class LLMService:
    """Service for interacting with LLM models via LiteLLM."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        """Initialize the LLM service."""
        self.config = config or LLMConfig()

        # Set up LiteLLM
        litellm.set_verbose = False

        # Check for API keys
        self._check_api_keys()

    def _check_api_keys(self) -> None:
        """Check if required API keys are available."""
        model_lower = self.config.model.lower()

        if "gpt" in model_lower or "openai" in model_lower:
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable.",
                )
        elif "claude" in model_lower or "anthropic" in model_lower:
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise ValueError(
                    "Anthropic API key not found. " "Set ANTHROPIC_API_KEY environment variable.",
                )
        elif "gemini" in model_lower or "google" in model_lower:
            if not os.getenv("GOOGLE_API_KEY"):
                raise ValueError(
                    "Google API key not found. Set GOOGLE_API_KEY environment variable.",
                )

    def generate_structured_data(
        self,
        prompt: str,
        schema: dict[str, Any],
        context: str = "",
        allow_revision: bool = False,
        files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate structured data based on a prompt and schema."""
        return self._generate_with_revision(
            prompt,
            schema,
            context,
            allow_revision,
            self._structured_data_generator,
            files=files,
        )

    def _generate_with_revision(
        self,
        prompt: str,
        schema: dict[str, Any],
        context: str,
        allow_revision: bool,
        generator_func,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate data with optional revision capability."""
        import typer
        from rich.console import Console
        from rich.table import Table

        console = Console()
        current_prompt = prompt

        while True:
            try:
                # Generate using the provided generator function
                result = generator_func(current_prompt, schema, context, **kwargs)

                if not allow_revision:
                    return result

                # Show the generated result
                console.print("\n🤖 Generated Result:", style="bold cyan")
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="white")

                for prop_name, value in result.items():
                    if value is not None:
                        display_value = str(value)
                        if isinstance(value, list):
                            display_value = ", ".join(str(v) for v in value)
                        table.add_row(prop_name, display_value)

                console.print(table)

                # Ask user if they want to revise
                console.print("\nOptions:", style="bold")
                console.print("1. Accept this result")
                console.print("2. Revise the prompt")
                console.print("3. Cancel")

                choice = typer.prompt("Choose an option (1-3)", type=int, default=1)

                if choice == 1:
                    return result
                elif choice == 2:
                    console.print(f"\nCurrent prompt: {current_prompt}", style="dim")
                    new_prompt = typer.prompt("Enter revised prompt")
                    if new_prompt.strip():
                        current_prompt = new_prompt
                        console.print(
                            "🔄 Regenerating with revised prompt...",
                            style="yellow",
                        )
                        continue
                    else:
                        console.print(
                            "❌ Empty prompt, keeping original",
                            style="yellow",
                        )
                        continue
                elif choice == 3:
                    raise ValueError("Operation cancelled by user")
                else:
                    console.print("❌ Invalid choice, please select 1-3", style="red")
                    continue

            except json.JSONDecodeError as e:
                if allow_revision:
                    console.print(
                        f"❌ Failed to parse LLM response as JSON: {e}",
                        style="red",
                    )
                    console.print(
                        "🔄 Please revise your prompt to be more specific",
                        style="yellow",
                    )
                    new_prompt = typer.prompt("Enter revised prompt")
                    if new_prompt.strip():
                        current_prompt = new_prompt
                        continue
                    else:
                        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
                else:
                    raise ValueError(f"Failed to parse LLM response as JSON: {e}")
            except Exception as e:
                if allow_revision:
                    console.print(f"❌ LLM request failed: {e}", style="red")
                    console.print("🔄 Please revise your prompt", style="yellow")
                    new_prompt = typer.prompt("Enter revised prompt")
                    if new_prompt.strip():
                        current_prompt = new_prompt
                        continue
                    else:
                        raise ValueError(f"LLM request failed: {e}")
                else:
                    raise ValueError(f"LLM request failed: {e}")

    def _structured_data_generator(
        self,
        prompt: str,
        schema: dict[str, Any],
        context: str = "",
        files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Internal method to generate structured data."""
        file_context = ""
        if files:
            import os

            file_info = []
            for file_path in files:
                if os.path.exists(file_path):
                    file_name = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)
                    file_info.append(f"- {file_name} ({file_size} bytes)")
                else:
                    file_info.append(f"- {file_path} (file not found)")

            if file_info:
                file_context = "\nFiles to be uploaded:\n" + "\n".join(file_info) + "\n"

        system_prompt = (
            "You are a helpful assistant that converts natural language "
            "prompts into structured data.\n\n"
            f"Context: {context}{file_context}\n"
            "You must respond with valid JSON that matches the provided "
            "schema exactly.\n"
            "Do not include any additional text or explanations - "
            "only the JSON response.\n\n"
            f"Schema:\n{json.dumps(schema, indent=2)}\n\n"
            "Guidelines:\n"
            "- Use appropriate data types for each field\n"
            "- For dates, use ISO format (YYYY-MM-DD)\n"
            "- For select fields, use exact values from the schema "
            "options if provided\n"
            "- For multi-select fields, return an array of values\n"
            "- For checkbox fields, return boolean values\n"
            "- For file fields, use the special value '__FILE__' to indicate "
            "a file should be uploaded\n"
            "- Leave fields empty/null if not mentioned in the prompt\n"
            "- Be conservative - only fill fields you're confident about"
        )

        user_prompt = f"""Convert this prompt into structured data following the schema:

Prompt: {prompt}

Respond with valid JSON only:"""

        response = litellm.completion(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return json.loads(content)

    def generate_filters_from_prompt(
        self,
        prompt: str,
        properties: dict[str, Any],
    ) -> str:
        """Generate filter expressions from natural language."""

        # Create a simplified schema of properties for the LLM
        prop_info = {}
        for name, prop_data in properties.items():
            prop_type = prop_data.get("type", "")
            prop_info[name] = {"type": prop_type}

            # Add options for select fields
            if prop_type == "select" and "select" in prop_data:
                options = prop_data["select"].get("options", [])
                prop_info[name]["options"] = [opt.get("name", "") for opt in options]
            elif prop_type == "multi_select" and "multi_select" in prop_data:
                options = prop_data["multi_select"].get("options", [])
                prop_info[name]["options"] = [opt.get("name", "") for opt in options]

        system_prompt = (
            "You are a database query assistant. Your job is to identify which "
            "database entries should be updated, NOT to filter by what will be changed.\n\n"
            f"Available properties:\n{json.dumps(prop_info, indent=2)}\n\n"
            "Filter syntax:\n"
            "- Equality: property=value\n"
            "- Not equal: property!=value\n"
            "- Contains: property~value\n"
            "- Does not contain: property!~value\n"
            "- Greater than: property>value\n"
            "- Less than: property<value\n"
            "- Greater than or equal: property>=value\n"
            "- Less than or equal: property<=value\n"
            "- In list: property in 'value1,value2,value3'\n"
            "- Not in list: property not in 'value1,value2,value3'\n"
            "- Multiple conditions: condition1,condition2 (AND)\n"
            "- OR conditions: OR(condition1,condition2)\n"
            "- NOT conditions: NOT(condition)\n\n"
            "Important rules:\n"
            "- Focus on WHO/WHAT entries to target, not what changes to make\n"
            "- For requests like 'Add X to Y' or 'Update X for Y', filter by Y's identifier\n"
            "- Do NOT filter by properties that will be updated/added\n"
            "- Use exact property names from the available properties list\n"
            "- For properties with spaces in names, use the exact name\n\n"
            "Examples:\n"
            "- 'Add resume to John Doe' → Name=John Doe\n"
            "- 'Update status for urgent tasks' → Tags~urgent\n"
            "- 'Set priority for Project Alpha' → Name=Project Alpha\n\n"
            "CRITICAL: Respond with ONLY the filter expression. No explanations, "
            "no parentheses with examples, no additional text."
        )

        user_prompt = f"""Convert this request into a filter expression:

{prompt}

Filter expression:"""

        try:
            response = litellm.completion(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise ValueError(f"Failed to generate filters: {e}")

    def generate_updates_from_prompt(
        self,
        prompt: str,
        properties: dict[str, Any],
        current_data: dict[str, Any] | None = None,
        files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate update data from natural language prompt."""

        # Create schema for updates
        schema = self._create_notion_schema(properties)

        context = f"Available properties: {list(properties.keys())}"
        if current_data:
            context += f"\nCurrent data: {json.dumps(current_data, indent=2)}"

        file_context = ""
        if files:
            import os

            file_info = []
            for file_path in files:
                if os.path.exists(file_path):
                    file_name = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)
                    file_info.append(f"- {file_name} ({file_size} bytes)")
                else:
                    file_info.append(f"- {file_path} (file not found)")

            if file_info:
                file_context = "\nFiles to be uploaded:\n" + "\n".join(file_info)

        system_prompt = (
            "You are updating database entries. Convert the update request "
            "into structured data.\n\n"
            f"{context}{file_context}\n\n"
            "Only include fields that should be updated. Leave out fields that are not "
            "mentioned or should remain unchanged.\n\n"
            f"Schema for updates:\n{json.dumps(schema, indent=2)}\n\n"
            "Guidelines:\n"
            "- For file fields, use the special value '__FILE__' to indicate "
            "a file should be uploaded\n"
            "- Only include fields that need to be changed\n\n"
            "Respond with valid JSON containing only the fields to update:"
        )

        user_prompt = f"""Update request: {prompt}

JSON for updates:"""

        try:
            response = litellm.completion(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            raise ValueError(f"LLM request failed: {e}")

    def _create_notion_schema(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a JSON schema from Notion properties."""
        schema = {"type": "object", "properties": {}}

        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type", "")

            if prop_type == "title":
                schema["properties"][prop_name] = {
                    "type": "string",
                    "description": "Title/name field",
                }
            elif prop_type == "rich_text":
                schema["properties"][prop_name] = {
                    "type": "string",
                    "description": "Rich text content",
                }
            elif prop_type == "number":
                schema["properties"][prop_name] = {
                    "type": "number",
                    "description": "Numeric value",
                }
            elif prop_type == "select":
                options = []
                if "select" in prop_data and "options" in prop_data["select"]:
                    options = [opt.get("name", "") for opt in prop_data["select"]["options"]]
                schema["properties"][prop_name] = {
                    "type": "string",
                    "enum": options,
                    "description": f"Select one of: {options}",
                }
            elif prop_type == "multi_select":
                options = []
                if "multi_select" in prop_data and "options" in prop_data["multi_select"]:
                    options = [opt.get("name", "") for opt in prop_data["multi_select"]["options"]]
                schema["properties"][prop_name] = {
                    "type": "array",
                    "items": {"type": "string", "enum": options},
                    "description": f"Select multiple from: {options}",
                }
            elif prop_type == "date":
                schema["properties"][prop_name] = {
                    "type": "string",
                    "format": "date",
                    "description": "Date in YYYY-MM-DD format",
                }
            elif prop_type == "checkbox":
                schema["properties"][prop_name] = {
                    "type": "boolean",
                    "description": "True/false value",
                }
            elif prop_type == "url":
                schema["properties"][prop_name] = {
                    "type": "string",
                    "format": "uri",
                    "description": "URL address",
                }
            elif prop_type == "email":
                schema["properties"][prop_name] = {
                    "type": "string",
                    "format": "email",
                    "description": "Email address",
                }
            elif prop_type == "phone_number":
                schema["properties"][prop_name] = {
                    "type": "string",
                    "description": "Phone number",
                }
            elif prop_type == "status":
                options = []
                if "status" in prop_data and "options" in prop_data["status"]:
                    options = [opt.get("name", "") for opt in prop_data["status"]["options"]]
                schema["properties"][prop_name] = {
                    "type": "string",
                    "enum": options,
                    "description": f"Status: {options}",
                }
            elif prop_type == "files":
                schema["properties"][prop_name] = {
                    "type": "string",
                    "enum": ["__FILE__"],
                    "description": "File attachment - use '__FILE__' to indicate a file should be uploaded",
                }
            else:
                # Default to string for unknown types
                schema["properties"][prop_name] = {
                    "type": "string",
                    "description": f"Field of type {prop_type}",
                }

        return schema


def get_default_llm_service() -> LLMService:
    """Get a default LLM service instance."""
    # Allow environment variable to override default model
    model = os.getenv("NOTION_CLI_LLM_MODEL", "gpt-3.5-turbo")
    config = LLMConfig(model=model)
    return LLMService(config)
