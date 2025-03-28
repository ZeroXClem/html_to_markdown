import sys
import re # Needed for final cleanup and potentially escaping
import logging
import argparse
import glob
import os
import functools # For lru_cache
from bs4 import BeautifulSoup, NavigableString, Tag

# Import rules from the updated file
from markdown_rules_v2 import MARKDOWN_RULES, escape_markdown_chars

# Configure logging (will be updated in MarkdownConverter init)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Improvement 3: Configuration and Extensibility ---
class MarkdownConverter:
    def __init__(self,
                 custom_rules=None,
                 ignore_tags=None,
                 log_level_str='INFO'):
        """
        Initialize the MarkdownConverter.

        Args:
            custom_rules (dict, optional): Dictionary to update/add markdown rules.
            ignore_tags (list or set, optional): Tags to completely ignore during conversion.
            log_level_str (str, optional): Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        """
        self.markdown_rules = MARKDOWN_RULES.copy()
        if custom_rules:
            self.markdown_rules.update(custom_rules)

        # Default tags to ignore + any user-provided ones
        default_ignore = {'script', 'style', 'head', 'title', 'meta', 'link'}
        if ignore_tags:
            self.ignore_tags = default_ignore.union(set(ignore_tags))
        else:
            self.ignore_tags = default_ignore

        # Configure logging level
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        # Update the root logger's level. Note: This affects global logging.
        # For more isolated logging, instantiate a separate logger.
        logging.getLogger().setLevel(log_level)

        logging.debug("MarkdownConverter initialized.")
        logging.debug(f"Ignore tags: {self.ignore_tags}")

    # --- Improvement 1: Error Handling and Validation ---
    def _validate_input(self, html_content):
        """
        Validates the input HTML content.

        Args:
            html_content (str): The HTML content string.

        Raises:
            ValueError: If HTML content is empty or seems invalid.
        """
        if not html_content or not html_content.strip():
            raise ValueError("Input HTML content is empty or whitespace only")

        try:
            # Basic check: Does it parse at all and contain any tags?
            soup = BeautifulSoup(html_content, 'html.parser')
            if not soup.find():
                # Allow empty body/html tag, but check if there's *any* content node
                if not soup.contents:
                     raise ValueError("Input HTML appears empty or contains no valid elements")
                # If only a root like <html> or <body> exists but is empty, allow it
                # More complex validation (e.g., DTD) is outside scope here.
        except Exception as e:
            # Catch potential parsing errors from BeautifulSoup
            logging.error(f"HTML parsing error during validation: {e}")
            raise ValueError(f"Failed to parse HTML: {e}") from e

    # --- Improvement 4: Performance Optimization (Caching) ---
    # Note: Caching BeautifulSoup objects can be tricky if they aren't perfectly hashable
    # or if their identity changes unexpectedly. Test thoroughly for complex HTML.
    # maxsize chosen arbitrarily, adjust based on memory/performance needs.
    @functools.lru_cache(maxsize=1024)
    def _convert_node_to_markdown(self, element, list_level=0, list_type=None, item_number=1):
        """
        Recursively converts a BeautifulSoup node (Tag or NavigableString) to Markdown.
        (Internal method using instance state like self.ignore_tags, self.markdown_rules)

        Args:
            element: The BeautifulSoup element (Tag or NavigableString).
            list_level (int): Current nesting level for lists.
            list_type (str | None): Type of the current list ('ul' or 'ol').
            item_number (int): The item number if this node is an 'li' within an 'ol'.

        Returns:
            str: The Markdown representation of the node.
        """
        # 1. Handle Text Nodes (NavigableString)
        if isinstance(element, NavigableString):
            text = str(element)
            # Avoid stripping significant whitespace within tags like <pre> or <code>
            # Check parent tag - simple check for now
            parent_name = getattr(element.parent, 'name', '')
            if parent_name not in ['pre'] and not text.isspace():
                 # Apply basic stripping and escaping for general text
                 return escape_markdown_chars(text.strip())
            elif parent_name == 'pre':
                 return text # Preserve whitespace in pre tags
            else:
                 # Keep space if it's between inline elements, strip otherwise
                 # This is complex; a simple approach is to strip if it's just whitespace
                 if text.isspace():
                     # Only return a single space if it seems significant (e.g., between words/tags)
                     # Check siblings - needs more complex logic, return ' ' for now if needed
                     # For simplicity, let's just return '' for pure whitespace nodes unless in <pre>
                     return ''
                 else:
                     return escape_markdown_chars(text) # Escape non-space text

        # 2. Handle Tags
        if not isinstance(element, Tag):
            return '' # Should not happen with standard BS parsing

        tag_name = element.name

        # Ignore tags specified in config
        if tag_name in self.ignore_tags:
            logging.debug(f"Ignoring tag: <{tag_name}>")
            return ''

        # Handle line breaks
        if tag_name == 'br':
            return '\n' # Use single newline, final cleanup will handle multiples

        # 3. Recursively process children
        children_md = ""
        current_item_number = 1 # For ordered lists within the current element's children
        for child in element.children:
            child_list_type = list_type
            child_list_level = list_level
            # Pass list context down
            if tag_name == 'ul':
                child_list_type = 'ul'
                child_list_level += 1
            elif tag_name == 'ol':
                child_list_type = 'ol'
                child_list_level += 1

            # Determine the item number for li elements
            li_item_number = 1
            if tag_name == 'ol' and isinstance(child, Tag) and child.name == 'li':
                li_item_number = current_item_number

            # Recursive call
            children_md += self._convert_node_to_markdown(
                child,
                list_level=child_list_level,
                list_type=child_list_type,
                item_number=li_item_number # Pass the calculated item number for this child if it's an li
            )

            # Increment item number for direct children of 'ol' that are 'li'
            if tag_name == 'ol' and isinstance(child, Tag) and child.name == 'li':
                current_item_number += 1

        # 4. Apply Markdown rule for the current tag
        if tag_name in self.markdown_rules:
            rule = self.markdown_rules[tag_name]
            try:
                # Pass necessary context to the rule
                kwargs = {
                    'element': element,
                    'children_md': children_md,
                    'list_level': list_level,
                    'list_type': list_type,
                    'item_number': item_number # Pass the item_number received from parent
                }
                return rule(**kwargs)
            except TypeError as e:
                logging.warning(f"Rule for '{tag_name}' failed or has wrong signature: {e}. Using children content. Check rule definition.")
                # Fallback if rule fails or doesn't accept expected args
                return children_md # Return processed children content as fallback
        else:
            # Default for unknown tags: return children's content
            logging.debug(f"No rule found for tag '{tag_name}'. Returning children content.")
            return children_md


    def convert(self, html_content):
        """
        Converts an HTML string to Markdown using the configured rules.

        Args:
            html_content (str): The HTML content string.

        Returns:
            str: The converted Markdown string.

        Raises:
            ValueError: If input validation fails.
        """
        logging.info("Starting HTML to Markdown conversion...")
        self._validate_input(html_content)

        # Clear cache if running multiple conversions with the same instance (optional)
        # self._convert_node_to_markdown.cache_clear()
        # Note: Cache is instance-based; creating a new instance per file implicitly clears.

        soup = BeautifulSoup(html_content, 'html.parser')

        # Prefer body if it exists, otherwise use the whole soup's children
        root_element = soup.body if soup.body else soup

        # Join parts converted from root's direct children
        # We process children of the root individually to avoid wrapping the whole doc in a spurious tag
        # Start list level at 0, type None, item_number 1 initially
        markdown_parts = [self._convert_node_to_markdown(child, 0, None, 1) for child in root_element.children]
        markdown_content = "".join(markdown_parts)

        # Clean up excessive newlines (more than 2 consecutive) and leading/trailing whitespace
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content.strip())

        logging.info("Conversion finished.")
        return markdown_content

