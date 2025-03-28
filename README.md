# HTML to Markdown Converter

A Python application that converts HTML documents into clean, readable Markdown format.

## Installation

```bash
# Clone the repository
git clone https://github.com/ZeroXClem/html_to_markdown
cd html_to_markdown

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python html_to_markdown.py input.html output.md
```

## Supported HTML Elements

The converter supports the following HTML elements:

- Headers (h1-h3)
- Paragraphs (p)
- Links (a)
- Emphasis (em)
- Strong text (strong)
- Code blocks (pre, code)
- Lists (ul, ol, li)

## Example

Input HTML:
```html
<h1>Welcome</h1>
<p>This is a <strong>sample</strong> with a <a href="https://example.com">link</a>.</p>
```

Output Markdown:
```markdown
# Welcome

This is a **sample** with a [link](https://example.com).
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
