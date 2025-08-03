#!/usr/bin/env python3
"""
MDX Utility Functions - Refactored Version

Improved utility functions for MDX dictionary processing.
"""

import logging
import re
from pathlib import Path
from typing import Any

try:
    from .file_util import file_util_get_files, file_util_is_ext, file_util_read_text
except ImportError:
    # Handle missing file_util module gracefully
    def file_util_get_files(root_dir: str | Path, result_list: list[str]) -> None:
        """Stub implementation for file discovery."""
        pass

    def file_util_is_ext(path: str | Path, ext: str) -> bool:
        """Stub implementation for extension checking."""
        return False

    def file_util_read_text(path: str | Path) -> str:
        """Stub implementation for text reading."""
        return ""


logger = logging.getLogger(__name__)


class LemmaProcessor:
    """Handle word lemmatization safely."""

    def __init__(self):
        """Initialize lemma processor."""
        self._lemma_cache = {}

    def get_lemma(self, word: str) -> str:
        """
        Get word lemma safely without external process calls.

        This is a simplified version. For production, consider using
        libraries like spaCy, NLTK, or other NLP tools.
        """
        if word in self._lemma_cache:
            return self._lemma_cache[word]

        # Simple lemmatization rules (expand as needed)
        lemma = self._simple_lemmatize(word)
        self._lemma_cache[word] = lemma
        return lemma

    def _simple_lemmatize(self, word: str) -> str:
        """Simple lemmatization rules."""
        word = word.lower().strip()

        # Handle common English suffixes
        if word.endswith("ies") and len(word) > 4:
            return word[:-3] + "y"
        elif word.endswith("s") and len(word) > 3 and not word.endswith("ss"):
            return word[:-1]
        elif word.endswith("ed") and len(word) > 3:
            return word[:-2]
        elif word.endswith("ing") and len(word) > 4:
            return word[:-3]

        return word


class MDXContentProcessor:
    """Process MDX content with proper error handling."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize content processor."""
        self.base_path = base_path or Path(__file__).parent
        self.resource_path = self.base_path / "mdx"
        self.lemma_processor = LemmaProcessor()

    def get_definition_mdx(self, word: str, builder: Any) -> list[bytes]:
        """
        Get MDX dictionary definition for a word.

        Args:
            word: The word to look up
            builder: The MDX IndexBuilder instance

        Returns:
            List of bytes containing the definition
        """
        if not word or not builder:
            return [b"<h1>Error: Invalid input</h1>"]

        try:
            # Initial lookup
            content = builder.mdx_lookup(word)

            # Try lemmatized form if no results
            if not content:
                lemma = self.lemma_processor.get_lemma(word)
                if lemma != word:
                    logger.debug(f"Trying lemma: {lemma} for word: {word}")
                    content = builder.mdx_lookup(lemma)

            # Handle link references
            if content:
                processed_content = self._process_content_links(content, builder)
            else:
                processed_content = [f"<h1>No definition found for: {word}</h1>"]

            # Combine content and inject resources
            final_content = self._combine_content_with_resources(processed_content)

            return [final_content.encode("utf-8")]

        except Exception as e:
            logger.error(f"Error processing word '{word}': {e}")
            return [f"<h1>Error processing word: {word}</h1>".encode()]

    def _process_content_links(self, content: list[str], builder: Any) -> list[str]:
        """Process @@@LINK= references in content."""
        processed = []

        for item in content:
            # Check for link references
            pattern = re.compile(r"@@@LINK=([\w\s]*)")
            match = pattern.match(item)

            if match:
                link = match.group(1).strip()
                logger.debug(f"Following link: {link}")
                linked_content = builder.mdx_lookup(link)
                processed.extend(linked_content)
            else:
                processed.append(item)

        return processed

    def _combine_content_with_resources(self, content: list[str]) -> str:
        """Combine content with injected resources."""
        # Join content
        main_content = "".join(content)

        # Clean up content
        main_content = main_content.replace("\r\n", "").replace("entry:/", "")

        # Add injection resources
        injection_html = self._get_injection_html()

        return main_content + injection_html

    def _get_injection_html(self) -> str:
        """Get HTML injection resources."""
        injection_html = ""

        if not self.resource_path.exists():
            return injection_html

        try:
            injection_files: list[str] = []
            file_util_get_files(str(self.resource_path), injection_files)

            for file_path in injection_files:
                if file_util_is_ext(file_path, "html"):
                    try:
                        content = file_util_read_text(file_path)
                        injection_html += content
                    except Exception as e:
                        logger.warning(
                            f"Failed to read injection file {file_path}: {e}"
                        )

        except Exception as e:
            logger.warning(f"Failed to process injection files: {e}")

        return injection_html

    def get_definition_mdd(self, path: str, builder: Any) -> list[bytes]:
        """
        Get MDD resource data.

        Args:
            path: Resource path
            builder: The MDX IndexBuilder instance

        Returns:
            List of bytes containing the resource data
        """
        if not path or not builder:
            return []

        try:
            # Normalize path separators
            normalized_path = path.replace("/", "\\")
            content = builder.mdd_lookup(normalized_path)

            if content and content[0]:  # Check if content is not empty
                logger.debug(
                    f"Found content in MDD for {path}, size: {len(content[0])}"
                )
                return [content[0]]
            else:
                logger.debug(
                    f"MDD content empty or not found for {path}, trying filesystem fallback"
                )
                # Fallback: try to read from filesystem if MDD resource is empty or not found
                return self._try_filesystem_fallback(path, builder)

        except Exception as e:
            logger.error(f"Error getting MDD resource '{path}': {e}")
            # Try filesystem fallback on error
            return self._try_filesystem_fallback(path, builder)

    def _try_filesystem_fallback(self, path: str, builder: Any) -> list[bytes]:
        """
        Try to read resource from filesystem as fallback.

        Args:
            path: Resource path
            builder: The MDX IndexBuilder instance

        Returns:
            List of bytes containing the resource data from filesystem
        """
        try:
            from pathlib import Path

            # Get the directory containing the MDX file
            mdx_path = Path(builder._mdx_file)
            dict_dir = mdx_path.parent

            # Clean the path - remove leading slashes and backslashes
            clean_path = path.lstrip("/\\")

            # Try to find the file in the same directory
            resource_path = dict_dir / clean_path

            logger.debug(f"Trying filesystem path: {resource_path} (original: {path})")

            if resource_path.exists() and resource_path.is_file():
                logger.debug(f"Found resource in filesystem: {resource_path}")
                with open(resource_path, "rb") as f:
                    return [f.read()]
            else:
                logger.debug(f"Resource not found in filesystem: {resource_path}")
                return []

        except Exception as e:
            logger.debug(f"Filesystem fallback failed for '{path}': {e}")
            return []


# Global processor instance for backward compatibility
_processor = MDXContentProcessor()


def get_definition_mdx(word: str, builder: Any) -> list[bytes]:
    """Backward compatible function for MDX lookup."""
    return _processor.get_definition_mdx(word, builder)


def get_definition_mdd(path: str, builder: Any) -> list[bytes]:
    """Backward compatible function for MDD lookup."""
    return _processor.get_definition_mdd(path, builder)
