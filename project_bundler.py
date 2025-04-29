import os
import fnmatch
import argparse
import sys

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

def generate_tree_structure(root_dir, exclusions):
    """Return a text tree of the project structure, excluding patterns."""
    lines = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not is_excluded(d, exclusions)]
        filenames = [f for f in filenames if not is_excluded(f, exclusions)]

        level = os.path.relpath(dirpath, root_dir).count(os.sep)
        indent = ' ' * 4 * level
        lines.append(f'{indent}{os.path.basename(dirpath)}/')
        sub_indent = ' ' * 4 * (level + 1)
        for filename in filenames:
            lines.append(f'{sub_indent}{filename}')
    return '\n'.join(lines)

def concatenate_files(root_dir, exclusions, output_file):
    """
    Append all non-excluded files into one output.
    Text files are inlined; binary files get a placeholder.
    """
    with open(output_file, 'a', encoding='utf-8') as fout:
        fout.write('\n\n# --- Concatenated Files ---\n\n')
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if not is_excluded(d, exclusions)]
            filenames = [f for f in filenames if not is_excluded(f, exclusions)]

            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(dirpath, filename), root_dir)
                fout.write(f'# --- File: {rel_path} ---\n')
                full_path = os.path.join(dirpath, filename)
                # Try reading as text
                try:
                    with open(full_path, 'r', encoding='utf-8') as fin:
                        fout.write(fin.read())
                except UnicodeDecodeError:
                    # Binary file placeholder
                    fout.write('binary file\n')
                except Exception as e:
                    sys.stderr.write(f"Error reading {rel_path}: {e}\n")
                fout.write(f'# --- End of File: {rel_path} ---\n\n')

def reverse_mode(input_file, target_dir):
    """
    Recreate directories and files from a concatenated project file.
    Correctly strips the trailing ' ---' from each file header.
    """
    FILE_HEADER = '# --- File: '
    FILE_FOOTER = '# --- End of File: '
    SECTION_HEADER = '# --- Concatenated Files ---'

    with open(input_file, 'r', encoding='utf-8') as fin:
        lines = fin.read().splitlines()

    # locate the start of the concatenated section
    try:
        start_idx = lines.index(SECTION_HEADER)
    except ValueError:
        sys.stderr.write("Input file missing concatenated section header.\n")
        return

    lines = lines[start_idx + 1:]
    current_path = None
    buffer = []

    def flush_file():
        """Write buffered lines to the current_path file under target_dir."""
        if current_path:
            dest = os.path.join(target_dir, current_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'w', encoding='utf-8') as fout:
                fout.write('\n'.join(buffer))

    for line in lines:
        if line.startswith(FILE_HEADER) and line.rstrip().endswith(' ---'):
            # start of new file
            flush_file()
            # extract path between header and trailing ' ---'
            raw = line[len(FILE_HEADER):]
            path = raw[:-4]  # remove the trailing ' ---'
            current_path = path
            buffer = []
        elif line.startswith(FILE_FOOTER):
            # end of this file
            flush_file()
            current_path = None
            buffer = []
        else:
            # content line
            if current_path:
                buffer.append(line)

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
                        help='Output file for forward mode')
    parser.add_argument('--input', '-i',
                        help='Input concatenated file for reverse mode')
    parser.add_argument('--config', '-c', default='config.txt',
                        help='Config file with exclusions (forward mode)')

    args = parser.parse_args()

    if args.forward:
        if not args.output:
            parser.error('--output is required for forward mode')
        exclusions = load_exclusions(args.config)
        # write tree header + structure
        tree_text = generate_tree_structure(args.root, exclusions)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write('# --- Project Structure ---\n\n')
            f.write(tree_text)
        # append all files
        concatenate_files(args.root, exclusions, args.output)
    else:
        if not args.input:
            parser.error('--input is required for reverse mode')
        reverse_mode(args.input, args.root)

if __name__ == '__main__':
    main()
