import sys
from bs4 import BeautifulSoup, NavigableString, Tag
from markdown_rules import MARKDOWN_RULES
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def convert_node_to_markdown(element, list_level=0, list_type=None):
   """
    Recursively converts a BeautifulSoup node (Tag or NavigableString) to Markdown.

    Args:
        element: The BeautifulSoup element (Tag or NavigableString).
        list_level (int): Current nesting level for lists.
        list_type (str | None): Type of the current list ('ul' or 'ol').

    Returns:
        str: The Markdown representation of the node.
    """
    # 1. Handle Text Nodes (NavigableString)
    if isinstance(element, NavigableString):
        text = str(element).strip() # Strip whitespace from raw text nodes
        # Potentially add escaping for Markdown special characters here if needed
        return text

    # 2. Handle Tags that should be ignored or have special handling
    if not isinstance(element, Tag):
        return '' # Should not happen with standard BS parsing

    tag_name = element.name

    # Ignore certain tags completely (like script, style)
    if tag_name in ['script', 'style', 'head', 'title', 'meta', 'link']:
        return ''

    # Handle line breaks
    if tag_name == 'br':
        return '\\n' # Use double backslash for literal newline in Markdown output

    # 3. Recursively process children
    children_md = ""
    item_number = 1 # For ordered lists
    for child in element.children:
        child_list_type = list_type
        if tag_name == 'ul':
            child_list_type = 'ul'
        elif tag_name == 'ol':
             child_list_type = 'ol'

        children_md += convert_node_to_markdown(child, list_level + (1 if tag_name in ['ul', 'ol'] else 0), child_list_type)

        # Increment item number for direct children of 'ol' that are 'li'
        if tag_name == 'ol' and isinstance(child, Tag) and child.name == 'li':
            item_number += 1

    # Reset item_number for the next recursive call where parent is not 'ol'
    if tag_name != 'ol':
        item_number = 1

    # 4. Apply Markdown rule for the current tag
    if tag_name in MARKDOWN_RULES:
        rule = MARKDOWN_RULES[tag_name]
        # Pass element, processed children, list context if needed
        try:
            # Pass necessary context to the rule
            kwargs = {
                'element': element,
                'children_md': children_md,
                'list_level': list_level,
                'list_type': list_type,
                # Provide item_number for 'li' within 'ol'
                'item_number': item_number -1 # Use the number *before* incrementing for the current item
            }
            return rule(**kwargs)
        except TypeError as e:
            logging.warning(f"Rule for '{tag_name}' failed or has wrong signature: {e}. Using children content.")
            # Fallback if rule fails or doesn't accept expected args
            return children_md
    else:
        # Default for unknown tags: return children's content
        # logging.debug(f"No rule found for tag '{tag_name}'. Returning children content.")
        return children_md


def convert_html_to_markdown(html_content):
    """
    Converts an HTML string to Markdown.

    Args:
        html_content (str): The HTML content string.

    Returns:
        str: The converted Markdown string.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Prefer body if it exists, otherwise use the whole soup
    root_element = soup.body if soup.body else soup

    # Join parts converted from root's direct children
    # We process children of the root individually to avoid wrapping the whole doc in a spurious tag
    markdown_content = "".join(convert_node_to_markdown(child) for child in root_element.children)

    # Clean up excessive newlines (more than 2 consecutive)
    import re
    markdown_content = re.sub(r'\\n{3,}', '\\n\\n', markdown_content.strip())

    return markdown_content

def main():
    """
    Main function to handle command-line arguments and file operations.
    """
    if len(sys.argv) != 3:
        print("Usage: python html_to_markdown.py <input.html> <output.md>")
        sys.exit(1) # Exit with error code

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        logging.info(f"Reading HTML from: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        logging.info("Converting HTML to Markdown...")
        md_content = convert_html_to_markdown(html_content)

        logging.info(f"Writing Markdown to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write(md_content)

        logging.info(f"Successfully converted {input_file} to {output_file}")

    except FileNotFoundError:
        logging.error(f"Error: Input file not found at {input_file}")
        sys.exit(1)
    except IOError as e:
        logging.error(f"Error reading or writing file: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True) # Log full traceback
        sys.exit(1)

if __name__ == "__main__":
    main()

