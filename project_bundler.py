import os
import fnmatch
import argparse
import sys
import io       # Added for comment stripping
import tokenize # Added for comment stripping

def load_exclusions(config_file):
    """Load exclusion patterns and names from config file."""
    exclusions = []
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    exclusions.append(line)
    return exclusions

def is_excluded(name, exclusions):
    """Check if a file or directory name matches any exclusion."""
    for pattern in exclusions:
        if fnmatch.fnmatch(name, pattern) or name == pattern:
            return True
    return False

def _core_remove_python_comments_tokenize(code_string):
    """
    Core helper to remove hash (#) comments from a Python code string using tokenize.
    This step removes comment text but may leave blank lines or whitespace-only lines.
    May raise tokenize.TokenError for malformed Python.
    """
    io_obj = io.StringIO(code_string)
    filtered_tokens = []
    # tokenize.generate_tokens can raise tokenize.TokenError for malformed Python
    for tok_info in tokenize.generate_tokens(io_obj.readline):
        if tok_info.type != tokenize.COMMENT:
            filtered_tokens.append(tok_info)
    
    return tokenize.untokenize(filtered_tokens)

def remove_blank_lines(text_content):
    """
    Removes lines that are empty or contain only whitespace from a text string.
    Ensures a single trailing newline if the resulting content is not empty.
    """
    lines = text_content.splitlines()
    # Keep lines that have some non-whitespace content
    processed_lines = [line for line in lines if line.strip()]
    
    if not processed_lines:
        return ""  # Return empty string if all lines were blank.
    else:
        # Join lines with a newline and add a trailing newline.
        return "\n".join(processed_lines) + "\n"

def remove_python_comments(code_string):
    """
    Removes hash (#) comments and blank lines from a Python code string.
    Uses the tokenize module for robust comment detection.
    - End-of-line comments are removed.
    - Lines that consisted only of comments (and potentially whitespace) are removed entirely.
    - Pre-existing blank lines (or lines with only whitespace) in the code are also removed.
    
    This function may reformat whitespace slightly due to tokenize.untokenize.
    The output, if non-empty, will end with a single newline character.
    If tokenizing fails (e.g., due to syntax errors in the Python code),
    this function will raise an error (e.g., tokenize.TokenError),
    which is expected to be handled by the caller.
    """
    # Step 1: Use tokenize to remove comment text robustly.
    # This can raise tokenize.TokenError, which will propagate.
    code_stripped_of_comment_text = _core_remove_python_comments_tokenize(code_string)

    # Step 2: Remove lines that are now blank or contain only whitespace.
    return remove_blank_lines(code_stripped_of_comment_text)


def generate_tree_structure(root_dir, exclusions):
    """Return a text tree of the project structure, excluding patterns."""
    lines = []
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
        dirnames[:] = sorted([d for d in dirnames if not is_excluded(d, exclusions)])
        current_files = sorted([f for f in filenames if not is_excluded(f, exclusions)])
        relative_dirpath = os.path.relpath(dirpath, root_dir)
        
        if relative_dirpath == ".":
            level = 0
            dir_display_name = os.path.basename(os.path.abspath(root_dir)) + '/' if root_dir != '.' else './'
            lines.append(f'{dir_display_name}')
        else:
            level = relative_dirpath.count(os.sep) + (1 if os.sep != '.' else 0)
            dir_display_name = os.path.basename(dirpath) + '/'
            indent = ' ' * 4 * level
            lines.append(f'{indent}{dir_display_name}')
        
        sub_indent = ' ' * 4 * (level + 1)
        for filename_in_tree in current_files:
            lines.append(f'{sub_indent}{filename_in_tree}')
            
    return '\n'.join(lines)

