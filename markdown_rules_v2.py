# Rules accept kwargs: element, children_md, list_level, list_type, item_number
import re

# --- Improvement 2: Escaping ---
# Defined here for use within rules, especially <a> link text and list items
def escape_markdown_chars(text):
    """
    Comprehensive Markdown character escaping
    Handle special Markdown characters like *, _, \, [], (), etc.
    """
    if not text: # Handle None or empty strings
        return ''
    # Escape backslashes first, then other chars
    text = text.replace('\\', '\\\\')
    # Escape other markdown special characters.
    # Using a specific list to avoid over-escaping in URLs etc.
    escape_chars = r'([`*_{}[\]()#+.!-])' # Removed '|' and initial '\' as it's handled above
    return re.sub(escape_chars, r'\\\1', text)

# Helper function for block elements to manage whitespace
def format_block(content):
    return f"{content.strip()}\n\n" # Use single \n, literal newlines handled later

# --- MARKDOWN_RULES Dictionary ---
MARKDOWN_RULES = {
    'h1': lambda element, children_md, **kwargs: format_block(f"# {children_md.strip()}"),
    'h2': lambda element, children_md, **kwargs: format_block(f"## {children_md.strip()}"),
    'h3': lambda element, children_md, **kwargs: format_block(f"### {children_md.strip()}"),
    'h4': lambda element, children_md, **kwargs: format_block(f"#### {children_md.strip()}"),
    'h5': lambda element, children_md, **kwargs: format_block(f"##### {children_md.strip()}"),
    'h6': lambda element, children_md, **kwargs: format_block(f"###### {children_md.strip()}"),

    'p': lambda element, children_md, **kwargs: format_block(children_md.strip()),

    # Apply escaping to link text
    'a': lambda element, children_md, **kwargs: f'[{escape_markdown_chars(children_md.strip())}]({element.get("href", "")})',

    'strong': lambda element, children_md, **kwargs: f'**{children_md}**', # Don't strip internal whitespace
    'b': lambda element, children_md, **kwargs: f'**{children_md}**',      # Treat <b> like <strong>

    'em': lambda element, children_md, **kwargs: f'*{children_md}*',       # Don't strip internal whitespace
    'i': lambda element, children_md, **kwargs: f'*{children_md}*',        # Treat <i> like <em>

    # Use element.string or get_text() for code/pre to avoid processing internal tags as Markdown
    # Apply escaping to content within single backticks
    'code': lambda element, **kwargs: f'`{escape_markdown_chars(element.string or "")}`',
    # Let ``` block handle content literally, no internal escaping needed by default
    'pre': lambda element, **kwargs: format_block(f'```\n{element.get_text().strip()}\n```'),

    'hr': lambda element, **kwargs: format_block('---'),

    'img': lambda element, **kwargs: f'![{escape_markdown_chars(element.get("alt", ""))}]( {element.get("src", "")})',

    # --- List Handling (Added back based on original script's needs) ---
    'ul': lambda element, children_md, **kwargs: format_block(children_md.strip()), # Let li handle indentation
    'ol': lambda element, children_md, **kwargs: format_block(children_md.strip()), # Let li handle numbering/indentation

    'li': lambda element, children_md, list_level, list_type, item_number, **kwargs:
        f"{'  ' * (list_level - 1 if list_level > 0 else 0)}" # Indentation (adjust multiplier if needed)
        f"{item_number}. " if list_type == 'ol' else '* '     # Marker
        f"{children_md.strip()}\n",                             # Content and newline

    # Handle blockquotes
    'blockquote': lambda element, children_md, **kwargs: format_block(
        # Add "> " prefix to each line of the blockquote content
        '\n'.join([f"> {line}" for line in children_md.strip().split('\n')])
    ),
}

