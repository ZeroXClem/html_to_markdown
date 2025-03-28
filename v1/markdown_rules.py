# Rules accept kwargs: element, children_md, list_level, list_type, item_number

# Helper function for block elements to manage whitespace
def format_block(content):
    return f"{content.strip()}\\n\\n"

MARKDOWN_RULES = {
    'h1': lambda element, children_md, **kwargs: format_block(f"# {children_md}"),
    'h2': lambda element, children_md, **kwargs: format_block(f"## {children_md}"),
    'h3': lambda element, children_md, **kwargs: format_block(f"### {children_md}"),
    'h4': lambda element, children_md, **kwargs: format_block(f"#### {children_md}"),
    'h5': lambda element, children_md, **kwargs: format_block(f"##### {children_md}"),
    'h6': lambda element, children_md, **kwargs: format_block(f"###### {children_md}"),

    'p': lambda element, children_md, **kwargs: format_block(children_md),

    'a': lambda element, children_md, **kwargs: f'[{children_md.strip()}]({element.get("href", "")})',

    'strong': lambda element, children_md, **kwargs: f'**{children_md}**', # Don't strip internal whitespace
    'b': lambda element, children_md, **kwargs: f'**{children_md}**',      # Treat <b> like <strong>

    'em': lambda element, children_md, **kwargs: f'*{children_md}*',       # Don't strip internal whitespace
    'i': lambda element, children_md, **kwargs: f'*{children_md}*',        # Treat <i> like <em>

    # Use element.string for code/pre to avoid processing internal tags as Markdown
    'code': lambda element, **kwargs: f'`{element.string or ""}`',
    'pre': lambda element, **kwargs: format_block(f'```\\n{element.get_text(strip=True)}\\n