# --- Improvement 5: Enhanced CLI / Batch Processing ---

def convert_file(input_file, output_file, converter_config):
    """
    Reads an HTML file, converts it using MarkdownConverter, and writes to a Markdown file.

    Args:
        input_file (str): Path to the input HTML file.
        output_file (str): Path to the output Markdown file.
        converter_config (dict): Configuration options for MarkdownConverter.
    """
    try:
        logging.info(f"Processing file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Create a converter instance for each file (clears cache implicitly)
        converter = MarkdownConverter(**converter_config)
        md_content = converter.convert(html_content)

        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            logging.info(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

        logging.info(f"Writing Markdown to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write(md_content)

        logging.info(f"Successfully converted {input_file} to {output_file}")

    except FileNotFoundError:
        logging.error(f"Error: Input file not found at {input_file}")
        # Optionally re-raise or handle differently if used in a larger batch process
    except IOError as e:
        logging.error(f"Error reading or writing file {input_file} or {output_file}: {e}")
    except ValueError as e: # Catch validation errors from converter
        logging.error(f"Error converting file {input_file}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred processing {input_file}: {e}", exc_info=True) # Log full traceback

def main():
    """
    Main function to handle command-line arguments and initiate file processing.
    """
    parser = argparse.ArgumentParser(
        description='Convert HTML file(s) to Markdown.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  python html_to_markdown_v2.py input.html output.md
  python html_to_markdown_v2.py "docs/*.html" -o output_md/
  python html_to_markdown_v2.py index.html -o . --log-level DEBUG
'''
    )
    parser.add_argument(
        'input_pattern',
        help='Input HTML file path or glob pattern (e.g., "pages/*.html"). Quote patterns containing wildcards.'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output directory or file. If input is a single file, this can be a file path. '
             'If input is a pattern or output is a directory, output files will be placed here '
             'with a .md extension. If omitted, .md files are created alongside input files.'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set the logging verbosity level (default: INFO).'
    )
    # Could add --ignore-tags argument here later

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    # --- Input File Resolution ---
    input_files = glob.glob(args.input_pattern)

    if not input_files:
        logging.error(f"No files found matching pattern: {args.input_pattern}")
        sys.exit(1)

    logging.info(f"Found {len(input_files)} file(s) to convert.")

    # --- Determine Output Mode ---
    output_is_dir = False
    single_output_file = None

    if args.output:
        # Check if output exists and is a directory
        if os.path.isdir(args.output):
            output_is_dir = True
        # Check if output path looks like a directory (ends with / or \)
        elif args.output.endswith(os.path.sep):
             output_is_dir = True
             # Ensure the directory exists
             os.makedirs(args.output, exist_ok=True)
        # If multiple inputs, output must be a directory
        elif len(input_files) > 1:
            output_is_dir = True
            logging.warning(f"Multiple input files specified; treating output '{args.output}' as a directory.")
            os.makedirs(args.output, exist_ok=True)
        # Single input, output doesn't exist or isn't a dir -> treat as output file path
        else:
            single_output_file = args.output

    # --- Process Files ---
    converter_config = {'log_level_str': args.log_level} # Add other config later if needed

    for input_file in input_files:
        output_file = None
        base_name = os.path.basename(input_file)
        # Ensure we handle various extensions like .htm, .xhtml etc.
        file_name_part, _ = os.path.splitext(base_name)
        md_name = file_name_part + '.md'

        if single_output_file: # Single input, specific output file
            output_file = single_output_file
        elif output_is_dir: # Output to a specific directory
            output_file = os.path.join(args.output, md_name)
        elif args.output and not output_is_dir : #Should have been caught, but safety check
             output_file = args.output #Treat as file path if only one input file
        else: # No output specified, create alongside input
            output_file = os.path.join(os.path.dirname(input_file), md_name)

        # Prevent overwriting input file if names collide (e.g., input.md exists)
        if os.path.abspath(input_file) == os.path.abspath(output_file):
            logging.error(f"Input and output file paths are the same: {input_file}. Skipping.")
            continue

        convert_file(input_file, output_file, converter_config)

        # If a single output file was specified for multiple inputs, stop after the first.
        if single_output_file and len(input_files) > 1:
            logging.warning("Output specified as a single file, but multiple inputs found. Processed only the first file.")
            break


if __name__ == "__main__":
    main()

