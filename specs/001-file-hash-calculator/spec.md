# Feature Specification: File & Directory Hash Calculator

**Feature Branch**: `001-file-hash-calculator`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "新增一个用于计算文件、目录的哈希值的命令，支持 BLAKE3 哈希算法、多输出格式、排除表达式、进度条、并发计算和断点续算"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic File and Directory Hash Calculation (Priority: P1)

A user wants to compute the BLAKE3 hash of one or more files and directories. They provide a list of paths on the command line, and the tool calculates the hash for each file (by hashing its content) and each directory (by hashing the sorted, `#`-joined hashes of all its children). Results are displayed in a Markdown table on the terminal by default.

**Why this priority**: This is the core functionality — without it, the tool provides no value. All other features (output formats, file output, exclusions, concurrency, progress) build on top of basic hash computation.

**Independent Test**: Run the command with a single file path, verify the correct BLAKE3 hash is output in Markdown format. Run with a directory path, verify all descendant files and subdirectories appear in the output with correct hashes.

**Acceptance Scenarios**:

1. **Given** a single file `image.png` exists on disk, **When** the user runs the command with the file path, **Then** the output contains the file's absolute path, name (`image.png`), and its BLAKE3 hash (256-bit hex by default).
2. **Given** a directory `mydir/` with structure `file1.txt`, `file2.txt`, `subdir/file3.txt`, **When** the user runs the command with `mydir/`, **Then** the output contains entries for `mydir/`, `mydir/file1.txt`, `mydir/file2.txt`, `mydir/subdir/`, and `mydir/subdir/file3.txt`, each with correct absolute path, name, and hash.
3. **Given** a directory hash is computed as `BLAKE3("aaa#bbb#ccc")` where `aaa`, `bbb`, `ccc` are sorted child hashes, **When** the user recomputes the hash for the same directory without any file changes, **Then** the hash is identical to the previous computation.
4. **Given** a file in a directory has been modified, **When** the user recomputes the directory hash, **Then** both the modified file's hash and the directory's hash change accordingly.

---

### User Story 2 - Multiple Output Formats (Priority: P1)

The user can choose to output results in Markdown (default), JSON, CSV, or YAML format, making the results suitable for further automated processing.

**Why this priority**: Output flexibility is a core requirement — without it, users cannot pipe results into other tools or scripts for downstream processing (e.g., the duplicate image detection use case).

**Independent Test**: Run the command on the same input with each of the four format flags, verify each output is valid Markdown/JSON/CSV/YAML respectively and contains the same hash values.

**Acceptance Scenarios**:

1. **Given** the user does not specify an output format, **When** the command runs, **Then** results are displayed as a Markdown table.
2. **Given** the user specifies `--format json`, **When** the command runs, **Then** results are output as a valid JSON array of objects, each containing `path`, `name`, and `hash` fields.
3. **Given** the user specifies `--format csv`, **When** the command runs, **Then** results are output as CSV with columns for absolute path, name, and hash.
4. **Given** the user specifies `--format yaml`, **When** the command runs, **Then** results are output as valid YAML with each entry containing path, name, and hash.

---

### User Story 3 - Output to File with Safety Check (Priority: P2)

The user can direct output to a file instead of the terminal. If the target file already exists and is non-empty, the tool warns the user and asks for confirmation before overwriting. During long computations, results are periodically flushed to the file so partial results are not lost.

**Why this priority**: Essential for long-running computations where terminal output is impractical, but a quality-of-life enhancement over the core compute-and-display flow.

**Independent Test**: Run the command with `--output results.md`, verify the file is created with results. Run again with the same `--output`, verify the tool warns and asks for confirmation. Kill the command mid-computation, verify partial results are already written to the file.

**Acceptance Scenarios**:

1. **Given** the user specifies `--output results.json` and `results.json` does not exist, **When** the command runs, **Then** a new file `results.json` is created with the computed results.
2. **Given** the user specifies `--output results.json` and `results.json` already exists with content, **When** the command runs, **Then** the tool prompts the user to confirm overwrite, explaining the file is non-empty and will be replaced.
3. **Given** the user is computing hashes for a large directory tree and output is directed to a file, **When** the computation is in progress, **Then** results are periodically written to the output file so that interrupting the process does not lose all progress.
4. **Given** the user specifies `--output` without a format flag, **When** the command runs, **Then** the output format is inferred from the file extension (e.g., `.json` → JSON, `.csv` → CSV, `.yaml`/`.yml` → YAML, otherwise Markdown).

---

### User Story 4 - Excluding Files and Directories (Priority: P2)

The user can specify exclusion patterns to skip certain files or directories during hash computation, using common glob-style patterns.

**Why this priority**: Real-world directories often contain files that should not be hashed (build artifacts, caches, `.git` directories, node_modules). Without exclusion, the tool would waste time on irrelevant files.

