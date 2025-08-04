#!/usr/bin/env python3
"""
Modern file utility functions for MDX Server.

Provides efficient file I/O operations with proper error handling
and type safety for Python 3.13+.
"""

from pathlib import Path


def read_text_lines(path: str | Path) -> list[str]:
    """Read text file and return list of lines.

    Args:
        path: Path to the text file

    Returns:
        List of lines from the file

    Raises:
        FileNotFoundError: If the file doesn't exist
        UnicodeDecodeError: If the file has encoding issues
    """
    with open(path, encoding="utf-8") as f:
        return f.readlines()


def read_text_lines_stripped(path: str | Path) -> list[str]:
    """Read text file and return list of stripped lines.

    Args:
        path: Path to the text file

    Returns:
        List of stripped lines from the file

    Raises:
        FileNotFoundError: If the file doesn't exist
        UnicodeDecodeError: If the file has encoding issues
    """
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f]


def read_text(path: str | Path) -> str:
    """Read entire text file content as string.

    Args:
        path: Path to the text file

    Returns:
        Complete file content as string

    Raises:
        FileNotFoundError: If the file doesn't exist
        UnicodeDecodeError: If the file has encoding issues
    """
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path: str | Path, text: str) -> None:
    """Write text content to file.

    Args:
        path: Path to the output file
        text: Text content to write

    Raises:
        PermissionError: If no write permission
        OSError: If other I/O error occurs
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_bytes(path: str | Path) -> bytes:
    """Read entire binary file content.

    Args:
        path: Path to the binary file

    Returns:
        Complete file content as bytes

    Raises:
        FileNotFoundError: If the file doesn't exist
        OSError: If other I/O error occurs
    """
    with open(path, "rb") as f:
        return f.read()


def get_file_extension(path: str | Path) -> str:
    """Get file extension without the dot.

    Args:
        path: File path

    Returns:
        File extension without leading dot

    Example:
        >>> get_file_extension("/path/file.txt")
        'txt'
    """
    return Path(path).suffix[1:] if Path(path).suffix else ""


def get_filename(path: str | Path) -> str:
    """Get filename from path.

    Args:
        path: File path

    Returns:
        Filename without directory path

    Example:
        >>> get_filename("/path/to/file.txt")
        'file.txt'
    """
    return Path(path).name


def has_extension(path: str | Path, ext: str) -> bool:
    """Check if file has specified extension.

    Args:
        path: File path
        ext: Extension to check (without dot)

    Returns:
        True if file has the specified extension

    Example:
        >>> has_extension("/path/file.txt", "txt")
        True
    """
    return get_file_extension(path).lower() == ext.lower()


def get_all_files(root_dir: str | Path) -> list[str]:
    """Get all files recursively from directory.

    Args:
        root_dir: Root directory to search

    Returns:
        List of all file paths found

    Raises:
        FileNotFoundError: If root directory doesn't exist
        PermissionError: If no read permission for directory
    """
    root_path = Path(root_dir)
    if not root_path.exists():
        raise FileNotFoundError(f"Directory does not exist: {root_dir}")

    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root_dir}")

    return [str(p) for p in root_path.rglob("*") if p.is_file()]


def path_exists(path: str | Path) -> bool:
    """Check if file or directory exists.

    Args:
        path: Path to check

    Returns:
        True if path exists
    """
    return Path(path).exists()


def delete_file(path: str | Path) -> bool:
    """Delete file if it exists.

    Args:
        path: Path to file to delete

    Returns:
        True if file was deleted, False if it didn't exist

    Raises:
        PermissionError: If no permission to delete
        OSError: If other error occurs during deletion
    """
    file_path = Path(path)
    if file_path.exists() and file_path.is_file():
        file_path.unlink()
        return True
    return False


def delete_files_by_extension(directory: str | Path, ext: str) -> int:
    """Delete all files with specified extension in directory.

    Args:
        directory: Directory to search
        ext: File extension to delete (without dot)

    Returns:
        Number of files deleted

    Raises:
        FileNotFoundError: If directory doesn't exist
        PermissionError: If no permission to delete files
    """
    if not directory or not ext:
        return 0

    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    deleted_count = 0
    for file_path in dir_path.rglob(f"*.{ext}"):
        if file_path.is_file():
            file_path.unlink()
            deleted_count += 1

    return deleted_count


# Backward compatibility aliases - deprecated, use new names instead
def file_util_get_files(root_dir: str | Path, result_list: list[str]) -> None:
    """Deprecated: Use get_all_files() instead."""
    result_list.extend(get_all_files(root_dir))


file_util_read_text = read_text
file_util_read_byte = read_bytes
file_util_get_ext = get_file_extension
file_util_is_ext = has_extension
file_util_is_exists = path_exists
