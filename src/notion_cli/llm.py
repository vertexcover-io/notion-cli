"""LLM service for natural language processing and structured data generation."""

import json
import os
from typing import Any

import litellm
import typer
from dotenv import load_dotenv
from pydantic import BaseModel
from rich.console import Console

from .config import ConfigManager

# Load environment variables from .env file
load_dotenv()


class LLMConfig(BaseModel):
    """Configuration for LLM service."""

    model: str = "gpt-4.1-mini"
    temperature: float = 0.1
    max_tokens: int = 2000


class LLMService:
    """Service for interacting with LLM models via LiteLLM."""

    def __init__(
        self, config: LLMConfig | None = None, config_manager: ConfigManager | None = None
    ) -> None:
        """Initialize the LLM service."""
        self.config_manager = config_manager or ConfigManager()

        # Get model from config or use provided config
        if config:
            self.config = config
        else:
            # Load model and API key from config
            model, api_key = self.config_manager.get_llm_config()
            if not model:
                # Prompt for model and API key if not configured
                model, api_key = self._prompt_for_llm_config()
                if model and api_key:
                    self.config_manager.set_llm_config(model, api_key)
            self.config = LLMConfig(model=model or "gpt-4.1-mini")

        # Set up LiteLLM
        litellm.set_verbose = False

        # Set up API key
        self._setup_api_key()

    def _setup_api_key(self) -> None:
        """Set up API key for the configured model."""
        model, api_key = self.config_manager.get_llm_config()

        if not api_key:
            return

        model_lower = model.lower() if model else ""

        if "gpt" in model_lower or "openai" in model_lower:
            os.environ["OPENAI_API_KEY"] = api_key
        elif "claude" in model_lower or "anthropic" in model_lower:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        elif "gemini" in model_lower or "google" in model_lower:
            os.environ["GOOGLE_API_KEY"] = api_key

    def _prompt_for_llm_config(self) -> tuple[str, str]:
        """Prompt user for LLM model and API key."""
        console = Console()

        console.print("\n🤖 LLM Configuration Required", style="bold cyan")
        console.print(
            "To use AI features, please configure your preferred LLM model and API key.\n",
            style="dim",
        )

        # Show available models
        console.print("Available models:", style="bold")
        console.print("1. gpt-4.1-mini (OpenAI) - Fast and cost-effective")
        console.print("2. gpt-4o (OpenAI) - More capable, higher cost")
        console.print("3. claude-3-haiku-20240307 (Anthropic) - Fast and efficient")
        console.print("4. claude-3-sonnet-20240229 (Anthropic) - Balanced performance")
        console.print("5. gemini-pro (Google) - Google's latest model")
        console.print("6. Other (enter custom model name)")

        while True:
            choice = typer.prompt("\nSelect model (1-6)", type=int, default=1)

            if choice == 1:
                model = "gpt-4.1-mini"
                provider_name = "OpenAI"
                key_url = "https://platform.openai.com/api-keys"
                break
            elif choice == 2:
                model = "gpt-4o"
                provider_name = "OpenAI"
                key_url = "https://platform.openai.com/api-keys"
                break
            elif choice == 3:
                model = "claude-3-haiku-20240307"
                provider_name = "Anthropic"
                key_url = "https://console.anthropic.com/account/keys"
                break
            elif choice == 4:
                model = "claude-3-sonnet-20240229"
                provider_name = "Anthropic"
                key_url = "https://console.anthropic.com/account/keys"
                break
            elif choice == 5:
                model = "gemini-pro"
                provider_name = "Google"
                key_url = "https://console.cloud.google.com/apis/credentials"
                break
            elif choice == 6:
                model = typer.prompt("Enter model name")
                provider_name = "Custom"
                key_url = None
                break
            else:
                console.print("❌ Please select 1-6", style="red")
                continue

        console.print(f"\n🔑 {provider_name} API key required for model '{model}'", style="yellow")
        if key_url:
            console.print(f"Get your API key from: {key_url}", style="blue underline")

        api_key = typer.prompt(f"\nEnter your {provider_name} API key", hide_input=True)

        if not api_key.strip():
            console.print("❌ API key is required", style="red")
            raise typer.Exit(1)

        console.print(f"✅ LLM configuration saved: {model}", style="green")
        return model, api_key.strip()

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
            "- For properties with spaces in names, use the exact name\n"
            "- Use CONTAINS (~) for partial names/text matching unless exact match is clearly intended\n"
            "- Use EQUALS (=) only when the full exact value is provided\n\n"
            "Examples:\n"
            "- 'Add resume to John Doe' → Name~John Doe (contains, in case full name differs)\n"
            "- 'Update status for urgent tasks' → Tags~urgent\n"
            "- 'Set linkedin for aman' → Name~aman (partial name match)\n"
            "- 'Set priority for Project Alpha' → Name~Project Alpha\n"
            "- 'Update completed tasks' → Status=Completed (exact status value)\n\n"
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
    config_manager = ConfigManager()
    return LLMService(config_manager=config_manager)
