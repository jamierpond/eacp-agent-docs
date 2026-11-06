#!/usr/bin/env python3
"""Reads plain // comments directly above a declaration as its doc comment.

As a Doxygen INPUT_FILTER (`plain_doc_comments.py <file>`) it prints the file
with each such // block turned into ///, and a // after an enumerator into
///<, keeping every line where it was. generate.py also calls
find_plain_doc_comments() to warn about the blocks still written with //.

A block is left alone when it is inside a function body, when its first line
starts with TODO, FIXME, XXX, HACK, clang-format or NOLINT, when most of its
lines look like code, or
when a blank line, a preprocessor line or an access specifier sits between it
and the next code.
"""

import re
import sys
from dataclasses import dataclass, field

NOTE_PREFIXES = ("TODO", "FIXME", "XXX", "HACK", "clang-format", "NOLINT")
CODE_LOOKING_COMMENT = re.compile(
    r";\s*$|^\s*[{}]\s*$|\{\s*$|^#\s*\w+|^(return|if|for|while|switch|auto)\b.*[;({]")
DECLARATION_SCOPE_OPENER = re.compile(
    r"^(\[\[.*?\]\]\s*)?(inline\s+|typedef\s+|export\s+)?"
    r"(namespace|class|struct|union|enum)\b|^extern\s+\"C\"")
ACCESS_SPECIFIER = re.compile(r"^(public|protected|private)\s*:")
LEADING_TEMPLATE = re.compile(r"^template\s*<")
TRANSPARENT_PREPROCESSOR_LINE = re.compile(
    r"^#\s*(if|ifdef|ifndef|elif|else|endif|pragma\s+warning)\b")
INDENTED_EXAMPLE_LINE = re.compile(r"^\s*//\s{2,}\S")
RAW_STRING_START = re.compile(r'R"([^(\s]*)\(')


@dataclass
class PlainDocComments:
    block_line_ranges: list = field(default_factory=list)
    trailing_enumerator_columns: dict = field(default_factory=dict)

    def get_first_lines(self):
        return [first for first, _ in self.block_line_ranges]


@dataclass
class ScannedLine:
    code: str = ""
    comment_column: int = -1
    starts_inside_comment_or_string: bool = False


def remove_leading_template_header(statement):
    if not LEADING_TEMPLATE.match(statement):
        return statement
    depth = 0
    for index, character in enumerate(statement):
        if character == "<":
            depth += 1
        elif character == ">":
            depth -= 1
            if depth == 0:
                return statement[index + 1:].lstrip()
    return statement


def is_declaration_scope_opener(statement):
    statement = ACCESS_SPECIFIER.sub("", statement.strip()).strip()
    statement = remove_leading_template_header(statement)
    return bool(DECLARATION_SCOPE_OPENER.match(statement))


class SourceScanner:
    def __init__(self):
        self.inside_block_comment = False
        self.raw_string_terminator = None

    def scan(self, line):
        scanned = ScannedLine(starts_inside_comment_or_string=(
            self.inside_block_comment or self.raw_string_terminator is not None))
        code = []
        index = 0
        while index < len(line):
            if self.inside_block_comment:
                end = line.find("*/", index)
                if end < 0:
                    break
                self.inside_block_comment = False
                index = end + 2
                continue
            if self.raw_string_terminator is not None:
                end = line.find(self.raw_string_terminator, index)
                if end < 0:
                    break
                index = end + len(self.raw_string_terminator)
                self.raw_string_terminator = None
                code.append('""')
                continue
            if line.startswith("//", index):
                scanned.comment_column = index
                break
            if line.startswith("/*", index):
                self.inside_block_comment = True
                index += 2
                continue
            raw_string = RAW_STRING_START.match(line, index)
            if raw_string and (index == 0 or not (line[index - 1].isalnum()
                                                  or line[index - 1] == "_")):
                self.raw_string_terminator = ")" + raw_string.group(1) + '"'
                index = raw_string.end()
                continue
            character = line[index]
            if character in "\"'":
                end = index + 1
                while end < len(line) and line[end] != character:
                    end += 2 if line[end] == "\\" else 1
                code.append(character * 2)
                index = end + 1
                continue
            code.append(character)
            index += 1
        scanned.code = "".join(code)
        return scanned