**Independent Test**: Run the command on a directory containing `.git/`, `node_modules/`, and `*.log` files with exclusion patterns for each, verify excluded items do not appear in the output.

**Acceptance Scenarios**:

1. **Given** a directory contains a `.git/` subdirectory, **When** the user specifies an exclusion pattern for `.git`, **Then** no files or directories under `.git/` appear in the output.
2. **Given** a directory contains `*.log` files, **When** the user specifies an exclusion pattern `*.log`, **Then** no `.log` files appear in the output.
3. **Given** multiple exclusion patterns are provided, **When** the command runs, **Then** all paths matching any pattern are excluded.
4. **Given** a directory is excluded, **When** the command runs, **Then** its parent directory's hash does not include the excluded directory's hash in the computation.

---

### User Story 5 - Progress Indication (Priority: P3)

During long-running hash computations, the user sees a progress bar showing how many files/directories have been processed out of the total, along with an estimated time remaining.

**Why this priority**: Important for user experience during large operations, but the tool is functional without it. Users can wait without a progress bar; they just won't know how long.

**Independent Test**: Run the command on a directory with 1000+ files, verify a progress bar appears and updates as files are processed.

**Acceptance Scenarios**:

1. **Given** the user runs the command on a directory with many files, **When** computation begins, **Then** a progress bar is displayed showing the current file being processed and overall completion percentage.
2. **Given** output is directed to a file, **When** the command runs, **Then** the progress bar is still displayed on stderr (terminal) while results go to the file.

---

### User Story 6 - Concurrent Computation (Priority: P3)

The user can specify a concurrency level to speed up hash computation by processing multiple files in parallel.

**Why this priority**: Performance optimization. The tool works correctly without parallelism; concurrency reduces wait time for large datasets.

**Independent Test**: Run the command on a directory with 100+ files, once with `--workers 1` and once with `--workers 4`, verify the parallel run completes faster and produces identical results.

**Acceptance Scenarios**:

1. **Given** the user specifies `--workers 4`, **When** the command runs, **Then** up to 4 files are hashed concurrently, and the total wall-clock time is reduced compared to sequential execution.
2. **Given** the user does not specify `--workers`, **When** the command runs, **Then** a reasonable default (e.g., number of CPU cores) is used.
3. **Given** concurrent computation is enabled, **When** the command completes, **Then** all results are identical to a sequential run (deterministic output).

---

### User Story 7 - Resume Interrupted Computation (Priority: P3)

If a hash computation is interrupted (e.g., Ctrl+C, system crash), the user can resume from where it left off by re-running the same command with the same output file. Already-computed hashes are read from the existing output, and only unprocessed files are hashed.

**Why this priority**: Resilience feature for very large datasets. Adds significant value for power users but is not needed for basic operation.

**Independent Test**: Start a computation with `--output results.json`, interrupt it mid-way, re-run the same command, verify only unprocessed files are computed and the final output is complete and correct.

**Acceptance Scenarios**:

1. **Given** a previous run with `--output results.json` was interrupted after processing 50% of files, **When** the user re-runs the same command with the same output file, **Then** the tool detects existing results, skips already-computed files, and only computes hashes for the remaining files.
2. **Given** a resumed computation completes, **When** the user inspects the output file, **Then** it contains all results (both resumed and newly computed) and is indistinguishable from a single uninterrupted run.
3. **Given** the underlying files have changed since the interrupted run, **When** the user resumes, **Then** the tool detects the mismatch (e.g., via file modification time or size) and recomputes the affected files.

---

### User Story 8 - Configurable Hash Output Length (Priority: P3)

The user can specify the desired output length (in bits) for the BLAKE3 hash, with a default of 256 bits.

**Why this priority**: Provides flexibility for users who need shorter or longer hash outputs, but the default covers the vast majority of use cases.

**Independent Test**: Run the command with `--hash-length 128` and `--hash-length 256`, verify the output hash strings have the correct hex character lengths (32 and 64 characters respectively).

**Acceptance Scenarios**:

1. **Given** the user does not specify a hash length, **When** the command runs, **Then** hashes are output as 64-character hex strings (256-bit).
2. **Given** the user specifies `--hash-length 128`, **When** the command runs, **Then** hashes are output as 32-character hex strings (128-bit).

---

### Edge Cases

