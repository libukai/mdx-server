#!/usr/bin/env python3
"""
MDict Query Interface - Modern implementation for Python 3.13+.

Provides a clean interface for querying MDX dictionary files.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import zlib
from pathlib import Path

# from struct import pack  # Unused after modernization
from .readmdict import MDD, MDX

# Note: LZO compression support has been removed as it's rarely used in modern MDX files

version = "1.1"


class IndexBuilder:
    """Build and maintain indexes for MDX dictionary files."""

    def __init__(
        self,
        fname: str | Path,
        encoding: str = "",
        passcode: str | None = None,
        force_rebuild: bool = False,
        enable_history: bool = False,
        sql_index: bool = True,
        check: bool = False,
    ) -> None:
        """Initialize IndexBuilder with modern type hints and documentation."""
        self._initialize_attributes()
        self._sql_index = sql_index
        self._check = check

        self._validate_and_set_paths(fname)

        if force_rebuild:
            self._force_rebuild_indexes()
        else:
            self._load_or_create_indexes()

    def _initialize_attributes(self) -> None:
        """Initialize instance attributes."""
        self._mdx_file = ""
        self._mdd_file = ""
        self._encoding = ""
        self._stylesheet: dict[str, tuple[str, str]] = {}
        self._title = ""
        self._version = ""
        self._description = ""
        self._mdx_db = ""
        self._mdd_db = ""

    def _validate_and_set_paths(self, fname: str | Path) -> None:
        """Validate MDX file and set up paths."""
        fname_path = Path(fname)
        if fname_path.suffix != ".mdx":
            raise ValueError(f"Expected .mdx file, got: {fname_path.suffix}")
        if not fname_path.is_file():
            raise FileNotFoundError(f"MDX file not found: {fname}")

        self._mdx_file = str(fname_path)
        filename_base = str(fname_path.with_suffix(""))
        self._mdx_db = filename_base + ".mdx.db"

        # Set up MDD file paths if exists
        mdd_path = Path(filename_base + ".mdd")
        if mdd_path.is_file():
            self._mdd_file = str(mdd_path)
            self._mdd_db = filename_base + ".mdd.db"

    def _force_rebuild_indexes(self) -> None:
        """Force rebuild all indexes."""
        self._make_mdx_index(self._mdx_db)
        if self._mdd_file:
            self._make_mdd_index(self._mdd_db)

    def _load_or_create_indexes(self) -> None:
        """Load existing indexes or create new ones."""
        if os.path.isfile(self._mdx_db):
            if self._load_meta_from_db():
                # Successfully loaded metadata
                pass
            else:
                # Need to rebuild
                self._rebuild_mdx_index()
        else:
            self._make_mdx_index(self._mdx_db)

        # Handle MDD index
        if self._mdd_file and not os.path.isfile(self._mdd_db):
            self._make_mdd_index(self._mdd_db)

    def _load_meta_from_db(self) -> bool:
        """Load metadata from existing database.

        Returns:
            True if metadata loaded successfully, False if rebuild needed.
        """
        try:
            with sqlite3.connect(self._mdx_db) as conn:
                # Check version info
                cursor = conn.execute('SELECT value FROM META WHERE key = "version"')
                if row := cursor.fetchone():
                    self._version = row[0]
                else:
                    return False  # No version info, need rebuild

                # Get encoding
                cursor = conn.execute(
                    "SELECT value FROM META WHERE key = ?", ("encoding",)
                )
                if row := cursor.fetchone():
                    self._encoding = row[0]

                # Get stylesheet
                cursor = conn.execute(
                    "SELECT value FROM META WHERE key = ?", ("stylesheet",)
                )
                if row := cursor.fetchone():
                    self._stylesheet = json.loads(row[0])

                # Get title
                cursor = conn.execute(
                    "SELECT value FROM META WHERE key = ?", ("title",)
                )
                if row := cursor.fetchone():
                    self._title = row[0]

                # Get description
                cursor = conn.execute(
                    "SELECT value FROM META WHERE key = ?", ("description",)
                )
                if row := cursor.fetchone():
                    self._description = row[0]

                return True
        except sqlite3.Error as e:
            logging.error(f"Error loading metadata from database: {e}")
            return False

    def _rebuild_mdx_index(self) -> None:
        """Rebuild MDX index and MDD if exists."""
        logging.info("Version info not found, rebuilding index")
        self._make_mdx_index(self._mdx_db)
        logging.info("mdx.db rebuilt")

        if self._mdd_file:
            self._make_mdd_index(self._mdd_db)
            logging.info("mdd.db rebuilt")

    def _replace_stylesheet(self, txt):
        # substitute stylesheet definition
        txt_list = re.split(r"`\d+`", txt)
        txt_tag = re.findall(r"`\d+`", txt)
        txt_styled = txt_list[0]
        for j, p in enumerate(txt_list[1:]):
            style = self._stylesheet[txt_tag[j][1:-1]]
            if p and p[-1] == "\n":
                txt_styled = txt_styled + style[0] + p.rstrip() + style[1] + "\r\n"
            else:
                txt_styled = txt_styled + style[0] + p + style[1]
        return txt_styled

    def _make_mdx_index(self, db_name):
        if os.path.exists(db_name):
            os.remove(db_name)
        mdx = MDX(self._mdx_file)
        self._mdx_db = db_name
        returned_index = mdx.get_index(check_block=self._check)
        index_list = returned_index["index_dict_list"]
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute(
            """ CREATE TABLE MDX_INDEX
               (key_text text not null,
                file_pos integer,
                compressed_size integer,
                decompressed_size integer,
                record_block_type integer,
                record_start integer,
                record_end integer,
                offset integer
                )"""
        )

        tuple_list = [
            (
                item["key_text"],
                item["file_pos"],
                item["compressed_size"],
                item["decompressed_size"],
                item["record_block_type"],
                item["record_start"],
                item["record_end"],
                item["offset"],
            )
            for item in index_list
        ]
        c.executemany("INSERT INTO MDX_INDEX VALUES (?,?,?,?,?,?,?,?)", tuple_list)
        # build the metadata table
        meta = returned_index["meta"]
        c.execute(
            """CREATE TABLE META
               (key text,
                value text
                )"""
        )

        # for k,v in meta:
        #    c.execute(
        #    'INSERT INTO META VALUES (?,?)',
        #    (k, v)
        #    )

        c.executemany(
            "INSERT INTO META VALUES (?,?)",
            [
                ("encoding", meta["encoding"]),
                ("stylesheet", meta["stylesheet"]),
                ("title", meta["title"]),
                ("description", meta["description"]),
                ("version", version),
            ],
        )

        if self._sql_index:
            c.execute(
                """
                CREATE INDEX key_index ON MDX_INDEX (key_text)
                """
            )

        conn.commit()
        conn.close()
        # set class member
        self._encoding = meta["encoding"]
        self._stylesheet = json.loads(meta["stylesheet"])
        self._title = meta["title"]
        self._description = meta["description"]

    def _make_mdd_index(self, db_name):
        if os.path.exists(db_name):
            os.remove(db_name)
        mdd = MDD(self._mdd_file)
        self._mdd_db = db_name
        index_list = mdd.get_index(check_block=self._check)
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute(
            """ CREATE TABLE MDX_INDEX
               (key_text text not null unique,
                file_pos integer,
                compressed_size integer,
                decompressed_size integer,
                record_block_type integer,
                record_start integer,
                record_end integer,
                offset integer
                )"""
        )

        tuple_list = [
            (
                item["key_text"],
                item["file_pos"],
                item["compressed_size"],
                item["decompressed_size"],
                item["record_block_type"],
                item["record_start"],
                item["record_end"],
                item["offset"],
            )
            for item in index_list
        ]
        c.executemany("INSERT INTO MDX_INDEX VALUES (?,?,?,?,?,?,?,?)", tuple_list)
        if self._sql_index:
            c.execute(
                """
                CREATE UNIQUE INDEX key_index ON MDX_INDEX (key_text)
                """
            )

        conn.commit()
        conn.close()

    def _decompress_record_block(self, file_handle, index: dict) -> bytes:
        """Extract and decompress record block from file.

        Args:
            file_handle: Open file handle
            index: Index information dict

        Returns:
            Decompressed record block data

        Raises:
            RuntimeError: If LZO compression not supported
        """
        file_handle.seek(index["file_pos"])
        record_block_compressed = file_handle.read(index["compressed_size"])
        record_block_type = index["record_block_type"]
        # decompressed_size is not used but kept for clarity
        _ = index["decompressed_size"]

        if record_block_type == 0:
            # No compression
            record_block = record_block_compressed[8:]
        elif record_block_type == 1:
            # LZO compression is no longer supported
            raise RuntimeError(
                "LZO compressed record block detected. LZO support has been removed. "
                "Please use a more modern MDX file format with zlib compression."
            )
        elif record_block_type == 2:
            # zlib compression
            record_block = zlib.decompress(record_block_compressed[8:])
        else:
            raise ValueError(f"Unknown compression type: {record_block_type}")

        # Extract the specific record from the block
        return record_block[
            index["record_start"] - index["offset"] : index["record_end"]
            - index["offset"]
        ]

    def get_mdx_by_index(self, fmdx, index: dict) -> str:
        """Get MDX record by index with text processing.

        Args:
            fmdx: Open MDX file handle
            index: Index information dict

        Returns:
            Processed text record
        """
        record = self._decompress_record_block(fmdx, index)

        # Decode and process text
        record = (
            record.decode(self._encoding, errors="ignore").strip("\x00").encode("utf-8")
        )

        # Apply stylesheet if available
        if self._stylesheet:
            record = self._replace_stylesheet(record)

        return record.decode("utf-8")

    def get_mdd_by_index(self, fmdx, index: dict) -> bytes:
        """Get MDD resource by index (binary data).

        Args:
            fmdx: Open MDD file handle
            index: Index information dict

        Returns:
            Raw binary data
        """
        return self._decompress_record_block(fmdx, index)

    def mdx_lookup(self, keyword: str) -> list[str]:
        """Look up keyword in MDX index with proper resource management.

        Args:
            keyword: Word to look up in dictionary

        Returns:
            List of definitions found

        Raises:
            sqlite3.Error: If database operation fails
            FileNotFoundError: If MDX file not found
            OSError: If file I/O fails
        """
        if not keyword:
            return []

        lookup_result_list = []

        try:
            with sqlite3.connect(self._mdx_db) as conn:
                # Use parameterized query to prevent SQL injection
                cursor = conn.execute(
                    "SELECT * FROM MDX_INDEX WHERE key_text = ?", (keyword,)
                )

                with open(self._mdx_file, "rb") as mdx_file:
                    for result in cursor:
                        index = {
                            "file_pos": result[1],
                            "compressed_size": result[2],
                            "decompressed_size": result[3],
                            "record_block_type": result[4],
                            "record_start": result[5],
                            "record_end": result[6],
                            "offset": result[7],
                        }
                        lookup_result_list.append(
                            self.get_mdx_by_index(mdx_file, index)
                        )

        except sqlite3.Error as e:
            logging.error(f"Database error during MDX lookup for '{keyword}': {e}")
            raise
        except (FileNotFoundError, OSError) as e:
            logging.error(f"File error during MDX lookup for '{keyword}': {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during MDX lookup for '{keyword}': {e}")
            raise

        return lookup_result_list

    def mdd_lookup(self, keyword: str) -> list[bytes]:
        """Look up resource in MDD index with proper resource management.

        Args:
            keyword: Resource path to look up

        Returns:
            List of resource data found

        Raises:
            sqlite3.Error: If database operation fails
            FileNotFoundError: If MDD file not found
            OSError: If file I/O fails
        """
        if not keyword or not hasattr(self, "_mdd_db") or not self._mdd_db:
            return []

        lookup_result_list = []

        try:
            with sqlite3.connect(self._mdd_db) as conn:
                # Use parameterized query to prevent SQL injection
                cursor = conn.execute(
                    "SELECT * FROM MDX_INDEX WHERE key_text = ?", (keyword,)
                )

                with open(self._mdd_file, "rb") as mdd_file:
                    for result in cursor:
                        index = {
                            "file_pos": result[1],
                            "compressed_size": result[2],
                            "decompressed_size": result[3],
                            "record_block_type": result[4],
                            "record_start": result[5],
                            "record_end": result[6],
                            "offset": result[7],
                        }
                        lookup_result_list.append(
                            self.get_mdd_by_index(mdd_file, index)
                        )

        except sqlite3.Error as e:
            logging.error(f"Database error during MDD lookup for '{keyword}': {e}")
            raise
        except (FileNotFoundError, OSError) as e:
            logging.error(f"File error during MDD lookup for '{keyword}': {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during MDD lookup for '{keyword}': {e}")
            raise

        return lookup_result_list

    def get_mdd_keys(self, query=""):
        """Get MDD keys with optional query pattern.

        Args:
            query: Optional query pattern. Use * for wildcards.

        Returns:
            List of matching keys.
        """
        if not self._mdd_db:
            return []

        try:
            with sqlite3.connect(self._mdd_db) as conn:
                if query:
                    if "*" in query:
                        query = query.replace("*", "%")
                    else:
                        query = query + "%"
                    cursor = conn.execute(
                        "SELECT key_text FROM MDX_INDEX WHERE key_text LIKE ?", (query,)
                    )
                    keys = [item[0] for item in cursor]
                else:
                    cursor = conn.execute("SELECT key_text FROM MDX_INDEX")
                    keys = [item[0] for item in cursor]
                return keys
        except sqlite3.Error as e:
            logging.error(f"Database error during MDD keys query '{query}': {e}")
            return []

    def get_mdx_keys(self, query=""):
        """Get MDX keys with optional query pattern.

        Args:
            query: Optional query pattern. Use * for wildcards.

        Returns:
            List of matching keys.
        """
        try:
            with sqlite3.connect(self._mdx_db) as conn:
                if query:
                    if "*" in query:
                        query = query.replace("*", "%")
                    else:
                        query = query + "%"
                    cursor = conn.execute(
                        "SELECT key_text FROM MDX_INDEX WHERE key_text LIKE ?", (query,)
                    )
                    keys = [item[0] for item in cursor]
                else:
                    cursor = conn.execute("SELECT key_text FROM MDX_INDEX")
                    keys = [item[0] for item in cursor]
                return keys
        except sqlite3.Error as e:
            logging.error(f"Database error during MDX keys query '{query}': {e}")
            return []


# mdx_builder = IndexBuilder("oald.mdx")
# text = mdx_builder.mdx_lookup('dedication')
# keys = mdx_builder.get_mdx_keys()
# keys1 = mdx_builder.get_mdx_keys('abstrac')
# keys2 = mdx_builder.get_mdx_keys('*tion')
# for key in keys2:
# text = mdx_builder.mdx_lookup(key)[0]
# pass
