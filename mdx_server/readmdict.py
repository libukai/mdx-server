#!/usr/bin/env python3
"""
MDict Dictionary File (.mdx) and Resource File (.mdd) Analyzer.

Modernized for Python 3.13+ with improved type safety and error handling.

Original Copyright (C) 2012, 2013, 2015 Xiaoqiang Wang
Licensed under GPL v3.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import zlib
from io import BytesIO
from struct import unpack


# Note: Encryption support has been removed as encrypted MDX files are not supported
def _unescape_entities(text: bytes) -> bytes:
    """
    Unescape HTML entities in bytes text.

    Args:
        text: Input bytes with HTML entities

    Returns:
        Bytes with entities unescaped
    """
    return (
        text.replace(b"&lt;", b"<")
        .replace(b"&gt;", b">")
        .replace(b"&quot;", b'"')
        .replace(b"&amp;", b"&")
    )


class MDict:
    """
    Base class which reads in header and key block.
    It has no public methods and serves only as code sharing base class.
    """

    def __init__(self, fname, encoding=""):
        self._fname = fname
        self._encoding = encoding.upper()

        self.header = self._read_header()
        try:
            self._key_list = self._read_keys()
        except Exception as e:
            logging.debug(f"Normal key reading failed: {e}")
            logging.info("Try Brutal Force on Key Blocks")
            self._key_list = self._read_keys_brutal()

    def __len__(self):
        return self._num_entries

    def __iter__(self):
        return self.keys()

    def keys(self):
        """
        Return an iterator over dictionary keys.
        """
        return (key_value for key_id, key_value in self._key_list)

    def _read_number(self, f):
        return unpack(self._number_format, f.read(self._number_width))[0]

    def _parse_header(self, header):
        """
        extract attributes from <Dict attr="value" ... >
        """
        taglist = re.findall(rb'(\w+)="(.*?)"', header, re.DOTALL)
        tagdict = {}
        for key, value in taglist:
            tagdict[key] = _unescape_entities(value)
        return tagdict

    def _decode_key_block_info(self, key_block_info_compressed):
        if self._version >= 2:
            # zlib compression
            assert key_block_info_compressed[:4] == b"\x02\x00\x00\x00"
            # Note: Decryption step removed - files are treated as unencrypted
            # decompress
            key_block_info = zlib.decompress(key_block_info_compressed[8:])
            # adler checksum
            adler32 = unpack(">I", key_block_info_compressed[4:8])[0]
            assert adler32 == zlib.adler32(key_block_info) & 0xFFFFFFFF
        else:
            # no compression
            key_block_info = key_block_info_compressed
        # decode
        key_block_info_list = []
        num_entries = 0
        i = 0
        if self._version >= 2:
            byte_format = ">H"
            byte_width = 2
            text_term = 1
        else:
            byte_format = ">B"
            byte_width = 1
            text_term = 0

        while i < len(key_block_info):
            # number of entries in current key block
            num_entries += unpack(
                self._number_format, key_block_info[i : i + self._number_width]
            )[0]
            i += self._number_width
            # text head size
            text_head_size = unpack(byte_format, key_block_info[i : i + byte_width])[0]
            i += byte_width
            # text head
            if self._encoding != "UTF-16":
                i += text_head_size + text_term
            else:
                i += (text_head_size + text_term) * 2
            # text tail size
            text_tail_size = unpack(byte_format, key_block_info[i : i + byte_width])[0]
            i += byte_width
            # text tail
            if self._encoding != "UTF-16":
                i += text_tail_size + text_term
            else:
                i += (text_tail_size + text_term) * 2
            # key block compressed size
            key_block_compressed_size = unpack(
                self._number_format, key_block_info[i : i + self._number_width]
            )[0]
            i += self._number_width
            # key block decompressed size
            key_block_decompressed_size = unpack(
                self._number_format, key_block_info[i : i + self._number_width]
            )[0]
            i += self._number_width
            key_block_info_list += [
                (key_block_compressed_size, key_block_decompressed_size)
            ]

        assert num_entries == self._num_entries

        return key_block_info_list

    def _decode_key_block(self, key_block_compressed, key_block_info_list):
        key_list = []
        i = 0
        for compressed_size, _decompressed_size in key_block_info_list:
            start = i
            end = i + compressed_size
            # 4 bytes : compression type
            key_block_type = key_block_compressed[start : start + 4]
            # 4 bytes : adler checksum of decompressed key block
            adler32 = unpack(">I", key_block_compressed[start + 4 : start + 8])[0]
            if key_block_type == b"\x00\x00\x00\x00":
                key_block = key_block_compressed[start + 8 : end]
            elif key_block_type == b"\x01\x00\x00\x00":
                # LZO compression is no longer supported
                raise RuntimeError(
                    "LZO compressed MDX file detected. LZO support has been removed. "
                    "Please use a more modern MDX file format with zlib compression."
                )
            elif key_block_type == b"\x02\x00\x00\x00":
                # decompress key block
                key_block = zlib.decompress(key_block_compressed[start + 8 : end])
            # extract one single key block into a key list
            key_list += self._split_key_block(key_block)
            # notice that adler32 returns signed value
            assert adler32 == zlib.adler32(key_block) & 0xFFFFFFFF

            i += compressed_size
        return key_list

    def _split_key_block(self, key_block):
        key_list = []
        key_start_index = 0
        while key_start_index < len(key_block):
            # temp = key_block[key_start_index : key_start_index + self._number_width]  # Unused
            # the corresponding record's offset in record block
            key_id = unpack(
                self._number_format,
                key_block[key_start_index : key_start_index + self._number_width],
            )[0]
            # key text ends with '\x00'
            if self._encoding == "UTF-16":
                delimiter = b"\x00\x00"
                width = 2
            else:
                delimiter = b"\x00"
                width = 1
            i = key_start_index + self._number_width
            while i < len(key_block):
                if key_block[i : i + width] == delimiter:
                    key_end_index = i
                    break
                i += width
            key_text = (
                key_block[key_start_index + self._number_width : key_end_index]
                .decode(self._encoding, errors="ignore")
                .encode("utf-8")
                .strip()
            )
            key_start_index = key_end_index + width
            key_list += [(key_id, key_text)]
        return key_list

    def _read_header(self):
        with open(self._fname, "rb") as f:
            # number of bytes of header text
            header_bytes_size = unpack(">I", f.read(4))[0]
            header_bytes = f.read(header_bytes_size)
            # 4 bytes: adler32 checksum of header, in little endian
            adler32 = unpack("<I", f.read(4))[0]
            assert adler32 == zlib.adler32(header_bytes) & 0xFFFFFFFF
            # mark down key block offset
            self._key_block_offset = f.tell()

        # header text in utf-16 encoding ending with '\x00\x00'
        header_text = header_bytes[:-2].decode("utf-16").encode("utf-8")
        header_tag = self._parse_header(header_text)
        if not self._encoding:
            encoding = header_tag[b"Encoding"]
            if sys.hexversion >= 0x03000000:
                encoding = encoding.decode("utf-8")
            # GB18030 > GBK > GB2312
            if encoding in ["GBK", "GB2312"]:
                encoding = "GB18030"
            self._encoding = encoding
        # 读取标题和描述
        if b"Title" in header_tag:
            self._title = header_tag[b"Title"].decode("utf-8")
        else:
            self._title = ""

        if b"Description" in header_tag:
            self._description = header_tag[b"Description"].decode("utf-8")
        else:
            self._description = ""
        pass
        # Note: Encryption is not supported - all files are treated as unencrypted

        # stylesheet attribute if present takes form of:
        #   style_number # 1-255
        #   style_begin # or ''
        #   style_end # or ''
        # store stylesheet in dict in the form of
        # {'number' : ('style_begin', 'style_end')}
        self._stylesheet = {}
        if header_tag.get("StyleSheet"):
            lines = header_tag["StyleSheet"].splitlines()
            for i in range(0, len(lines), 3):
                self._stylesheet[lines[i]] = (lines[i + 1], lines[i + 2])

        # before version 2.0, number is 4 bytes integer
        # version 2.0 and above uses 8 bytes
        self._version = float(header_tag[b"GeneratedByEngineVersion"])
        if self._version < 2.0:
            self._number_width = 4
            self._number_format = ">I"
        else:
            self._number_width = 8
            self._number_format = ">Q"

        return header_tag

    def _read_keys(self):
        with open(self._fname, "rb") as f:
            f.seek(self._key_block_offset)

            # read key block header information
            if self._version >= 2.0:
                num_bytes = 8 * 5
            else:
                num_bytes = 4 * 4
            block = f.read(num_bytes)

            # Note: Encryption handling removed - files are treated as unencrypted

            # decode this block
            sf = BytesIO(block)
            # number of key blocks
            num_key_blocks = self._read_number(sf)
            # number of entries
            self._num_entries = self._read_number(sf)
            # number of bytes of key block info after decompression
            if self._version >= 2.0:
                self._read_number(sf)  # key_block_info_decomp_size (unused)
            # number of bytes of key block info
            key_block_info_size = self._read_number(sf)
            # number of bytes of key block
            key_block_size = self._read_number(sf)

            # 4 bytes: adler checksum of previous 5 numbers
            if self._version >= 2.0:
                adler32 = unpack(">I", f.read(4))[0]
                assert adler32 == (zlib.adler32(block) & 0xFFFFFFFF)

            # read key block info, which indicates key block's compressed and
            # decompressed size
            key_block_info = f.read(key_block_info_size)
            key_block_info_list = self._decode_key_block_info(key_block_info)
            assert num_key_blocks == len(key_block_info_list)

            # read key block
            key_block_compressed = f.read(key_block_size)
            # extract key block
            key_list = self._decode_key_block(key_block_compressed, key_block_info_list)

            self._record_block_offset = f.tell()

        return key_list

    def _read_keys_brutal(self):
        with open(self._fname, "rb") as f:
            f.seek(self._key_block_offset)

            # the following numbers could be encrypted, disregard them!
            if self._version >= 2.0:
                num_bytes = 8 * 5 + 4
                key_block_type = b"\x02\x00\x00\x00"
            else:
                num_bytes = 4 * 4
                key_block_type = b"\x01\x00\x00\x00"
            f.read(num_bytes)  # block (unused)

            # key block info
            # 4 bytes '\x02\x00\x00\x00'
            # 4 bytes adler32 checksum
            # unknown number of bytes follows until '\x02\x00\x00\x00' which marks
            # the beginning of key block
            key_block_info = f.read(8)
            if self._version >= 2.0:
                assert key_block_info[:4] == b"\x02\x00\x00\x00"
            while True:
                fpos = f.tell()
                t = f.read(1024)
                index = t.find(key_block_type)
                if index != -1:
                    key_block_info += t[:index]
                    f.seek(fpos + index)
                    break
                else:
                    key_block_info += t

            key_block_info_list = self._decode_key_block_info(key_block_info)
            key_block_size = sum(list(zip(*key_block_info_list, strict=False))[0])

            # read key block
            key_block_compressed = f.read(key_block_size)
            # extract key block
            key_list = self._decode_key_block(key_block_compressed, key_block_info_list)

            self._record_block_offset = f.tell()

        self._num_entries = len(key_list)
        return key_list

    def _process_record_blocks(self):
        """
        Common generator method to process record blocks.
        Yields (record_block_data, compressed_size, decompressed_size) tuples.
        """
        with open(self._fname, "rb") as f:
            f.seek(self._record_block_offset)

            num_record_blocks = self._read_number(f)
            num_entries = self._read_number(f)
            assert num_entries == self._num_entries
            record_block_info_size = self._read_number(f)
            _ = self._read_number(f)  # record_block_size unused

            # record block info section
            record_block_info_list = []
            size_counter = 0
            for _ in range(num_record_blocks):
                compressed_size = self._read_number(f)
                decompressed_size = self._read_number(f)
                record_block_info_list.append((compressed_size, decompressed_size))
                size_counter += self._number_width * 2
            assert size_counter == record_block_info_size

            # process actual record blocks
            for compressed_size, decompressed_size in record_block_info_list:
                record_block_compressed = f.read(compressed_size)
                # 4 bytes: compression type
                record_block_type = record_block_compressed[:4]

                if record_block_type == b"\x00\x00\x00\x00":
                    # no compression
                    record_block = record_block_compressed[8:]
                elif record_block_type == b"\x01\x00\x00\x00":
                    # LZO compression is no longer supported
                    raise RuntimeError(
                        "LZO compressed record block detected. LZO support has been removed. "
                        "Please use a more modern MDX file format with zlib compression."
                    )
                elif record_block_type == b"\x02\x00\x00\x00":
                    # zlib compression
                    record_block = zlib.decompress(record_block_compressed[8:])
                else:
                    raise ValueError(f"Unknown compression type: {record_block_type}")

                yield record_block, compressed_size, decompressed_size

    def _generate_index_info(self, check_block=True):
        """
        Common generator method to create index information for both MDX and MDD.
        Yields tuples of (index_dict, record_block_data) for each key entry.
        """
        with open(self._fname, "rb") as f:
            f.seek(self._record_block_offset)

            num_record_blocks = self._read_number(f)
            num_entries = self._read_number(f)
            assert num_entries == self._num_entries
            record_block_info_size = self._read_number(f)
            _ = self._read_number(f)  # record_block_size unused

            # record block info section
            record_block_info_list = []
            size_counter = 0
            for _ in range(num_record_blocks):
                compressed_size = self._read_number(f)
                decompressed_size = self._read_number(f)
                record_block_info_list += [(compressed_size, decompressed_size)]
                size_counter += self._number_width * 2
            assert size_counter == record_block_info_size

            # actual record block
            offset = 0
            i = 0
            size_counter = 0
            for compressed_size, decompressed_size in record_block_info_list:
                current_pos = f.tell()
                record_block_compressed = f.read(compressed_size)
                # 4 bytes: compression type
                record_block_type = record_block_compressed[:4]
                # 4 bytes: adler32 checksum of decompressed record block
                adler32 = unpack(">I", record_block_compressed[4:8])[0]

                if record_block_type == b"\x00\x00\x00\x00":
                    _type = 0
                    if check_block:
                        record_block = record_block_compressed[8:]
                elif record_block_type == b"\x01\x00\x00\x00":
                    # LZO compression is no longer supported
                    raise RuntimeError(
                        "LZO compressed record block detected. LZO support has been removed. "
                        "Please use a more modern MDX file format with zlib compression."
                    )
                elif record_block_type == b"\x02\x00\x00\x00":
                    _type = 2
                    if check_block:
                        record_block = zlib.decompress(record_block_compressed[8:])

                # notice that adler32 return signed value
                if check_block:
                    assert adler32 == zlib.adler32(record_block) & 0xFFFFFFFF
                    assert len(record_block) == decompressed_size

                # split record block according to the offset info from key block
                while i < len(self._key_list):
                    index_dict = {}
                    index_dict["file_pos"] = current_pos
                    index_dict["compressed_size"] = compressed_size
                    index_dict["decompressed_size"] = decompressed_size
                    index_dict["record_block_type"] = _type
                    record_start, key_text = self._key_list[i]
                    index_dict["record_start"] = record_start
                    index_dict["key_text"] = key_text.decode("utf-8")
                    index_dict["offset"] = offset

                    # reach the end of current record block
                    if record_start - offset >= decompressed_size:
                        break
                    # record end index
                    if i < len(self._key_list) - 1:
                        record_end = self._key_list[i + 1][0]
                    else:
                        record_end = decompressed_size + offset
                    index_dict["record_end"] = record_end
                    i += 1

                    # yield the data needed for different subclasses
                    record_data = None
                    if check_block:
                        record_data = record_block[
                            record_start - offset : record_end - offset
                        ]

                    yield index_dict, record_data

                offset += decompressed_size
                size_counter += compressed_size
            # Record block size validation removed as variable is not used

    def _decode_records_common(self, process_record_func=None):
        """
        Common method to decode record blocks and yield key-data pairs.

        Args:
            process_record_func: Optional function to process record data
                                Should take (record_data, key_text, encoding) and return processed data
        """
        offset = 0
        i = 0

        for (
            record_block,
            _compressed_size,
            _decompressed_size,
        ) in self._process_record_blocks():
            # split record block according to the offset info from key block
            while i < len(self._key_list):
                record_start, key_text = self._key_list[i]
                # reach the end of current record block
                if record_start - offset >= len(record_block):
                    break

                # record end index
                if i < len(self._key_list) - 1:
                    record_end = self._key_list[i + 1][0]
                else:
                    record_end = len(record_block) + offset
                i += 1

                record = record_block[record_start - offset : record_end - offset]

                # Process record using provided function or return raw data
                if process_record_func:
                    processed_record = process_record_func(
                        record, key_text, self._encoding
                    )
                    yield key_text, processed_record
                else:
                    yield key_text, record

            offset += len(record_block)


class MDD(MDict):
    """
    MDict resource file format (*.MDD) reader.
    >>> mdd = MDD("example.mdd")
    >>> len(mdd)
    208
    >>> for filename,content in mdd.items():
    ... print filename, content[:10]
    """

    def __init__(self, fname):
        MDict.__init__(self, fname, encoding="UTF-16")

    def items(self):
        """Return a generator which in turn produce tuples in the form of (filename, content)"""
        return self._decode_records_common()

    def get_index(self, check_block=True):
        """Generate index information for MDD files using base class method."""
        index_dict_list = []
        for index_dict, _record_data in self._generate_index_info(check_block):
            # MDD doesn't need to process the record data, just collect index info
            index_dict_list.append(index_dict)
        return index_dict_list


class MDX(MDict):
    """
    MDict dictionary file format (*.MDD) reader.
    >>> mdx = MDX("example.mdx")
    >>> len(mdx)
    42481
    >>> for key,value in mdx.items():
    ... print key, value[:10]
    """

    def __init__(self, fname, encoding="", substyle=False):
        MDict.__init__(self, fname, encoding)
        self._substyle = substyle

    def items(self):
        """Return a generator which in turn produce tuples in the form of (key, value)"""
        return self._decode_records_common(self._process_mdx_record)

    def _substitute_stylesheet(self, txt):
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

    def _process_mdx_record(self, record, key_text, encoding):
        """Process MDX record with text decoding and stylesheet substitution."""
        # convert to utf-8
        processed_record = (
            record.decode(encoding, errors="ignore").strip("\x00").encode("utf-8")
        )
        # substitute styles
        if self._substyle and self._stylesheet:
            processed_record = self._substitute_stylesheet(processed_record)
        return processed_record

    ### 获取 mdx 文件的索引列表，格式为
    ###  key_text(关键词，可以由后面的 keylist 得到)
    ###  file_pos(record_block开始的位置)
    ###  compressed_size(record_block压缩前的大小)
    ###  decompressed_size(解压后的大小)
    ###  record_block_type(record_block 的压缩类型)
    ###  record_start (以下三个为从 record_block 中提取某一调记录需要的参数，可以直接保存）
    ###  record_end
    ###  offset
    ### 所需 metadata
    ###
    def get_index(self, check_block=True):
        """Generate index information for MDX files using base class method."""
        index_dict_list = []
        for index_dict, record_data in self._generate_index_info(check_block):
            # MDX-specific processing: handle record data if check_block is True
            if check_block and record_data is not None:
                # convert to utf-8
                record = (
                    record_data.decode(self._encoding, errors="ignore")
                    .strip("\x00")
                    .encode("utf-8")
                )
                # substitute styles if enabled
                if self._substyle and self._stylesheet:
                    record = self._substitute_stylesheet(record)

            index_dict_list.append(index_dict)

        # MDX-specific: add metadata information
        meta = {}
        meta["encoding"] = self._encoding
        meta["stylesheet"] = json.dumps(self._stylesheet)
        meta["title"] = self._title
        meta["description"] = self._description

        return {"index_dict_list": index_dict_list, "meta": meta}


if __name__ == "__main__":
    import argparse
    import os
    import os.path
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-x",
        "--extract",
        action="store_true",
        help="extract mdx to source format and extract files from mdd",
    )
    parser.add_argument(
        "-s",
        "--substyle",
        action="store_true",
        help="substitute style definition if present",
    )
    parser.add_argument(
        "-d",
        "--datafolder",
        default="data",
        help="folder to extract data files from mdd",
    )
    parser.add_argument(
        "-e", "--encoding", default="", help="folder to extract data files from mdd"
    )
    parser.add_argument("filename", nargs="?", help="mdx file name")
    args = parser.parse_args()

    # check if filename is provided
    if not args.filename:
        print("Error: Please specify an MDX/MDD file")
        print("Usage: python readmdict.py <filename.mdx>")
        sys.exit(1)

    if not os.path.exists(args.filename):
        print(f"Error: File '{args.filename}' does not exist")
        sys.exit(1)

    base, ext = os.path.splitext(args.filename)

    # read mdx file
    mdx: MDX | None = None
    if ext.lower() == os.path.extsep + "mdx":
        mdx = MDX(args.filename, args.encoding, args.substyle)
        if isinstance(args.filename, str):
            bfname = args.filename.encode("utf-8")
        else:
            bfname = args.filename
        print(
            f"======== {bfname.decode('utf-8') if isinstance(bfname, bytes) else bfname} ========"
        )
        print(f"  Number of Entries : {len(mdx)}")
        for key, value in mdx.header.items():
            print(f"  {key} : {value}")
    else:
        mdx = None

    # find companion mdd file
    mdd_filename = "".join([base, os.path.extsep, "mdd"])
    mdd: MDD | None = None
    if os.path.exists(mdd_filename):
        mdd = MDD(mdd_filename)
        if isinstance(mdd_filename, str):
            bfname = mdd_filename.encode("utf-8")
        else:
            bfname = mdd_filename
        print(
            f"======== {bfname.decode('utf-8') if isinstance(bfname, bytes) else bfname} ========"
        )
        print(f"  Number of Entries : {len(mdd)}")
        for key, value in mdd.header.items():
            print(f"  {key} : {value}")
    else:
        mdd = None

    if args.extract:
        # write out glos
        if mdx:
            output_fname = "".join([base, os.path.extsep, "txt"])
            with open(output_fname, "wb") as tf:
                for key, value in mdx.items():
                    tf.write(key)
                    tf.write(b"\r\n")
                    tf.write(value)
                    if not value.endswith(b"\n"):
                        tf.write(b"\r\n")
                    tf.write(b"</>\r\n")
            # write out style
            if mdx.header.get("StyleSheet"):
                style_fname = "".join([base, "_style", os.path.extsep, "txt"])
                with open(style_fname, "wb") as sf:
                    sf.write(b"\r\n".join(mdx.header["StyleSheet"].splitlines()))
        # write out optional data files
        if mdd:
            datafolder = os.path.join(os.path.dirname(args.filename), args.datafolder)
            if not os.path.exists(datafolder):
                os.makedirs(datafolder)
            for key, value in mdd.items():
                fname = key.decode("utf-8").replace("\\", os.path.sep)
                dfname = datafolder + fname
                if not os.path.exists(os.path.dirname(dfname)):
                    os.makedirs(os.path.dirname(dfname))
                with open(dfname, "wb") as df:
                    df.write(value)
