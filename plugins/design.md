# Plugin Interface Design Document

## Overview

This document outlines the design for a plugin system in the Funsense project. The plugin system will allow for extensible processing of analyzed email data, enabling the detection of specific information of interest and generation of additional content based on that information.

## Goals

1. Create a simple, extensible plugin interface
2. Allow plugins to process analyzed email objects
3. Enable plugins to detect information of interest in emails
4. Provide a mechanism for plugins to generate content based on detected information
5. Integrate generated content back into the original email object

## Plugin Interface

### Core Components

1. **Plugin Registry**: Central system for registering and managing plugins
2. **Plugin Base Class**: Abstract base class that all plugins must implement
3. **Plugin Processor**: Component that routes email objects through registered plugins
4. **Plugin Result Model**: Standardized structure for plugin output

### Plugin Base Class

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BasePlugin(ABC):
    """Base class that all plugins must inherit from."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the plugin."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of the plugin."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what the plugin does."""
        pass
    
    @abstractmethod
    def detect(self, email_data: Dict[str, Any]) -> bool:
        """
        Detect if this plugin should process the email data.
        
        Args:
            email_data: The analyzed email object
            
        Returns:
            True if the plugin should process this email, False otherwise
        """
        pass
    
    @abstractmethod
    def generate(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate content based on the email data.
        
        Args:
            email_data: The analyzed email object
            
        Returns:
            A dictionary containing the generated content
        """
        pass
```

### Plugin Registry

```python
class PluginRegistry:
    """Registry for managing plugins."""
    
    def __init__(self):
        self._plugins = {}
    
    def register(self, plugin: BasePlugin) -> None:
        """
        Register a plugin.
        
        Args:
            plugin: The plugin to register
        """
        self._plugins[plugin.name] = plugin
    
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """
        Get a plugin by name.
        
        Args:
            name: The name of the plugin
            
        Returns:
            The plugin if found, None otherwise
        """
        return self._plugins.get(name)
    
    def get_all_plugins(self) -> List[BasePlugin]:
        """
        Get all registered plugins.
        
        Returns:
            List of all registered plugins
        """
        return list(self._plugins.values())
```

### Plugin Processor

```python
class PluginProcessor:
    """Processes email data through registered plugins."""
    
    def __init__(self, registry: PluginRegistry):
        self.registry = registry
    
    def process(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an email through all registered plugins.
        
        Args:
            email_data: The analyzed email object
            
        Returns:
            The email object with plugin results added
        """
        # Make a copy of the email data to avoid modifying the original
        result = email_data.copy()
        
        # Initialize plugins field if it doesn't exist
        if 'plugins' not in result:
            result['plugins'] = {}
        
        # Process through each plugin
        for plugin in self.registry.get_all_plugins():
            # Check if the plugin should process this email
            if plugin.detect(email_data):
                # Generate content and add to plugins field
                plugin_result = plugin.generate(email_data)
                result['plugins'][plugin.name] = plugin_result
        
        return result
```

## Plugin Flow

1. **Initialization**:
   - The application loads and registers all available plugins
   - The plugin registry maintains references to all registered plugins

2. **Email Processing**:
   - An analyzed email object is passed to the plugin processor
   - The processor iterates through all registered plugins

3. **Detection**:
   - Each plugin's `detect()` method is called with the email data
   - The plugin examines the email to determine if it contains information of interest
   - If the plugin detects relevant information, it returns `True`

4. **Generation**:
   - For plugins that returned `True` from `detect()`, the `generate()` method is called
   - The plugin processes the email data and generates additional content
   - The generated content is returned as a dictionary

5. **Integration**:
   - The plugin processor adds the generated content to the email object under a `plugins` field
   - The plugin's name is used as the key for its generated content
   - The updated email object is returned

## Example Plugin Implementation

```python
class ArxivPaperPlugin(BasePlugin):
    """Plugin for detecting and processing arXiv paper references in emails."""
    
    @property
    def name(self) -> str:
        return "arxiv_paper"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Detects arXiv paper references and generates additional metadata"
    
    def detect(self, email_data: Dict[str, Any]) -> bool:
        # Check if email contains arXiv paper references
        content = email_data.get("post_content_en", "")
        return "arxiv-id:" in content or "arxiv.org/abs/" in content
    
    def generate(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        # Extract arXiv IDs
        content = email_data.get("post_content_en", "")
        arxiv_ids = []
        
        # Simple regex to extract arXiv IDs
        import re
        pattern = r"arxiv-id:\s*(\d+\.\d+)|arxiv\.org\/abs\/(\d+\.\d+)"
        matches = re.finditer(pattern, content)
        
        for match in matches:
            arxiv_id = match.group(1) or match.group(2)
            if arxiv_id:
                arxiv_ids.append(arxiv_id)
        
        # Generate additional metadata
        return {
            "detected_arxiv_ids": arxiv_ids,
            "paper_count": len(arxiv_ids),
            "generated_at": "2025-04-26T22:05:00-07:00",
            "summary": "Found references to arXiv papers in this email"
        }
```

## Usage Example

```python
# Initialize the plugin system
registry = PluginRegistry()
processor = PluginProcessor(registry)

# Register plugins
registry.register(ArxivPaperPlugin())

# Process an email
with open('email_analyzed.json', 'r') as f:
    email_data = json.load(f)

# Process the email through all plugins
processed_email = processor.process(email_data)

# Save the processed email
with open('email_processed.json', 'w') as f:
    json.dump(processed_email, f, indent=2)
```

## Plugin Directory Structure

```
plugins/
├── __init__.py
├── base.py           # Contains BasePlugin and registry classes
├── processor.py      # Contains PluginProcessor class
├── registry.py       # Contains PluginRegistry class
├── models.py         # Contains data models for plugin results
└── implementations/  # Directory for plugin implementations
    ├── __init__.py
    ├── arxiv_plugin.py
    └── ...
```

## Future Enhancements

1. **Plugin Configuration**: Add support for plugin-specific configuration
2. **Plugin Dependencies**: Allow plugins to depend on other plugins
3. **Async Processing**: Support asynchronous plugin processing
4. **Plugin Versioning**: Better handling of plugin versions and compatibility
5. **Plugin Marketplace**: A system for discovering and installing third-party plugins
6. **Plugin Metrics**: Collect metrics on plugin performance and usage

## Conclusion

This plugin system provides a flexible framework for extending the functionality of the Funsense email analysis system. By following a simple interface, developers can create plugins that detect specific information in emails and generate additional content based on that information.