def concatenate_files(root_dir, exclusions, output_file, args):
    """
    Append all non-excluded files into one output.
    Text files are inlined; binary files get a placeholder.
    Python file comments and/or blank lines can be stripped based on args.
    """
    with open(output_file, 'a', encoding='utf-8') as fout:
        fout.write('\n\n# --- Concatenated Files ---\n\n')
        
        paths_to_process = []
        for dirpath, dirnames, filenames_in_walk in os.walk(root_dir, topdown=True):
            dirnames[:] = sorted([d for d in dirnames if not is_excluded(d, exclusions)])
            current_filenames = sorted([f for f in filenames_in_walk if not is_excluded(f, exclusions)])
            for fname in current_filenames:
                paths_to_process.append(os.path.join(dirpath, fname))

        paths_to_process.sort(key=lambda p: os.path.relpath(p, root_dir).replace(os.sep, '/'))

        for full_path in paths_to_process:
            rel_path = os.path.relpath(full_path, root_dir)
            rel_path_header = rel_path.replace(os.sep, '/')

            fout.write(f'# --- File: {rel_path_header} ---\n')
            
            try:
                with open(full_path, 'r', encoding='utf-8') as fin:
                    content = fin.read()
                
                current_file_basename = os.path.basename(full_path)
                is_python_file = current_file_basename.lower().endswith('.py')
                
                # Flag to track if Python-specific processing (which includes blank line removal) occurred
                python_specific_processing_done = False

                if args.strip_python_comments and is_python_file:
                    try:
                        content = remove_python_comments(content) # This also removes blank lines
                        python_specific_processing_done = True
                    except Exception as e_strip:
                        sys.stderr.write(f"Warning: Could not strip comments from {rel_path}: {e_strip}. Using original content.\n")
                
                # Apply general blank line stripping if requested AND
                # it's not a Python file OR it's a Python file but comment stripping was not done/enabled.
                if args.strip_blank_lines:
                    if not is_python_file: # Always apply to non-Python text files
                        content = remove_blank_lines(content)
                    elif is_python_file and not python_specific_processing_done: # Apply to .py only if SPC didn't already
                        content = remove_blank_lines(content)
                
                fout.write(content)
                # Both remove_python_comments and remove_blank_lines ensure a trailing \n for non-empty output.
                # This final check handles cases where no stripping was done and the original file lacked a newline.
                if content and not content.endswith('\n'):
                    fout.write('\n')

            except UnicodeDecodeError:
                fout.write('binary file\n')
            except Exception as e:
                sys.stderr.write(f"Error processing file {rel_path}: {e}\n")
                fout.write(f'Error processing file: {e}\n')
            
            fout.write(f'# --- End of File: {rel_path_header} ---\n\n')

def reverse_mode(input_file, target_dir):
    """
    Recreate directories and files from a concatenated project file.
    Correctly strips the trailing ' ---' from each file header.
    Handles paths with either / or \ as separators from the header.
    """
    FILE_HEADER = '# --- File: '
    FILE_FOOTER = '# --- End of File: '
    SECTION_HEADER = '# --- Concatenated Files ---'

    try:
        with open(input_file, 'r', encoding='utf-8') as fin:
            all_lines = fin.read().splitlines()
    except FileNotFoundError:
        sys.stderr.write(f"Error: Input file '{input_file}' not found.\n")
        return
    except Exception as e:
        sys.stderr.write(f"Error reading input file '{input_file}': {e}\n")
        return

    try:
        start_idx = -1
        for i, line_check in enumerate(all_lines):
            if line_check.strip() == SECTION_HEADER:
                start_idx = i
                break
        if start_idx == -1:
            sys.stderr.write(f"Input file missing '{SECTION_HEADER}' header.\n")
            return
    except ValueError: 
        sys.stderr.write(f"Input file missing '{SECTION_HEADER}' header.\n")
        return

    content_lines = all_lines[start_idx + 2:] 
    
    current_path_str_for_reverse = None
    buffer_for_reverse = []

    def _flush_current_file_for_reverse():
        nonlocal current_path_str_for_reverse 
        if current_path_str_for_reverse:
            normalized_path = current_path_str_for_reverse.replace('/', os.sep).replace('\\', os.sep)
            dest = os.path.join(target_dir, normalized_path)
            
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
            except OSError as e: 
                sys.stderr.write(f"Error creating directory {os.path.dirname(dest)}: {e}\n")
                current_path_str_for_reverse = None 
                return

            content_to_write = '\n'.join(buffer_for_reverse)
            
            try:
                with open(dest, 'w', encoding='utf-8') as fout_rev:
                    if content_to_write == 'binary file' and len(buffer_for_reverse) == 1:
                        fout_rev.write('binary file\n')
                    else:
                        fout_rev.write(content_to_write)
                        if content_to_write and not content_to_write.endswith('\n'):
                            fout_rev.write('\n')
            except IOError as e:
                sys.stderr.write(f"Error writing file {dest}: {e}\n")
            current_path_str_for_reverse = None 

    for line in content_lines:
        line_stripped_for_header_check = line.rstrip()
        
        if line.startswith(FILE_HEADER) and line_stripped_for_header_check.endswith(' ---'):
            _flush_current_file_for_reverse() 
            path_extract_part = line[len(FILE_HEADER):]
            if ' ---' in path_extract_part:
                 current_path_str_for_reverse = path_extract_part.rsplit(' ---', 1)[0].strip()
            else: 
                 sys.stderr.write(f"Warning: Malformed file header (missing ' ---' marker): {line}\n")
                 current_path_str_for_reverse = None 
            buffer_for_reverse = [] 
        elif line.startswith(FILE_FOOTER): 
            _flush_current_file_for_reverse()
            buffer_for_reverse = [] 
        else: 
            if current_path_str_for_reverse: 
                buffer_for_reverse.append(line)
    
    _flush_current_file_for_reverse() 