- **Empty directory**: What hash does an empty directory produce? (Should be a well-defined constant or the BLAKE3 of an empty string.)
- **Symlinks**: How are symbolic links handled? (Should be skipped or reported with a warning to avoid infinite loops and inconsistencies.)
- **Unreadable files**: What happens when a file exists but cannot be read due to permissions? (Should be reported as an error for that specific file, but computation continues for other files.)
- **Very large files**: How does the tool handle files that are gigabytes in size? (Should stream content in chunks rather than loading the entire file into memory.)
- **Path with special characters**: Files or directories with spaces, Unicode characters, or shell-special characters in their names should be handled correctly.
- **Duplicate input paths**: If the user provides the same path multiple times or overlapping paths (e.g., both `mydir/` and `mydir/file1.txt`), duplicates should be deduplicated.
- **Stdin/pipe input**: The tool may receive paths via stdin piping in addition to command-line arguments.
- **Interrupted output file integrity**: If the tool is killed while writing to the output file, the file should remain in a recoverable state (e.g., JSON lines format for append-friendly writes).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The command MUST accept one or more file/directory paths as positional arguments.
- **FR-002**: The command MUST compute the BLAKE3 hash for each file by reading its content.
- **FR-003**: The command MUST compute the hash for each directory by sorting the hashes of its immediate children, joining them with `#`, and computing the BLAKE3 hash of the resulting string.
- **FR-004**: The command MUST recursively process all descendant files and subdirectories for each input directory.
- **FR-005**: The command MUST output, for each computed entry, the absolute path, the entry name (file or directory name), and the hash value.
- **FR-006**: The command MUST support `--format` / `-f` option with values `markdown` (default), `json`, `csv`, and `yaml`.
- **FR-007**: The command MUST support `--output` / `-o` option to write results to a file instead of stdout.
- **FR-008**: When `--output` targets an existing non-empty file, the command MUST prompt the user for confirmation before overwriting, explaining the consequences.
- **FR-009**: When `--output` is specified without `--format`, the command MUST infer the format from the output file extension (`.json` → JSON, `.csv` → CSV, `.yaml`/`.yml` → YAML, otherwise Markdown).
- **FR-010**: The command MUST support `--exclude` / `-e` option to specify glob-style exclusion patterns. Multiple patterns can be provided.
- **FR-011**: The command MUST display a progress bar on stderr during computation, showing the number of processed entries out of total.
- **FR-012**: The command MUST support `--workers` / `-w` option to specify the number of parallel workers for concurrent hash computation.
- **FR-013**: The command MUST support `--hash-length` / `-l` option to specify the BLAKE3 output length in bits (default: 256).
- **FR-014**: The command MUST support resume of interrupted computations when `--output` is used, by detecting existing results and skipping already-computed entries.
- **FR-015**: During resumed computation, the command MUST detect if a previously-computed file has been modified (by comparing modification time and/or size) and recompute it if changed.
- **FR-016**: The command MUST periodically flush results to the output file during long computations to minimize data loss on interruption.
- **FR-017**: The command MUST report errors for unreadable files (permission denied, not found) and continue processing remaining files.
- **FR-018**: The command MUST skip symbolic links and report a warning for each skipped symlink.
- **FR-019**: The command MUST deduplicate overlapping or duplicate input paths.
- **FR-020**: The command MUST accept paths from stdin when piped (in addition to command-line arguments).

### Key Entities

- **HashEntry**: Represents a computed hash result for a single file or directory. Contains the absolute path, the base name (file/directory name), the hash value (hex string), and the entry type (file or directory).
- **ExclusionPattern**: A glob-style pattern that specifies which paths to skip during traversal. Applied against both file/directory names and full relative paths.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can compute hashes for a directory containing 10,000 files and receive correct results for all entries.
- **SC-002**: The same input produces identical hash values across repeated runs (deterministic output).
- **SC-003**: When a file within a directory changes, only that file's hash and its ancestor directories' hashes change — all other sibling hashes remain unchanged.
- **SC-004**: With `--workers 4`, hash computation for 1,000 files completes at least 2x faster than with `--workers 1` on a multi-core machine.
- **SC-005**: An interrupted computation can be resumed, and the final output is byte-for-byte identical to a single uninterrupted run.
- **SC-006**: Results in all four output formats (Markdown, JSON, CSV, YAML) are valid according to their respective format specifications and contain identical hash data.
- **SC-007**: Excluded files and directories do not appear in the output and do not affect any directory hash computation.
- **SC-008**: A progress bar is visible during the entire computation and accurately reflects the proportion of work completed.

## Assumptions

- The tool is run from a command-line environment (terminal) on macOS, Linux, or Windows.
- The user has read access to all files and directories they want to hash.
- BLAKE3 is the only hash algorithm; no support for alternative hash functions is needed.
- The default hash output length is 256 bits (64 hex characters).
- The `#` character is used as the delimiter when concatenating child hashes for directory hash computation.
- Glob-style patterns (similar to `.gitignore` syntax) are used for exclusion, as this is the most widely recognized pattern format for file/directory exclusion.
- The default concurrency level is the number of available CPU cores.
- When outputting to a file, JSON format is used for the resume/checkpoint mechanism internally, regardless of the user-specified output format, and the final output is converted to the requested format upon completion.
- Symlinks are skipped (not followed) to prevent infinite recursion and inconsistent results.
- The tool follows the project convention: Python implementation in `python/<command>/` with a root-level Bash wrapper script.
- Dependencies are managed by `uv` with a `pyproject.toml`, consistent with existing Python-based tools in the project.
- The tool does not require network access — all computation is local.