def get_comment_text(line):
    return line.strip()[2:].strip()


def is_plain_comment_line(line, scanned):
    stripped = line.lstrip()
    return (not scanned.starts_inside_comment_or_string and scanned.code.strip() == ""
            and stripped.startswith("//") and not stripped.startswith(("///", "//!")))


def can_document_next_line(code_line):
    stripped = code_line.strip()
    if not stripped or stripped.startswith(("}", "{")) or ACCESS_SPECIFIER.match(stripped):
        return False
    if stripped.startswith("#"):
        return stripped.startswith("#define")
    return not stripped.startswith(("static_assert", "using namespace"))


def is_documenting_block(lines):
    texts = [get_comment_text(line) for line in lines]
    if not any(texts) or texts[0].startswith(NOTE_PREFIXES):
        return False
    if all(not re.search(r"\w", text) for text in texts):
        return False
    prose_texts = [get_comment_text(line) for line in lines
                   if not INDENTED_EXAMPLE_LINE.match(line)]
    texts = prose_texts or texts
    code_looking_count = sum(bool(CODE_LOOKING_COMMENT.search(text)) for text in texts)
    return code_looking_count * 2 <= len([text for text in texts if text])


def find_plain_doc_comments(text):
    lines = text.splitlines()
    found = PlainDocComments()
    scanner = SourceScanner()
    scope_kinds = []
    statement = ""
    comment_run_start = None
    comment_run_end = None

    def is_inside_declaration_scope():
        return all(kind != "body" for kind in scope_kinds)

    for line_index, line in enumerate(lines):
        scanned = scanner.scan(line)
        if is_plain_comment_line(line, scanned):
            if comment_run_start is None:
                comment_run_start = line_index
            comment_run_end = line_index + 1
            continue
        if (comment_run_start is not None
                and TRANSPARENT_PREPROCESSOR_LINE.match(scanned.code.strip())):
            continue
        if comment_run_start is not None:
            run = lines[comment_run_start:comment_run_end]
            if (is_inside_declaration_scope() and can_document_next_line(scanned.code)
                    and not scanned.starts_inside_comment_or_string
                    and is_documenting_block(run)):
                found.block_line_ranges.append((comment_run_start, comment_run_end))
            comment_run_start = None
        if scanned.code.lstrip().startswith("#"):
            continue
        if (scope_kinds and scope_kinds[-1] == "enum" and scanned.comment_column > 0
                and scanned.code.strip() and not line[scanned.comment_column:].startswith(
                    ("///", "//!"))):
            found.trailing_enumerator_columns[line_index] = scanned.comment_column
        for character in scanned.code:
            if character == "{":
                if not is_inside_declaration_scope():
                    scope_kinds.append("body")
                elif re.match(r"^\s*(enum)\b", ACCESS_SPECIFIER.sub("", statement.strip())):
                    scope_kinds.append("enum")
                elif is_declaration_scope_opener(statement):
                    scope_kinds.append("declarations")
                else:
                    scope_kinds.append("body")
                statement = ""
            elif character == "}":
                if scope_kinds:
                    scope_kinds.pop()
                statement = ""
            elif character == ";":
                statement = ""
            else:
                statement += character
        statement += " "
    return found


def convert_plain_doc_comments(text):
    found = find_plain_doc_comments(text)
    lines = text.split("\n")
    for first, end in found.block_line_ranges:
        for line_index in range(first, end):
            lines[line_index] = lines[line_index].replace("//", "///", 1)
    for line_index, column in found.trailing_enumerator_columns.items():
        line = lines[line_index]
        lines[line_index] = line[:column] + "///<" + line[column + 2:]
    return "\n".join(lines)


def main():
    with open(sys.argv[1], encoding="utf-8", errors="surrogateescape") as source:
        text = source.read()
    sys.stdout.buffer.write(convert_plain_doc_comments(text).encode(
        "utf-8", errors="surrogateescape"))


if __name__ == "__main__":
    main()