def main():
    parser = argparse.ArgumentParser(
        description='Forward: generate tree + concat files; Reverse: split into files/dirs.'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--forward', action='store_true',
                       help='Generate single concatenated project file')
    group.add_argument('--reverse', action='store_true',
                       help='Recreate dirs/files from concatenated project file')

    parser.add_argument('--root', '-r', default='.',
                        help='Root directory to scan or recreate into (default: .)')
    parser.add_argument('--output', '-o',
                        help='Output file for forward mode (required if --forward)')
    parser.add_argument('--input', '-i',
                        help='Input concatenated file for reverse mode (required if --reverse)')
    parser.add_argument('--config', '-c', default='config.txt',
                        help='Config file with exclusions (default: config.txt, for forward mode)')
    parser.add_argument(
        '--strip-python-comments', '-spc',
        action='store_true',
        help='(Forward mode only) Remove comments and blank lines from Python files (.py) before concatenation.'
    )
    parser.add_argument(
        '--strip-blank-lines', '-sbl',
        action='store_true',
        help='(Forward mode only) Remove blank lines (empty or whitespace-only) from all text files. For .py files, this is only applied if --strip-python-comments is not active (as that option already handles it).'
    )

    args = parser.parse_args()

    if args.forward and not os.path.isdir(args.root):
        sys.stderr.write(f"Error: Root directory '{args.root}' not found or not a directory.\n")
        sys.exit(1)
    
    if args.reverse:
        pass

    if args.forward:
        if not args.output:
            parser.error('--output is required for forward mode')
        exclusions = load_exclusions(args.config)
        
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write('# --- Project Structure ---\n\n')
                tree_text = generate_tree_structure(args.root, exclusions)
                f.write(tree_text)
            # Pass the full args object to concatenate_files
            concatenate_files(args.root, exclusions, args.output, args)
            print(f"Project bundled into {args.output}")
        except IOError as e:
            sys.stderr.write(f"Error writing to output file {args.output}: {e}\n")
            sys.exit(1)
            
    elif args.reverse: 
        if not args.input:
            parser.error('--input is required for reverse mode')
        
        if os.path.exists(args.root) and not os.path.isdir(args.root):
            sys.stderr.write(f"Error: Target root '{args.root}' exists and is not a directory.\n")
            sys.exit(1)
        
        if not os.path.exists(args.root):
            try:
                os.makedirs(args.root, exist_ok=True) 
                print(f"Target root directory '{args.root}' created.")
            except OSError as e:
                sys.stderr.write(f"Error: Could not create target root directory '{args.root}': {e}\n")
                sys.exit(1)

        reverse_mode(args.input, args.root)
        print(f"Project reconstructed into {args.root} from {args.input}")

if __name__ == '__main__':
    main()
