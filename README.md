# Project Bundler

## Description
**Project Bundler** is a lightweight, zero-dependency command-line tool written in pure Python that packages an entire directory tree into a single text file. It first generates a visual “tree” snapshot of the project structure and then concatenates every file—text and code inline, binary files replaced by a placeholder—into one well-structured output. It also supports a reverse mode to reconstruct the original directories and files from that single bundle.

## Motivation
Large language models (LLMs) often impose limits on the number of files or total upload size. By combining your entire codebase into one neatly formatted text file, you can attach it to a single LLM prompt, avoid juggling multiple uploads, and ensure the model sees the full project context in one go.

## Features
 - **Project tree snapshot**: Visualize your directory hierarchy at the top of the bundle.
 - **Full concatenation**: Recursively include every file (unless excluded), with clear headers and footers.
 - **Configurable exclusions**: Use glob patterns or exact names in `config.txt` to skip unwanted files or directories.
 - **Binary-file handling**: Automatically detect non-text files and insert the placeholder `binary file` in their place.
 - **Reverse reconstruction**: Given a bundle, faithfully recreate the original folder structure and file contents.
 - **Python comment stripping**: Optionally remove comments and blank lines from `.py` files for a cleaner, more compact bundle, reducing token count for LLMs.
 - **Blank line stripping**: Optionally remove blank or whitespace-only lines from all text files, further reducing bundle size.
 - **Zero external dependencies**: Relies only on the Python standard library.
 - **Clean English comments**: Source code is documented entirely in English.

## Prerequisites
- **Python 3.6+**

## Installation
Clone or download this repository, or simply copy `project_bundler.py` into your project folder.

```bash
git clone https://github.com/your-username/project-bundler.git
cd project-bundler
```

## Configuration
Create a `config.txt` in the same directory as the script to list names or glob patterns (one per line) to exclude from the bundle:

```text
# Skip all .bin and .db files
*.bin
*.db

# Skip these directories
storage
temp

# Skip this specific file
Read.me
```

- Lines beginning with `#` are treated as comments and ignored.
- Patterns follow Unix shell-style wildcards.



## Usage

### Bundle mode (forward)
 Generate a single text file containing the tree snapshot and all files:
 
 ```bash
 python project_bundler.py --forward \
     --root /path/to/your/project \
     --output project_bundle.txt \
+    --config config.txt \
+    --strip-python-comments # Example: strip comments and blank lines from Python files

```

### Reconstruct mode (reverse)
Recreate the original directory tree and files from a bundled text file:

```bash
python project_bundler.py --reverse \
    --root ./restored_project \
    --input project_bundle.txt
```

- `--root, -r`  
  Base directory under which files and folders will be recreated (default: current directory).  
- `--input, -i`  
  The bundled text file to split back into individual files (required).

## Example Workflow

1. **Bundle your project**  
   ```bash
   python project_bundler.py --forward \
       --root ./my_project \
       --output my_project_bundle.txt
   ```
2. **Feed `my_project_bundle.txt` to your LLM**  
   No more multiple uploads—just one well-formed text file.
3. **Reconstruct later**  
   ```bash
   python project_bundler.py --reverse \
       --root ./restored_project \
       --input my_project_bundle.txt
   ```

---

[![Support me on PayPal](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate/?hosted_button_id=T4SKREGYTG5ES)

> _Pack your entire codebase into a single text file and share it with any LLM in one go!_

